"""
Relic Ring Protocol — Terminal Visualizer
Renders the star system, routes, and transmission logs in the terminal.
"""
import math
import os
import sys


# ansi color helpers

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def bold(t):    return _c("1", t)
def dim(t):     return _c("2", t)
def red(t):     return _c("31", t)
def green(t):   return _c("32", t)
def yellow(t):  return _c("33", t)
def blue(t):    return _c("34", t)
def magenta(t): return _c("35", t)
def cyan(t):    return _c("36", t)
def white(t):   return _c("37", t)
def bright_blue(t):    return _c("94", t)
def bright_yellow(t):  return _c("93", t)
def bright_green(t):   return _c("92", t)
def bright_cyan(t):    return _c("96", t)
def bright_magenta(t): return _c("95", t)


PLANET_COLORS = [bright_cyan, bright_yellow, bright_green, bright_magenta,
                 yellow, blue, green, magenta]


def _color_for(planet_id: str, planets: list) -> callable:
    idx = next((i for i, p in enumerate(planets) if p["id"] == planet_id), 0)
    return PLANET_COLORS[idx % len(PLANET_COLORS)]


def print_header():
    print()
    print(bold(cyan("╔══════════════════════════════════════════════════════════════╗")))
    print(bold(cyan("║") + bright_yellow("          ✦  RELIC RING PROTOCOL — ZETA-26  ✦               ") + bold(cyan("║"))))
    print(bold(cyan("║") + dim("       IEEE CS UOK · Launch 26 · Interstellar Network        ") + bold(cyan("║"))))
    print(bold(cyan("╚══════════════════════════════════════════════════════════════╝")))
    print()


def visualize_universe(planets: list, topology: dict, dead_planets: set = None,
                       dead_links: set = None, active_route: list = None):
    """
    Draws an ASCII star-map of the universe.
    planets: list of planet dicts from config
    topology: {id: {id: latency_ms}}
    """
    dead_planets = dead_planets or set()
    dead_links = dead_links or set()
    active_route = active_route or []

    W, H = 70, 30

    # Find coordinate bounds
    xs = [p["x"] for p in planets]
    ys = [p["y"] for p in planets]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad = 0.1
    rx = (max_x - min_x) or 1
    ry = (max_y - min_y) or 1

    def to_screen(x, y):
        sx = int((x - min_x + pad * rx) / (rx * (1 + 2 * pad)) * (W - 1))
        sy = int((1 - (y - min_y + pad * ry) / (ry * (1 + 2 * pad))) * (H - 1))
        return max(0, min(W - 1, sx)), max(0, min(H - 1, sy))

    grid = [[" " for _ in range(W)] for _ in range(H)]
    color_grid = [[None for _ in range(W)] for _ in range(H)]

    # Draw topology links
    for src_id, neighbors in topology.items():
        for dst_id in neighbors:
            if dst_id <= src_id:
                continue
            p1 = next(p for p in planets if p["id"] == src_id)
            p2 = next(p for p in planets if p["id"] == dst_id)
            x1, y1 = to_screen(p1["x"], p1["y"])
            x2, y2 = to_screen(p2["x"], p2["y"])

            link = tuple(sorted((src_id, dst_id)))
            is_dead = link in dead_links
            is_active = (src_id in active_route and dst_id in active_route and
                         abs(active_route.index(src_id) - active_route.index(dst_id)) == 1)

            steps = max(abs(x2 - x1), abs(y2 - y1))
            if steps == 0:
                continue
            for step in range(1, steps):
                lx = x1 + int((x2 - x1) * step / steps)
                ly = y1 + int((y2 - y1) * step / steps)
                if 0 <= lx < W and 0 <= ly < H and grid[ly][lx] == " ":
                    if is_dead:
                        grid[ly][lx] = "✗"
                        color_grid[ly][lx] = "red"
                    elif is_active:
                        grid[ly][lx] = "═"
                        color_grid[ly][lx] = "bright_yellow"
                    else:
                        grid[ly][lx] = "·"
                        color_grid[ly][lx] = "dim"

    # Draw planets
    planet_positions = {}
    for i, p in enumerate(planets):
        sx, sy = to_screen(p["x"], p["y"])
        planet_positions[p["id"]] = (sx, sy)
        is_dead = p["id"] in dead_planets
        is_active = p["id"] in active_route

        symbol = "☠" if is_dead else ("◉" if is_active else "●")
        color_key = "red" if is_dead else ("bright_yellow" if is_active else "bright_cyan")

        grid[sy][sx] = symbol
        color_grid[sy][sx] = color_key

        # Label
        label = p["id"]
        lx = sx + 1
        for ci, ch in enumerate(label):
            if 0 <= lx + ci < W and 0 <= sy < H:
                grid[sy][lx + ci] = ch
                color_grid[sy][lx + ci] = color_key

    # Render
    color_fn_map = {
        "red": red, "bright_yellow": bright_yellow, "bright_cyan": bright_cyan,
        "dim": dim, "bright_green": bright_green,
    }

    print(bold("  " + "─" * W))
    for row_idx, row in enumerate(grid):
        line = "  │"
        for ci, ch in enumerate(row):
            cfn = color_fn_map.get(color_grid[row_idx][ci])
            line += cfn(ch) if cfn else ch
        line += bold("│")
        print(line)
    print(bold("  " + "─" * W))

    # Legend
    print()
    parts = []
    for i, p in enumerate(planets):
        cfn = red if p["id"] in dead_planets else (bright_yellow if p["id"] in active_route
                                                    else PLANET_COLORS[i % len(PLANET_COLORS)])
        marker = "☠" if p["id"] in dead_planets else "●"
        parts.append(cfn(f"{marker} {p['id']}") + dim(f"(B{p['codex']})"))
    print("  " + "  ".join(parts))
    print()


def print_universe_info(planets: list, metadata: dict):
    print(bold(cyan("\n┌─── Universe Configuration ──────────────────────────────────────┐")))
    print(f"  System      : {bright_yellow(metadata.get('system_name', 'Zeta-26'))}")
    print(f"  Speed of c  : {metadata.get('speed_of_light_kms', 300000):,.0f} km/s")
    print(f"  Lmax        : {metadata.get('max_void_hop_distance_km', 50e6)/1e6:.0f}M km")
    print(f"  Tower delay : {metadata.get('tower_processing_delay_ms', 7)} ms")
    print(f"  Fiber speed : {metadata.get('fiber_speed_fraction', 0.67)*100:.0f}% c")
    print(f"  Scale unit  : {metadata.get('coordinate_scale_unit_km', 100000):,} km/unit")
    print(bold(cyan("└─────────────────────────────────────────────────────────────────┘")))
    print()

    print(bold(cyan("┌─── Planetary Nodes ─────────────────────────────────────────────┐")))
    for i, p in enumerate(planets):
        cfn = PLANET_COLORS[i % len(PLANET_COLORS)]
        print(f"  {cfn('●')} {bold(p['id']):<10} "
              f"Codex:" + bright_yellow(f'B{p["codex"]}') + "  "
              f"Towers:{p['active_towers']}  "
              f"R:{p['radius_km']:,}km  "
              f"Atm:{p['atmosphere_thickness_km']}km  "
              f"n:{p['refraction_index']}")
    print(bold(cyan("└─────────────────────────────────────────────────────────────────┘")))
    print()


def print_topology_table(planets: list, topology: dict):
    ids = [p["id"] for p in planets]
    print(bold(cyan("\n┌─── Reachable Links (Void Distance ≤ 50M km) ───────────────────┐")))
    count = 0
    for src in ids:
        for dst in topology.get(src, {}):
            if dst > src:
                latency = topology[src][dst]
                print(f"  {bright_cyan(src):<12} ──── {bright_cyan(dst):<12}  Tv={yellow(f'{latency:.2f} ms')}")
                count += 1
    print(f"  {dim(f'Total links: {count}')}")
    print(bold(cyan("└─────────────────────────────────────────────────────────────────┘")))
    print()


def print_packet_result(result: dict, raw_message: str):
    """Pretty-print a full packet transmission result."""
    if not result:
        print(red("\n  ✗ TRANSMISSION FAILED — No valid route found."))
        return

    meta = result["meta_telemetry"]
    hops = result["hop_log"]
    route = meta["route_taken"]

    print()
    print(bold(green("┌─── PACKET DELIVERED ────────────────────────────────────────────┐")))
    print(f"  {bold('Origin')}      : {bright_cyan(result['origin_id'])}")
    print(f"  {bold('Destination')}: {bright_cyan(result['destination_id'])}")
    print(f"  {bold('Message')}     : {bright_yellow(repr(raw_message))}")
    route_str = " → ".join(bright_cyan(p) for p in route)
    print(f"  {bold('Route')}       : {route_str}")
    print(f"  {bold('Total Hops')} : {meta['hop_count']}")
    lat_str = bright_green(str(round(meta['total_latency_ms'], 4)) + " ms")
    print(f"  {bold('Total Latency')}: {lat_str}")
    print(bold(green("├─── Hop-by-Hop Log ──────────────────────────────────────────────┤")))

    total_fiber = 0.0
    total_void = 0.0
    total_tower = 0.0

    for hop in hops:
        lb = hop["latency_breakdown"]
        total_fiber += lb["fiber_arc_ms"]
        total_void += lb["void_pure_ms"] + lb["atmosphere_origin_ms"] + lb["atmosphere_dest_ms"]
        total_tower += lb["tower_delay_ms"]

        hop_num = hop["hop_index"] + 1
        tx = hop["tx_planet"]
        rx = hop["rx_planet"]
        txT = hop["tx_tower"]
        rxT = hop["rx_tower"]
        print()
        print(f"  {bold('HOP ' + str(hop_num))}: {bright_cyan(tx)}:{yellow(txT)} ──▶  {bright_cyan(rx)}:{yellow(rxT)}")
        print(f"    Void distance : {hop['void_distance_km']:,.2f} km")
        print(f"    Payload       : {dim(hop['payload_in_next_codex'])}")
        print(f"    Latency breakdown:")
        print(f"      Fiber arc   : {lb['fiber_arc_ms']:.4f} ms  ({lb['segments_traversed']} seg)")
        print(f"      Tower proc  : {lb['tower_delay_ms']:.4f} ms  ({lb['towers_hit']} towers)")
        print(f"      Atm origin  : {lb['atmosphere_origin_ms']:.4f} ms")
        print(f"      Pure void   : {lb['void_pure_ms']:.4f} ms")
        print(f"      Atm dest    : {lb['atmosphere_dest_ms']:.4f} ms")
        hop_str = bright_green(str(round(lb['hop_total_ms'], 4)) + " ms")
        print(f"      {bold('Hop total')}   : {hop_str}")

    print()
    print(bold(green("├─── Latency Summary ─────────────────────────────────────────────┤")))
    atm_total = sum(h["latency_breakdown"]["atmosphere_origin_ms"] + h["latency_breakdown"]["atmosphere_dest_ms"] for h in hops)
    void_total = sum(h["latency_breakdown"]["void_pure_ms"] for h in hops)
    print(f"  Fiber arcs  : {yellow(str(round(total_fiber, 4)) + ' ms')}")
    print(f"  Atmosphere  : {yellow(str(round(atm_total, 4)) + ' ms')}")
    print(f"  Pure void   : {yellow(str(round(void_total, 4)) + ' ms')}")
    print(f"  Tower proc  : {yellow(str(round(total_tower, 4)) + ' ms')}")
    total_str = bright_green(str(round(meta['total_latency_ms'], 4)) + " ms")
    print(f"  {bold('TOTAL')}       : {total_str}")
    print()
    print(f"  Final payload at {bright_cyan(result['destination_id'])} : {bright_yellow(result['payload'])}")
    print(bold(green("└─────────────────────────────────────────────────────────────────┘")))
    print()


def print_encoding_trace(raw_message: str, route: list, planets: list):
    """Print step-by-step encoding translation along the route."""
    CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def to_base_n(n, base):
        if n == 0:
            return "0"
        d = []
        while n:
            d.append(int(n % base))
            n //= base
        return "".join(CHARS[x] for x in reversed(d))

    planet_map = {p["id"]: p for p in planets}

    print()
    print(bold(magenta("┌─── Encoding Translation Trace ──────────────────────────────────┐")))
    print(f"  Raw message: {bright_yellow(repr(raw_message))}")
    ascii_vals = [ord(c) for c in raw_message]
    print(f"  ASCII      : {dim(str(ascii_vals))}")
    print()

    for i in range(len(route) - 1):
        src_id = route[i]
        dst_id = route[i + 1]
        dst = planet_map[dst_id]
        base = dst["codex"]
        encoded = [to_base_n(v, base) for v in ascii_vals]
        print(f"  {bright_cyan(src_id)} → {bright_cyan(dst_id)} "
              f"{dim(f'[encode to Base {base}]')}")
        print(f"    [{']  ['.join(encoded)}]")
        print()

    print(bold(magenta("└─────────────────────────────────────────────────────────────────┘")))
    print()


def print_chaos_event(event: str, detail: str, is_kill: bool = True):
    if is_kill:
        print(red(f"\n  ☠  CHAOS EVENT: {event}"))
        print(red(f"     {detail}"))
    else:
        print(bright_green(f"\n  ✦  REVIVAL: {event}"))
        print(bright_green(f"     {detail}"))
    print()
