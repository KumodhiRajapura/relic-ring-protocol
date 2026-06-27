# ✦ Relic Ring Protocol — Zeta-26 Interstellar Network

**IEEE CS University of Kelaniya · Launch 26**

A simulation of a star-system-wide routing protocol built on primitive physical infrastructure — underground fiber cables and laser transceivers — reconnecting planets of the Zeta-26 system after the Hyper-Flare of 3704 destroyed the quantum Aether-Net.

---

## Setup

**Requirements:** Python 3.10+

```bash
pip install flask flask-cors
cd relic-ring-protocol

# Run the interactive CLI
python3 main.py

# Or run the web API
python3 -m api.app
```

---

## Running the System

On launch you will see:
1. **Universe initialization** — config parsed, planets loaded, topology precomputed
2. **Star-map** — ASCII visualization of the Zeta-26 system
3. **Mission Control menu** with 10 options

### CLI Menu Options

| Key | Action |
|-----|--------|
| `1` | Send a message between any two planets |
| `2` | View the live star-map and topology table |
| `3` | **Chaos test** — kill a planet (node failure) |
| `4` | Revive a planet |
| `5` | **Chaos test** — sever a link (link failure) |
| `6` | Restore a link |
| `7` | Show full planet & network details |
| `8` | Run the built-in demo (`Hello world`: Aegis → Caelum) |
| `9` | Reset universe (restore all nodes & links) |
| `0` | Exit |

---

## Web API Endpoints

The Flask API (`api/app.py`) exposes the full protocol over HTTP.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/universe` | Full topology — planets, links, blocked links, active state |
| `POST` | `/api/transmit` | Send a message `{origin, destination, message}` |
| `POST` | `/api/planet/<id>/kill` | Take a planet offline |
| `POST` | `/api/planet/<id>/revive` | Bring a planet back online |
| `POST` | `/api/link/kill` | Sever a link `{source, target}` |
| `POST` | `/api/link/revive` | Restore a link `{source, target}` |
| `POST` | `/api/reset` | Restore all nodes and links |

### `/api/universe` Response Fields

- `links` — reachable planet pairs with `latency_ms` and `void_latency_ms`
- `blocked_links` — pairs physically unreachable because `L > Lmax` (50,000,000 km), each with `reason: "void_distance_exceeds_lmax"`
- `active_planets` — currently online planet IDs
- `disabled_links` — operator-severed links

---

## Architecture

```
relic-ring-protocol/
├── main.py                  # Interactive CLI entry point
├── universe-config.json     # Universe definition (planets, metadata)
├── api/
│   └── app.py               # Flask REST API
├── core/
│   ├── universe.py          # Planet / Tower / Universe data model + config validator
│   ├── routing.py           # A* + Dijkstra routing engine, latency formulas
│   ├── network.py           # NetworkOrchestrator (node/link failure control)
│   ├── encoder.py           # Codex (base-N) encoding/decoding utilities
│   └── packet.py            # Packet dataclass
├── tests/
│   ├── test_encoder.py      # 20 tests — ascii↔codex, encode_payload_as_string
│   ├── test_latency.py      # 18 tests — void distance, fiber arc, hop latency, validator
│   └── test_routing.py      # 13 tests — routing, kill/revive, link failure, blocked links
└── ui/
    └── visualizer.py        # ANSI terminal star-map and packet log renderer
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

51 tests across encoder, latency, routing, config validator, and blocked-link detection.

---

## Config Validation

`universe.py` validates `universe-config.json` at load time and raises descriptive errors for:

- Missing required fields (`id`, `codex`, `x`, `y`, `radius_km`, `active_towers`, `atmosphere_thickness_km`, `refraction_index`)
- Duplicate planet IDs
- `codex` outside 2–36
- `active_towers < 4` (spec requirement)
- `radius_km ≤ 0`
- `atmosphere_thickness_km < 0`
- `refraction_index ≤ 0`

---

## Latency Model

All physical constants are read from `universe_metadata` in the config — nothing is hardcoded.

### 1. Void Distance (L)

```
L = sqrt((x2−x1)² + (y2−y1)²) × S  −  (R1+h1)  −  (R2+h2)
```

Where `S = coordinate_scale_unit_km`. Hops with `L > Lmax` (50,000,000 km) are rejected.

### 2. Void Travel Time (Tv)

```
Tv = (h1×n1 + h2×n2 + L) / c
```

Atmospheric refraction is modeled as the signal passing straight through each atmosphere at thickness `h`, slowed by refraction index `n`. Both entry and exit atmospheres are accounted for.

### 3. Fiber Arc Transit (Tp)

```
Arc length = 2πr × (s/N)
Tp = arc_length / (f × c)  +  m × Δt
```

- `s` = number of ring segments traversed (shortest arc)
- `m` = number of towers hit (`s+1` for different towers; `1` if same tower — dedup per spec)
- `Δt` = tower processing delay (7 ms default)
- `f` = fiber speed fraction (0.67c default)

### 4. Total Route Latency

```
Total = Σ Tp(planet_i)  +  Σ Tv(planet_i → planet_{i+1})
```

One `Tp` per planet visited, one `Tv` per void hop.

### Assumed Constants (defaults if not in config)

| Constant | Default | Justification |
|----------|---------|---------------|
| `speed_of_light_kms` | 300,000 km/s | Physical constant in vacuum |
| `max_void_hop_distance_km` | 50,000,000 km | Spec constraint (Lmax) |
| `tower_processing_delay_ms` | 7 ms | Spec default |
| `fiber_speed_fraction` | 0.67 | Typical silica fiber propagation speed |
| `coordinate_scale_unit_km` | 100,000 km | Spec default |

---

## Data Encoding & Transmission Flow

```
Origin planet (ASCII internally)
  → convert payload to next-hop planet's codex (base-N)
  → serialize as binary stream
  → laser across void (L km)
  → relay planet receives in its codex
  → decodes to ASCII for internal routing
  → re-encodes for next hop codex
  → ... repeat until destination
  → destination decodes to ASCII → delivers message
```

Each hop log entry records:
- `tx_planet` / `rx_planet` — sending and receiving planets
- `tx_tower` / `rx_tower` — which towers physically sent and received
- `ascii_intermediate` — ASCII values of the message at this relay (proving decode step)
- `payload_in_next_codex` — encoded form transmitted across the void
- `latency_breakdown` — fiber arc, tower delays, atmosphere, void, per component

### Tower Placement

Towers are placed at equal angular intervals starting from the top (positive y-axis = 90°), numbered clockwise:

```
Tower i  →  angle = 90° − (360°/N) × i
Position →  (cx + r·cos(angle), cy + r·sin(angle))
```

### Line-of-Sight (LoS) Rule

The tower pair (one per planet) whose positions minimize straight-line distance between them is selected as the send/receive pair for each void hop. This determines `tx_tower` / `rx_tower` in the hop log and the fiber arc path on each planet.

> **Simplification (per spec):** The void distance `L` is computed center-to-center minus atmosphere boundaries, independent of which towers are selected. Tower position affects only internal fiber arc routing and hop log reporting.

---

## Dynamic Rerouting

The routing engine (A*) works on a live set of `active_planets` and `disabled_links`. When you kill a planet or link:
- It is instantly removed from the routing graph
- The next transmission automatically finds an alternative route
- If no route exists, the packet is reported as **undeliverable**

---

## Zeta-26 Star System

| Planet | Codex | Towers | Notes |
|--------|-------|--------|-------|
| Aegis | Base 8 | 8 | Origin world |
| Boreas | Base 5 | 4 | Thin atmosphere relay |
| Dawn | Base 6 | 6 | Key mid-system relay |
| Elysium | Base 10 | 12 | Dense atmosphere |
| Fenix | Base 16 | 4 | Outer fast relay |
| Caelum | Base 14 | 16 | Gas giant, far edge |
