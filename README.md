# relic-ring-protocol
IEEE CS Hackathon - Zeta-26 star system routing protocol

markdown# Relic Ring Protocol

A routing protocol simulation for the Zeta-26 star system, built for the IEEE Computer Society University of Kelaniya Hackathon (Launch 26).

---

## Setup

### Requirements

- Python 3.11+

### Installation

```bash
git clone https://github.com/KumodhiRajapura/relic-ring-protocol.git
cd relic-ring-protocol
```

### Running

```bash
python main.py
```

---

## Project Structure
relic-ring-protocol/

│

├── core/

│   ├── init.py

│   ├── universe.py          # Config loader, Planet, Tower classes

│   ├── latency.py           # Latency calculation (void, fiber, atmosphere)

│   ├── encoder.py           # Codex translation between planet dialects

│   ├── routing.py           # Shortest path algorithm (Dijkstra)

│   ├── network.py           # Graph management and failure handling

│   └── packet.py            # Packet schema definition

│

├── ui/

│   └── visualizer.py        # Network visualization

│

├── universe-config.json     # Zeta-26 system configuration

├── main.py                  # Entry point

└── README.md

---

## Core Modules

### universe.py

Responsible for loading the universe configuration and constructing all planetary objects.

**Classes:**

**Tower**
- Represents a single routing tower placed on a planet's surface.
- Position is calculated using angular placement starting from the top (positive y-axis, 90 degrees), proceeding clockwise.
- Tower coordinates are computed as:
  - surface = radius + atmosphere_thickness
  - x = planet_x + surface * cos(angle)
  - y = planet_y + surface * sin(angle)

**Planet**
- Represents a node in the universe graph.
- Stores physical properties: codex, coordinates (scaled to km), radius, atmosphere thickness, and refraction index.
- Coordinates are scaled using coordinate_scale_unit_km from universe metadata.
- radius_km is not scaled as it is already provided in kilometers.
- Maintains an alive flag for failure simulation.
- Instantiates all Tower objects on initialization.

**Universe**
- Parses universe-config.json and constructs all Planet objects.
- All physical constants (speed of light, max void hop distance, fiber speed fraction, tower delay) are read from universe_metadata — no values are hardcoded.
- Provides utility methods:
  - get_planet(id) — O(1) lookup by planet ID
  - kill_planet(id) — marks a planet as dead for resilience testing
  - revive_planet(id) — restores a planet to active state
  - alive_planets() — returns only currently active planets

**Assumed Constants (defaults if not in config):**

| Constant | Default Value |
| speed_of_light_kms | 300,000 km/s |
| max_void_hop_distance_km | 50,000,000 km |
| coordinate_scale_unit_km | 100,000 km |
| tower_processing_delay_ms | 7 ms |
| fiber_speed_fraction | 0.67 |

---

### latency.py

Calculates all latency components for a single planet-to-planet hop.

**Functions:**

**find_closest_tower_pair(origin, destination)**
- Iterates over all tower combinations between two planets.
- Returns the pair with the minimum straight-line distance.
- Used to determine which towers physically send and receive the laser signal (line-of-sight rule).

**calc_void_distance(origin, destination)**
- Computes the actual vacuum gap between two planets.
- Formula:
  - L = sqrt((x2-x1)^2 + (y2-y1)^2) - (R1 + h1) - (R2 + h2)
- Center-to-center distance minus both planets' surface boundaries (radius + atmosphere).

**calc_void_travel_time(origin, destination, L, C)**
- Computes signal travel time across the void including atmospheric refraction on both sides.
- Formula:
  - Tv = [ (h1 x n1) + (h2 x n2) + L ] / C
- Returns time in milliseconds.

**calc_fiber_transit_time(planet, send_tower_index, recv_tower_index, ...)**
- Computes travel time along the planet's equatorial fiber ring between two towers.
- Formula:
  - arc_length = 2 x pi x r x (s / N)
  - Tp = arc_length / (f x C) + m x delta_t
- Shortest arc is used (clockwise or counter-clockwise, whichever is smaller).
- Tower hit count (m):
  - Same tower: m = 1
  - Different towers: m = s + 1
- Returns time in milliseconds, segment count, and tower hit count.

**calc_hop_latency(origin, destination, ...)**
- Orchestrates a full single-hop latency calculation.
- Returns a structured breakdown:

```json
{
  "origin": "Aegis",
  "destination": "Boreas",
  "send_tower": 2,
  "recv_tower": 1,
  "void_distance_km": 17540210.5,
  "latency": {
    "fiber_origin_ms": 0.0023,
    "void_ms": 58.6,
    "fiber_destination_ms": 0.0018,
    "total_ms": 58.6041
  },
  "segments": {
    "origin_segments": 1,
    "origin_towers_hit": 2,
    "destination_segments": 0,
    "destination_towers_hit": 1
  }
}
```

---

*More modules will be documented as implementation progresses.*