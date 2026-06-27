import json
import logging
from typing import Dict, Optional, Set, Any

from .routing import RoutingEngine, PlanetId, LinkId

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RelicRingNetwork")


class NetworkOrchestrator:
    def __init__(self, config_filepath: str):
        self.config_filepath = config_filepath
        self.raw_metadata: Dict[str, Any] = {}
        self.planets_registry: Dict[PlanetId, Dict[str, Any]] = {}
        self.active_planets: Set[PlanetId] = set()
        self.disabled_links: Set[LinkId] = set()
        self.router: Optional[RoutingEngine] = None

        self.reload_universe_configuration()

    def reload_universe_configuration(self) -> None:
        try:
            logger.info(f"Loading universe configuration from: {self.config_filepath}")
            with open(self.config_filepath, "r") as file:
                config_data = json.load(file)

            self.raw_metadata = config_data["universe_metadata"]
            self.planets_registry = {p["id"]: p for p in config_data["nodes"]}

            self.active_planets = set(self.planets_registry.keys())
            self.disabled_links.clear()

            self.router = RoutingEngine(self.planets_registry, self.raw_metadata)
            logger.info("Universe loaded successfully.")

        except Exception as e:
            logger.critical(f"Failed to load universe: {str(e)}")
            raise

    def set_planet_operational_status(self, planet_id: PlanetId, is_online: bool) -> bool:
        if planet_id not in self.planets_registry:
            return False
        if is_online:
            self.active_planets.add(planet_id)
        else:
            self.active_planets.discard(planet_id)
        return True

    def set_link_operational_status(self, src: PlanetId, dst: PlanetId, is_online: bool) -> bool:
        if src not in self.planets_registry or dst not in self.planets_registry:
            return False
        link_tuple = tuple(sorted((src, dst)))
        if is_online:
            self.disabled_links.discard(link_tuple)
        else:
            self.disabled_links.add(link_tuple)
        return True

    def process_transmission_transaction(
        self,
        origin: PlanetId,
        destination: PlanetId,
        raw_message: str
    ) -> Optional[Dict[str, Any]]:
        if not self.router:
            return None

        if origin not in self.active_planets or destination not in self.active_planets:
            logger.error(f"Transmission dropped: planet offline ({origin} -> {destination})")
            return None

        packet = self.router.find_route_astar(
            origin=origin,
            destination=destination,
            active_planets=self.active_planets,
            disabled_links=self.disabled_links,
            raw_message=raw_message
        )

        if packet:
            logger.info(
                f"Packet delivered via {packet['meta_telemetry']['route_taken']} "
                f"| Latency: {packet['meta_telemetry']['total_latency_ms']} ms"
            )
        else:
            logger.warning(f"No route found: {origin} -> {destination}")

        return packet
