# Relic Ring Protocol

A routing protocol simulation for the Zeta-26 star system, built for the IEEE Computer Society University of Kelaniya Hackathon (Launch 26).

---

## Setup

### Requirements

- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/KumodhiRajapura/relic-ring-protocol.git
cd relic-ring-protocol
pip install -r requirements.txt
```

### Running — Terminal Mode

```bash
python main.py
```

### Running — Web UI Mode

```bash
python api/app.py
```

Then open `http://localhost:5000` in your browser.

### Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
relic-ring-protocol/
│
├── core/
│   ├── universe.py       # Config loader, Planet, Tower classes
│   ├── latency.py        # Latency calculation (void, fiber, atmosphere)
│   ├── encoder.py        # Codex translation between planet dialects
│   ├── routing.py        # A* and Dijkstra shortest path algorithms
│   ├── network.py        # Orchestration and failure handling
│   └── packet.py         # Packet schema definition
│
├── api/
│   └── app.py            # Flask REST API for web UI
│
├── ui/
│   ├── visualizer.py     # Terminal visualizer
│   └── relic-ring-protocol.html  # Web UI star map
│
├── tests/
│   ├── test_encoder.py   # 14 encoder unit tests
│   ├── test_latency.py   # 13 latency unit tests
│   └── test_routing.py   # 10 routing unit tests
│
├── universe-config.json  # Zeta-26 system configuration
├── requirements.txt
└── main.py               # Entry point (terminal mode)
```

---

## Assumed Constants

All physical constants are read from `universe-config.json` under `universe_metadata`. The following defaults apply if a field is absent:

| Constant | Default Value |
|---|---|
| speed_of_light_kms | 300,000 km/s |
| max_void_hop_distance_km | 50,000,000 km |
| coordinate_scale_unit_km | 100,000 km/unit |
| tower_processing_delay_ms | 7 ms |
| fiber_speed_fraction | 0.67 |

---

## Core Modules

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         universe-config.json     │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │           universe.py            │
                    │   Planet · Tower · Universe      │
                    └──────┬─────────────┬────────────┘
                           │             │
           ┌───────────────▼──┐    ┌─────▼──────────────┐
           │    latency.py    │    │    encoder.py       │
           │  Tv · Tp · Fiber │    │  ASCII ↔ Codex      │
           └───────────────┬──┘    └─────┬───────────────┘
                           │             │
                    ┌──────▼─────────────▼──────────┐
                    │          routing.py             │
                    │     A* · Dijkstra · HopLog      │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │          network.py             │
                    │   Kill · Revive · Orchestrate   │
                    └──────┬───────────────┬──────────┘
                           │               │
              ┌────────────▼──┐    ┌───────▼────────────┐
              │    main.py    │    │     api/app.py      │
              │  Terminal UI  │    │    Flask REST API   │
              └───────────────┘    └────────┬────────────┘
                                            │
                                   ┌────────▼────────────┐
                                   │  relic-ring.html    │
                                   │   Web UI Star Map   │
                                   └─────────────────────┘
```
### universe.py

Loads `universe-config.json` and constructs all planetary objects. Validates config at load time — catches missing fields, duplicate IDs, invalid codex values, and insufficient tower counts.

**Tower placement:** Towers are placed at equal angular intervals starting from the top (positive y-axis, 90°), proceeding clockwise. Position is calculated at `radius + atmosphere_thickness` from the planet center.

**Coordinate scaling:** `x` and `y` values are multiplied by `coordinate_scale_unit_km` to obtain actual kilometers. `radius_km` is already in kilometers and is not scaled.

---

### latency.py

Calculates all latency components for a single planet-to-planet hop.

**Void Distance (L):**
```
L = √((x₂−x₁)² + (y₂−y₁)²) − (R₁+h₁) − (R₂+h₂)
```

**Void Travel Time (Tᵥ):**
```
Tᵥ = [ (h₁×n₁) + (h₂×n₂) + L ] / C
```

**Fiber Transit Time (Tₚ):**
```
arc = 2πr × (s/N)
Tₚ = arc / (f×C) + m×Δt
s = shortest arc segments
m = towers hit (s+1 for different towers, 1 for same tower)
```

**Total Latency:**
```
Total = Σ Tₚ(Pᵢ) + Σ Tᵥ(Pᵢ → Pᵢ₊₁)
```

---

### encoder.py

Handles all codex (numerical base) conversions between planets.

**Transmission flow:**
```
Raw payload → ASCII → Next-hop codex → Binary stream → Void → Destination codex → ASCII → Delivered
```

Key functions: `ascii_to_codex`, `codex_to_ascii`, `encode_string_to_codex`, `decode_codex_to_string`, `convert_payload_between_codex`.

Valid codex range: 2 to 36.

---

### routing.py

Implements A* and Dijkstra shortest-path algorithms over the planet graph.

- Network topology is precomputed at startup for all valid planet pairs (L ≤ Lmax).
- Active planet filtering and link failure handling are applied at query time — no topology rebuild required on kill/revive.
- A* uses a straight-line void distance heuristic (admissible — never overestimates).
- Physically impossible links (L > Lmax) are tracked and reported separately.

---

### network.py

Single entry point for all transmissions. Manages alive/dead state for planets and links. Delegates pathfinding to `RoutingEngine`.

---

### packet.py

Defines the `Packet` dataclass — the mandatory schema for all inter-planet transmissions.

Fields: `origin_id`, `destination_id`, `current_id`, `payload`, `hop_log`, `delivered`, `total_latency_ms`, `route_taken`.

---

### api/app.py

Flask REST API serving the web UI and exposing endpoints for transmission, chaos control, and universe state.

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves web UI |
| `/api/universe` | GET | Returns full universe state |
| `/api/transmit` | POST | Send a packet |
| `/api/planet/<id>/kill` | POST | Kill a planet |
| `/api/planet/<id>/revive` | POST | Revive a planet |
| `/api/link/kill` | POST | Sever a link |
| `/api/link/revive` | POST | Restore a link |
| `/api/reset` | POST | Reset universe |

---
