import math
from .universe import Planet, Tower

# CLOSEST TOWER PAIR

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

#calculate void distance between two planets
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

    if L < 0:
        L = 0.0

    return L

#calculate void travel time between two planets
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

    total_distance = (h1 * n1) + (h2 * n2) + L

    Tv_seconds = total_distance / speed_of_light_kms
    Tv_ms = Tv_seconds * 1000.0

    return Tv_ms

#calculate fiber transit time between two towers on the same planet
def calc_fiber_transit_time(
    planet: Planet,
    send_tower_index: int,
    recv_tower_index: int,
    fiber_speed_fraction: float,
    speed_of_light_kms: float,
    tower_delay_ms: float
) -> tuple[float, int, int]:
 
    N = planet.active_towers
    r = planet.radius_km
    f = fiber_speed_fraction
    C = speed_of_light_kms
    delta_t = tower_delay_ms

    if send_tower_index == recv_tower_index:
        # Same tower, no arc segments
        s = 0
        m = 1
    else:
        # Calculate the shortest arc distance between the two towers
        diff = abs(send_tower_index - recv_tower_index)
        s = min(diff, N - diff)
        m = s + 1

    # Arc length along planet surface ring
    arc_length = 2 * math.pi * r * (s / N)

    # Fiber travel time
    fiber_speed_kms = f * C
    Tp_seconds = arc_length / fiber_speed_kms

    # Add tower processing delays
    Tp_ms = (Tp_seconds * 1000.0) + (m * delta_t)

    return Tp_ms, s, m

#calculate hop latency between two planets
def calc_hop_latency(
    origin: Planet,
    destination: Planet,
    speed_of_light_kms: float,
    fiber_speed_fraction: float,
    tower_delay_ms: float
) -> dict:

    # close tower pair
    send_tower, recv_tower = find_closest_tower_pair(origin, destination)

    # Void distance
    L = calc_void_distance(origin, destination)

    # minimum number of towers hit on origin planet

    # void travel time
    Tv = calc_void_travel_time(origin, destination, L, speed_of_light_kms)

    # fiber transit time on origin planet
    Tp_origin, s_origin, m_origin = calc_fiber_transit_time(
        planet=origin,
        send_tower_index=0,
        recv_tower_index=send_tower.index,
        fiber_speed_fraction=fiber_speed_fraction,
        speed_of_light_kms=speed_of_light_kms,
        tower_delay_ms=tower_delay_ms
    )

    # Destination planet
    Tp_destination, s_dest, m_dest = calc_fiber_transit_time(
        planet=destination,
        send_tower_index=recv_tower.index,
        recv_tower_index=0,
        fiber_speed_fraction=fiber_speed_fraction,
        speed_of_light_kms=speed_of_light_kms,
        tower_delay_ms=tower_delay_ms
    )

    total_ms = Tp_origin + Tv + Tp_destination

    return {
        "origin": origin.id,
        "destination": destination.id,
        "send_tower": send_tower.index,
        "recv_tower": recv_tower.index,
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
