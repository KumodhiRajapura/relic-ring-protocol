import json
import math
import os


class Tower:
    def __init__(self, index: int, planet):
        self.index = index
        self.planet = planet

        n = planet.active_towers
        angle_deg = 90.0 - (360.0 / n) * index
        angle_rad = math.radians(angle_deg)
        surface = planet.radius_km + planet.atmosphere_thickness_km

        self.x = planet.x + surface * math.cos(angle_rad)
        self.y = planet.y + surface * math.sin(angle_rad)

    def __repr__(self):
        return f"Tower(planet={self.planet.id}, index={self.index})"


class Planet:
    def __init__(self, data: dict, scale_km: float):
        self.id = data["id"]
        self.codex = data["codex"]
        self.x = data["x"] * scale_km
        self.y = data["y"] * scale_km
        self.radius_km = data["radius_km"]
        self.active_towers = data["active_towers"]
        self.atmosphere_thickness_km = data["atmosphere_thickness_km"]
        self.refraction_index = data["refraction_index"]
        self.alive = True

        self.towers: list[Tower] = [
            Tower(i, self) for i in range(self.active_towers)
        ]

    def get_tower(self, index: int) -> Tower:
        return self.towers[index]

    def __repr__(self):
        return f"Planet({self.id}, codex={self.codex})"


class Universe:
    def __init__(self, config_path: str):
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Universe config not found: '{config_path}'. "
                f"Please provide a valid universe-config.json file."
            )

        with open(config_path, "r") as f:
            config = json.load(f)

        meta = config["universe_metadata"]

        self.system_name = meta["system_name"]
        self.speed_of_light_kms = meta.get("speed_of_light_kms", 300000.0)
        self.max_void_hop_km = meta.get("max_void_hop_distance_km", 50_000_000.0)
        self.scale_km = meta.get("coordinate_scale_unit_km", 100_000.0)
        self.tower_delay_ms = meta.get("tower_processing_delay_ms", 7.0)
        self.fiber_speed_fraction = meta.get("fiber_speed_fraction", 0.67)

        self.planets: dict[str, Planet] = {}
        for node in config["nodes"]:
            planet = Planet(node, self.scale_km)
            self.planets[planet.id] = planet

        print(f"Universe '{self.system_name}' loaded - {len(self.planets)} planets found.")

    def get_planet(self, planet_id: str) -> Planet:
        if planet_id not in self.planets:
            raise ValueError(f"Planet '{planet_id}' not found in universe.")
        return self.planets[planet_id]

    def all_planets(self) -> list[Planet]:
        return list(self.planets.values())

    def kill_planet(self, planet_id: str):
        self.get_planet(planet_id).alive = False
        print(f"Planet '{planet_id}' has been killed.")

    def revive_planet(self, planet_id: str):
        self.get_planet(planet_id).alive = True
        print(f"Planet '{planet_id}' revived.")

    def alive_planets(self) -> list[Planet]:
        return [p for p in self.planets.values() if p.alive]
