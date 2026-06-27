import math
import heapq
from typing import Dict, List, Optional, Set, Tuple, Any
from core.latency import calc_fiber_transit_time, calc_void_travel_time
from core.encoder import encode_payload_as_string
from core.packet import Packet

PlanetId = str
LinkId = Tuple[PlanetId, PlanetId]
Milliseconds = float
Radians = float


class RoutingEngine:
    def __init__(self, planets, metadata: Dict[str, Any]):
        self.planets = planets
        self.metadata = metadata

        self.c: float = float(metadata.get("speed_of_light_kms", 300000.0))
        self.l_max: float = float(metadata.get("max_void_hop_distance_km", 50_000_000.0))
        self.tower_delay: float = float(metadata.get("tower_processing_delay_ms", 7.0))
        self.scale_unit: float = float(metadata.get("coordinate_scale_unit_km", 100_000.0))
        self.fiber_fraction: float = float(metadata.get("fiber_speed_fraction", 0.67))

        self._void_latency: Dict[PlanetId, Dict[PlanetId, Milliseconds]] = {}
        self._static_topology: Dict[PlanetId, Dict[PlanetId, Milliseconds]] = {}
        self._precompute_network_topology()

    def _precompute_network_topology(self) -> None:
        for p1_id in self.planets:
            self._void_latency[p1_id] = {}
            self._static_topology[p1_id] = {}
            for p2_id in self.planets:
                if p1_id == p2_id:
                    continue
                result = self._compute_hop_latency(p1_id, p2_id)
                if result is not None:
                    void_lat, total_lat = result
                    self._void_latency[p1_id][p2_id] = void_lat
                    self._static_topology[p1_id][p2_id] = total_lat

    def _compute_hop_latency(self, p1_id: PlanetId, p2_id: PlanetId) -> Optional[Tuple[Milliseconds, Milliseconds]]:
        """Returns (void_only_ms, full_hop_ms) or None if hop is impossible."""
        p1, p2 = self.planets[p1_id], self.planets[p2_id]

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        center_dist = math.sqrt(dx * dx + dy * dy)

        L = center_dist \
            - (p1.radius_km + p1.atmosphere_thickness_km) \
            - (p2.radius_km + p2.atmosphere_thickness_km)

        if L < 0 or L > self.l_max:
            return None

        Tv_ms = (
            (p1.atmosphere_thickness_km * p1.refraction_index)
            + (p2.atmosphere_thickness_km * p2.refraction_index)
            + L
        ) / self.c * 1000.0

        send_t, recv_t = self._closest_tower_pair(p1_id, p2_id)
        Tp_origin_ms, _, _ = self._fiber_arc_ms(p1_id, 0, send_t)
        Tp_dest_ms, _, _ = self._fiber_arc_ms(p2_id, recv_t, 0)

        total_ms = Tp_origin_ms + Tv_ms + Tp_dest_ms
        return Tv_ms, total_ms

    def _tower_angle(self, tower_idx: int, total_towers: int) -> Radians:
        return math.radians(90.0 - (360.0 / total_towers) * tower_idx)

    def _tower_position(self, planet_id: PlanetId, tower_idx: int) -> Tuple[float, float]:
        p = self.planets[planet_id]
        a = self._tower_angle(tower_idx, p.active_towers)
        return p.x + p.radius_km * math.cos(a), p.y + p.radius_km * math.sin(a)

    def _closest_tower_pair(self, src_id: PlanetId, dst_id: PlanetId) -> Tuple[int, int]:
        p1, p2 = self.planets[src_id], self.planets[dst_id]
        best_dist = float("inf")
        best = (0, 0)
        for t1 in range(p1.active_towers):
            x1, y1 = self._tower_position(src_id, t1)
            for t2 in range(p2.active_towers):
                x2, y2 = self._tower_position(dst_id, t2)
                d = (x2 - x1) ** 2 + (y2 - y1) ** 2
                if d < best_dist:
                    best_dist = d
                    best = (t1, t2)
        return best

    def _fiber_arc_ms(self, planet_id: PlanetId, from_tower: int, to_tower: int) -> Tuple[float, int, int]:
        return calc_fiber_transit_time(
            self.planets[planet_id], from_tower, to_tower,
            self.fiber_fraction, self.c, self.tower_delay
        )

    def _heuristic(self, current_id: PlanetId, target_id: PlanetId) -> float:
        p1, p2 = self.planets[current_id], self.planets[target_id]
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return (math.sqrt(dx * dx + dy * dy) / self.c) * 1000.0

    def find_route_astar(
        self,
        origin: PlanetId,
        destination: PlanetId,
        active_planets: Set[PlanetId],
        disabled_links: Set[LinkId],
        raw_message: str
    ) -> Optional[Dict[str, Any]]:
        if origin not in active_planets or destination not in active_planets:
            return None

        g_score: Dict[PlanetId, float] = {n: float("inf") for n in active_planets}
        previous: Dict[PlanetId, Optional[PlanetId]] = {n: None for n in active_planets}

        g_score[origin] = 0.0
        pq: List[Tuple[float, PlanetId]] = [(self._heuristic(origin, destination), origin)]
        best_f: Dict[PlanetId, float] = {origin: self._heuristic(origin, destination)}

        while pq:
            curr_f, curr_node = heapq.heappop(pq)
            if curr_node == destination:
                break
            if curr_f > best_f.get(curr_node, float("inf")):
                continue

            for neighbor, total_latency in self._static_topology.get(curr_node, {}).items():
                if neighbor not in active_planets:
                    continue
                link = tuple(sorted((curr_node, neighbor)))
                if link in disabled_links:
                    continue

                tentative_g = g_score[curr_node] + total_latency
                if tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    previous[neighbor] = curr_node
                    f = tentative_g + self._heuristic(neighbor, destination)
                    best_f[neighbor] = f
                    heapq.heappush(pq, (f, neighbor))

        return self._build_packet(origin, destination, previous, raw_message)

    def find_route_dijkstra(
        self,
        origin: PlanetId,
        destination: PlanetId,
        active_planets: Set[PlanetId],
        disabled_links: Set[LinkId],
        raw_message: str = ""
    ) -> Optional[Dict[str, Any]]:
        if origin not in active_planets or destination not in active_planets:
            return None

        dist: Dict[PlanetId, float] = {n: float("inf") for n in active_planets}
        previous: Dict[PlanetId, Optional[PlanetId]] = {n: None for n in active_planets}
        dist[origin] = 0.0
        pq = [(0.0, origin)]

        while pq:
            d, curr = heapq.heappop(pq)
            if d > dist[curr]:
                continue
            if curr == destination:
                break
            for neighbor, latency in self._static_topology.get(curr, {}).items():
                if neighbor not in active_planets:
                    continue
                link = tuple(sorted((curr, neighbor)))
                if link in disabled_links:
                    continue
                nd = d + latency
                if nd < dist[neighbor]:
                    dist[neighbor] = nd
                    previous[neighbor] = curr
                    heapq.heappush(pq, (nd, neighbor))

        return self._build_packet(origin, destination, previous, raw_message)

    def _build_packet(
        self,
        origin: PlanetId,
        destination: PlanetId,
        previous: Dict[PlanetId, Optional[PlanetId]],
        raw_message: str
    ) -> Optional[Dict[str, Any]]:
        path: List[PlanetId] = []
        step: Optional[PlanetId] = destination
        while step is not None:
            path.insert(0, step)
            step = previous.get(step)

        if not path or path[0] != origin:
            return None

        hop_log, total_latency_ms = self._reconstruct_hop_logs(path, raw_message)

        dest_codex = self.planets[destination].codex
        final_payload = encode_payload_as_string(raw_message, dest_codex)

        return Packet(
            origin_id=origin,
            destination_id=destination,
            current_id=destination,
            payload=final_payload,
            hop_log=hop_log,
            delivered=True,
            total_latency_ms=round(total_latency_ms, 4),
            route_taken=path,
        )

    def _reconstruct_hop_logs(
        self,
        path: List[PlanetId],
        raw_message: str
    ) -> Tuple[List[Dict], float]:
        hop_log = []
        total_ms = 0.0
        entry_tower: Dict[PlanetId, int] = {path[0]: 0}

        for i in range(len(path) - 1):
            curr_id = path[i]
            next_id = path[i + 1]
            curr_planet = self.planets[curr_id]
            next_planet = self.planets[next_id]

            send_t, recv_t = self._closest_tower_pair(curr_id, next_id)
            in_t = entry_tower.get(curr_id, 0)

            Tp_origin_ms, s_origin, m_origin = self._fiber_arc_ms(curr_id, in_t, send_t)
            Tv_ms = self._void_latency[curr_id][next_id]

            if i == len(path) - 2:
                Tp_dest_ms = self.tower_delay
                m_dest = 1
                s_dest = 0
            else:
                Tp_dest_ms = 0.0
                m_dest = 0
                s_dest = 0

            h1 = curr_planet.atmosphere_thickness_km
            n1 = curr_planet.refraction_index
            h2 = next_planet.atmosphere_thickness_km
            n2 = next_planet.refraction_index

            dx = next_planet.x - curr_planet.x
            dy = next_planet.y - curr_planet.y
            center_dist = math.sqrt(dx * dx + dy * dy)
            L = max(center_dist - (curr_planet.radius_km + h1) - (next_planet.radius_km + h2), 0.0)

            t_atm_origin_ms = (h1 * n1 / self.c) * 1000.0
            t_void_pure_ms = (L / self.c) * 1000.0
            t_atm_dest_ms = (h2 * n2 / self.c) * 1000.0

            next_codex = next_planet.codex
            hop_payload = encode_payload_as_string(raw_message, next_codex)

            hop_total = Tp_origin_ms + Tv_ms + Tp_dest_ms
            total_ms += hop_total

            hop_log.append({
                "hop_index": i,
                "tx_planet": curr_id,
                "rx_planet": next_id,
                "tx_tower": f"T_{send_t}",
                "rx_tower": f"T_{recv_t}",
                "payload_in_next_codex": f"[Base {next_codex}] {hop_payload}",
                "latency_breakdown": {
                    "fiber_arc_ms": round(Tp_origin_ms - m_origin * self.tower_delay, 4),
                    "tower_delay_ms": round((m_origin + m_dest) * self.tower_delay, 4),
                    "towers_hit": m_origin + m_dest,
                    "segments_traversed": s_origin,
                    "atmosphere_origin_ms": round(t_atm_origin_ms, 4),
                    "void_pure_ms": round(t_void_pure_ms, 4),
                    "atmosphere_dest_ms": round(t_atm_dest_ms, 4),
                    "total_void_ms": round(Tv_ms, 4),
                    "fiber_dest_ms": round(Tp_dest_ms, 4),
                    "hop_total_ms": round(hop_total, 4),
                },
                "void_distance_km": round(L, 2),
            })

            entry_tower[next_id] = recv_t

        return hop_log, total_ms

    def get_topology(self) -> Dict[PlanetId, Dict[PlanetId, float]]:
        return self._static_topology

    def get_void_topology(self) -> Dict[PlanetId, Dict[PlanetId, float]]:
        """Returns void-only latencies, useful for UI link weight display."""
        return self._void_latency