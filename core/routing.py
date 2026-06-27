import math
import heapq
from typing import Dict, List, Optional, Set, Tuple, Any

from sklearn.metrics import f1_score

PlanetId = str
LinkId = Tuple[PlanetId, PlanetId]
Milliseconds = float
Radians = float


class CodexTranscoder:
    @staticmethod
    def _int_to_base_n(n: int, base: int) -> str:
        if n == 0:
            return "0"
        digits = []
        while n:
            digits.append(int(n % base))
            n //= base
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return "".join(chars[d] for d in reversed(digits))

    @classmethod
    def encode_payload_for_planet(cls, text_payload: str, target_base: int) -> str:
        if target_base == 10:
            return " ".join(str(ord(char)) for char in text_payload)
        
        encoded_tokens = []
        for char in text_payload:
            encoded_tokens.append(cls._int_to_base_n(ord(char), target_base))
        return " ".join(encoded_tokens)


class RoutingEngine:

    def __init__(self, planets: Dict[PlanetId, Dict[str, Any]], metadata: Dict[str, Any]):
        self.planets = planets
        self.metadata = metadata

        self.c: float = float(metadata["speed_of_light_kms"])
        self.l_max: float = float(metadata["max_void_hop_distance_km"])
        self.tower_delay: float = float(metadata["tower_processing_delay_ms"])
        self.scale_unit: float = float(metadata["coordinate_scale_unit_km"])
        self.fiber_fraction: float = float(metadata["fiber_speed_fraction"])

        self._static_topology: Dict[PlanetId, Dict[PlanetId, Milliseconds]] = {}
        self._precompute_network_topology()

    def _precompute_network_topology(self) -> None:
        for p1_id in self.planets:
            self._static_topology[p1_id] = {}
            for p2_id in self.planets:
                if p1_id == p2_id:
                    continue
                latency = self._compute_raw_hop_latency(p1_id, p2_id)
                if latency is not None:
                    self._static_topology[p1_id][p2_id] = latency

    def _compute_raw_hop_latency(self, p1_id: PlanetId, p2_id: PlanetId) -> Optional[Milliseconds]:
        p1, p2 = self.planets[p1_id], self.planets[p2_id]
        
        dx = (p2["x"] - p1["x"]) * self.scale_unit
        dy = (p2["y"] - p1["y"]) * self.scale_unit
        center_dist = math.sqrt(dx * dx + dy * dy)

        boundary_1 = p1["radius_km"] + p1["atmosphere_thickness_km"]
        boundary_2 = p2["radius_km"] + p2["atmosphere_thickness_km"]
        L = center_dist - boundary_1 - boundary_2

        if L > self.l_max or L < 0:
            return None

        t_void = (L / self.c) * 1000.0
        t_atmo1 = (p1["atmosphere_thickness_km"] / (self.c / p1["refraction_index"])) * 1000.0
        t_atmo2 = (p2["atmosphere_thickness_km"] / (self.c / p2["refraction_index"])) * 1000.0
        
        return t_void + t_atmo1 + t_atmo2

    def _get_tower_angle(self, tower_idx: int, total_towers: int) -> Radians:
        return (math.pi / 2.0) - (tower_idx * (2.0 * math.pi / total_towers))

    def _calculate_fiber_delay(self, planet_id: PlanetId, in_angle: Radians, out_angle: Radians) -> Milliseconds:
        p = self.planets[planet_id]
        delta_theta = abs(in_angle - out_angle)
        shortest_angle = min(delta_theta, 2.0 * math.pi - delta_theta)
        arc_length = p["radius_km"] * shortest_angle
        return (arc_length / (self.c * self.fiber_fraction)) * 1000.0

    def _get_optimal_tower_alignment(self, src_id: PlanetId, dst_id: PlanetId) -> Tuple[int, int, Radians, Radians]:
        p1, p2 = self.planets[src_id], self.planets[dst_id]
        p1_x, p1_y = p1["x"] * self.scale_unit, p1["y"] * self.scale_unit
        p2_x, p2_y = p2["x"] * self.scale_unit, p2["y"] * self.scale_unit
        min_dist = float("inf")
        best_alignment = (0, 0, 0.0, 0.0)

        for t1 in range(p1["active_towers"]):
            a1 = self._get_tower_angle(t1, p1["active_towers"])
            t1_x = p1_x + p1["radius_km"] * math.cos(a1)
            t1_y = p1_y + p1["radius_km"] * math.sin(a1)
            for t2 in range(p2["active_towers"]):
                a2 = self._get_tower_angle(t2, p2["active_towers"])
                t2_x = p2_x + p2["radius_km"] * math.cos(a2)
                t2_y = p2_y + p2["radius_km"] * math.sin(a2)
                
                d = (t2_x - t1_x)**2 + (t2_y - t1_y)**2
                if d < min_dist:
                    min_dist = d
                    best_alignment = (t1, t2, a1, a2)
        return best_alignment

    def reconstruct_hop_logs(self, path: List[PlanetId]) -> List[Dict[str, Any]]:
        if not path or len(path) < 2:
            return []
        hop_logs = []
        last_ingress_angle: Optional[Radians] = None

        for i in range(len(path) - 1):
            curr_node, next_node = path[i], path[i+1]
            t_send, t_recv, a_send, a_recv = self._get_optimal_tower_alignment(curr_node, next_node)
            
            fiber_transit_ms = 0.0
            if i > 0 and last_ingress_angle is not None:
                fiber_transit_ms = self._calculate_fiber_delay(curr_node, last_ingress_angle, a_send)

            hop_logs.append({
                "hop_index": i,
                "tx_planet": curr_node,
                "rx_planet": next_node,
                "tx_tower": f"T_{t_send}",
                "rx_tower": f"T_{t_recv}",
                "internal_fiber_delay_ms": round(fiber_transit_ms, 4),
                "hop_latency_ms": round(self._static_topology[curr_node][next_node], 4)
            })
            last_ingress_angle = a_recv
        return hop_logs


    # HEAP ROUTERS WITH LINK LEVEL FAILURE AWARENESS
    def find_route_dijkstra(self, origin: PlanetId, destination: PlanetId, 
                             active_planets: Set[PlanetId], 
                             disabled_links: Set[LinkId] = None) -> Optional[Dict[str, Any]]:
        if origin not in active_planets or destination not in active_planets:
            return None
        
        links_to_ignore = disabled_links if disabled_links else set()
        distances: Dict[PlanetId, float] = {node: float("inf") for node in active_planets}
        previous: Dict[PlanetId, Optional[PlanetId]] = {node: None for node in active_planets}
        
        distances[origin] = 0.0
        pq: List[Tuple[float, PlanetId]] = [(0.0, origin)]

        while pq:
            curr_dist, curr_node = heapq.heappop(pq)
            if curr_dist > distances[curr_node]:
                continue
            if curr_node == destination:
                break

            neighbors = self._static_topology.get(curr_node, {})
            for neighbor, edge_latency in neighbors.items():
                # Rule 1: Node Failure Chaos Check
                if neighbor not in active_planets:
                    continue
                # Rule 2: Fine-Grained Link Failure Chaos Check
                if (curr_node, neighbor) in links_to_ignore or (neighbor, curr_node) in links_to_ignore:
                    continue

                tentative_cost = curr_dist + edge_latency + self.tower_delay
                if tentative_cost < distances[neighbor]:
                    distances[neighbor] = tentative_cost
                    previous[neighbor] = curr_node
                    heapq.heappush(pq, (tentative_cost, neighbor))

        return self._build_packet_schema(origin, destination, distances, previous, raw_message="")

    def _heuristic(self, current_id: PlanetId, target_id: PlanetId) -> float:
        p1, p2 = self.planets[current_id], self.planets[target_id]
        return (math.sqrt(((p2["x"] - p1["x"])*self.scale_unit)**2 + ((p2["y"] - p1["y"])*self.scale_unit)**2) / self.c) * 1000.0

    def find_route_astar(self, origin: PlanetId, destination: PlanetId, 
                           active_planets: Set[PlanetId], 
                           disabled_links: Set[LinkId],
                           raw_message: str) -> Optional[Dict[str, Any]]:
        if origin not in active_planets or destination not in active_planets:
            return None
        
        g_score: Dict[PlanetId, float] = {node: float("inf") for node in active_planets}
        previous: Dict[PlanetId, Optional[PlanetId]] = {node: None for node in active_planets}
        
        g_score[origin] = 0.0
        pq: List[Tuple[float, PlanetId]] = [(self._heuristic(origin, destination), origin)]
        enqueued_f: Dict[PlanetId, float] = {origin: g_score[origin]}

        while pq:
            curr_f, curr_node = heapq.heappop(pq)
            if curr_node == destination:
                break
            if curr_f > enqueued_f.get(curr_node, float("inf")):
                continue

            neighbors = self._static_topology.get(curr_node, {})
            for neighbor, edge_latency in neighbors.items():
                if neighbor not in active_planets:
                    continue
                if (curr_node, neighbor) in disabled_links or (neighbor, curr_node) in disabled_links:
                    continue


                tentative_g = g_score[curr_node] + edge_latency + self.tower_delay
                if tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    previous[neighbor] = curr_node
                    f_score = tentative_g + self._heuristic(neighbor, destination)
                    enqueued_f[neighbor] = f_score
                    heapq.heappush(pq, (f_score, neighbor))

        return self._build_packet_schema(origin, destination, g_score, previous, raw_message="")

    # PACKET GENERATION & DIALECT OUTPUT 
    def _build_packet_schema(self, origin: PlanetId, destination: PlanetId, 
                         costs: Dict[PlanetId, float], previous: Dict[PlanetId, Optional[PlanetId]], 
                         raw_message: str = "") -> Optional[Dict[str, Any]]:

        path: List[PlanetId] = []
        step: Optional[PlanetId] = destination
        while step is not None:
            path.insert(0, step)
            step = previous[step]

        if not path or path[0] != origin:
            return None

        final_latency = f1_score[destination] + self.tower_delay
        translated_payload = CodexTranscoder.encode_payload_for_planet(raw_message, self.planets[destination]["codex"])

        return {
            "origin_id": origin,
            "destination_id": destination,
            "current_id": destination,
            "payload": translated_payload,
            "meta_telemetry": {
                "total_latency_ms": round(final_latency, 4),
                "route_taken": path
            },
            "hop_log": self.reconstruct_hop_logs(path)
        }

    def _heuristic(self, current_id: PlanetId, target_id: PlanetId) -> float:
        p1, p2 = self.planets[current_id], self.planets[target_id]
        dist = math.sqrt(((p2["x"] - p1["x"]) * self.scale_unit)**2 + ((p2["y"] - p1["y"]) * self.scale_unit)**2)
        return (dist / self.c) * 1000.0
    
