import math
from .universe import Planet, Tower

#tower path latency calculation
def find_closest_tower_pair(origin: Planet, destination: Planet) -> tuple[Tower, Tower]:
    best_dist = float("inf")
    best_pair = (origin.towers[0], destination.towers[0])

    for t1 in origin.towers:
        for t2 in destination.towers:
            dist = math.hypot(t1.x - t2.x, t1.y - t2.y)
            if dist < best_dist:
                best_dist = dist
                best_pair = (t1, t2)

    return best_pair

#void distance calculation
def calc_void_distance(origin: Planet, destination: Planet) -> float:
    center_distance = math.hypot(
        destination.x - origin.x,
        destination.y - origin.y
    )

    L = (
        center_distance
        - (origin.radius_km + origin.atmosphere_thickness_km)
        - (destination.radius_km + destination.atmosphere_thickness_km)
    )

    # Clamp to 0 if planets are overlapping
    if L < 0:
        L = 0.0

    return L

#travel time calculation across the void
def calc_void_travel_time(
    origin: Planet,
    destination: Planet,
    L: float,
    speed_of_light_kms: float
) -> float:
   
    h1 = origin.atmosphere_thickness_km
    n1 = origin.refraction_index
    h2 = destination.atmosphere_thickness_km
    n2 = destination.refraction_index

    # Total effective distance including atmospheric refraction
    total_distance = (h1 * n1) + (h2 * n2) + L

    Tv_seconds = total_distance / speed_of_light_kms
    Tv_ms = Tv_seconds * 1000.0

    return Tv_ms

#fiber transit time calculation 

def calc_fiber_transit_time(
    planet: Planet,
    tower1_index: int,
    tower2_index: int,
    fiber_speed_fraction: float,
    speed_of_light_kms: float,
    tower_delay_ms: float
) -> tuple[float, int, int]:
 
    N = planet.active_towers
    r = planet.radius_km
    f = fiber_speed_fraction
    C = speed_of_light_kms
    delta_t = tower_delay_ms

    # Calculate shortest arc distance between towers
    if tower1_index == tower2_index:
        # Same tower - no arc traversal, but tower is still "hit" once
        s = 0
        m = 1
    else:
        # Different towers - find shortest path (clockwise or counter-clockwise)
        diff = abs(tower1_index - tower2_index)
        s = min(diff, N - diff)  # Shortest arc in segments
        m = s + 1                # Towers hit = segments + 1 (the path endpoints)

    # Arc length along the planet's equatorial fiber ring
    arc_length = 2 * math.pi * r * (s / N)

    # Fiber propagation speed (0.67c for typical fiber)
    fiber_speed_kms = f * C
    Tp_seconds = arc_length / fiber_speed_kms

    # Total time: propagation + tower processing delays
    Tp_ms = (Tp_seconds * 1000.0) + (m * delta_t)

    return Tp_ms, s, m

#single hop latency calculation
def calc_hop_latency(
    origin: Planet,
    destination: Planet,
    speed_of_light_kms: float,
    fiber_speed_fraction: float,
    tower_delay_ms: float,
    max_void_hop_km: float = 50_000_000.0,
    origin_entry_tower: int = 0,
    destination_exit_tower: int = 0
) -> dict:

#check if planets are alive
    if not origin.alive:
        raise RuntimeError(
            f"Cannot route from dead planet '{origin.id}'. "
            f"This planet is offline."
        )
    if not destination.alive:
        raise RuntimeError(
            f"Cannot route to dead planet '{destination.id}'. "
            f"This planet is offline."
        )
    
   #find closest tower pair between origin and destination
    send_tower, recv_tower = find_closest_tower_pair(origin, destination)

    # calculate void distance between origin and destination
    L = calc_void_distance(origin, destination)

    # check if the void distance exceeds the maximum allowed hop distance
    if L > max_void_hop_km:
        raise ValueError(
            f"Void distance {L:.0f} km between '{origin.id}' and '{destination.id}' "
            f"exceeds maximum {max_void_hop_km:.0f} km. "
            f"Direct hop impossible; route must use intermediate planets."
        )

    # calculate void travel time based on the void distance and speed of light
    Tv = calc_void_travel_time(origin, destination, L, speed_of_light_kms)

    # calculate fiber transit time on the origin planet
    Tp_origin, s_origin, m_origin = calc_fiber_transit_time(
        planet=origin,
        tower1_index=origin_entry_tower,
        tower2_index=send_tower.index,
        fiber_speed_fraction=fiber_speed_fraction,
        speed_of_light_kms=speed_of_light_kms,
        tower_delay_ms=tower_delay_ms
    )

    # calculate fiber transit time on the destination planet
    Tp_destination, s_dest, m_dest = calc_fiber_transit_time(
        planet=destination,
        tower1_index=recv_tower.index,
        tower2_index=destination_exit_tower,
        fiber_speed_fraction=fiber_speed_fraction,
        speed_of_light_kms=speed_of_light_kms,
        tower_delay_ms=tower_delay_ms
    )

    # total latency
    total_ms = Tp_origin + Tv + Tp_destination

    # return a dictionary containing all relevant latency information
    return {
        "origin": origin.id,
        "destination": destination.id,
        "send_tower": send_tower.index,
        "recv_tower": recv_tower.index,
        "origin_entry_tower": origin_entry_tower,
        "destination_exit_tower": destination_exit_tower,
        "void_distance_km": round(L, 3),
        "latency": {
            "fiber_origin_ms": round(Tp_origin, 4),
            "void_ms": round(Tv, 4),
            "fiber_destination_ms": round(Tp_destination, 4),
            "total_ms": round(total_ms, 4)
        },
        "segments": {
            "origin_segments": s_origin,
            "origin_towers_hit": m_origin,
            "destination_segments": s_dest,
            "destination_towers_hit": m_dest
        }
    }