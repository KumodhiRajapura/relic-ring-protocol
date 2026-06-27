import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.network import NetworkOrchestrator

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "universe-config.json")


@pytest.fixture
def orchestrator():
    return NetworkOrchestrator(CONFIG_PATH)


class TestBasicRouting:
    def test_aegis_to_caelum(self, orchestrator):
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Hello world")
        assert result is not None
        assert result.origin_id == "Aegis"
        assert result.destination_id == "Caelum"
        assert result.payload != ""

    def test_route_exists(self, orchestrator):
        result = orchestrator.process_transmission_transaction("Aegis", "Boreas", "Test")
        assert result is not None
        assert "Aegis" in result.route_taken
        assert "Boreas" in result.route_taken

    def test_latency_positive(self, orchestrator):
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Hi")
        assert result.total_latency_ms > 0

    def test_hop_log_not_empty(self, orchestrator):
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Hi")
        assert len(result.hop_log) > 0

    def test_payload_encoded(self, orchestrator):
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Hi")
        assert result.payload != "Hi"


class TestNodeFailure:
    def test_kill_node_reroutes(self, orchestrator):
        result1 = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Test")
        route1 = result1.route_taken

        orchestrator.set_planet_operational_status("Dawn", False)
        result2 = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Test")

        assert result2 is not None
        assert "Dawn" not in result2.route_taken
        orchestrator.set_planet_operational_status("Dawn", True)

    def test_kill_origin_returns_none(self, orchestrator):
        orchestrator.set_planet_operational_status("Aegis", False)
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Test")
        assert result is None
        orchestrator.set_planet_operational_status("Aegis", True)

    def test_revive_restores_routing(self, orchestrator):
        orchestrator.set_planet_operational_status("Boreas", False)
        orchestrator.set_planet_operational_status("Boreas", True)
        result = orchestrator.process_transmission_transaction("Aegis", "Boreas", "Test")
        assert result is not None


class TestLinkFailure:
    def test_kill_link_reroutes(self, orchestrator):
        orchestrator.set_link_operational_status("Aegis", "Dawn", False)
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Test")
        assert result is not None
        route = result.route_taken
        hops = list(zip(route, route[1:]))
        assert ("Aegis", "Dawn") not in hops
        orchestrator.set_link_operational_status("Aegis", "Dawn", True)


class TestReset:
    def test_reset_restores_all(self, orchestrator):
        orchestrator.set_planet_operational_status("Dawn", False)
        orchestrator.set_link_operational_status("Aegis", "Boreas", False)
        orchestrator.reload_universe_configuration()
        result = orchestrator.process_transmission_transaction("Aegis", "Caelum", "Test")
        assert result is not None

class TestBlockedLinks:
    def test_get_blocked_links_returns_list(self, orchestrator):
        blocked = orchestrator.router.get_blocked_links()
        assert isinstance(blocked, list)

    def test_blocked_links_have_required_fields(self, orchestrator):
        blocked = orchestrator.router.get_blocked_links()
        for entry in blocked:
            assert "source" in entry
            assert "target" in entry
            assert "reason" in entry
            assert entry["reason"] == "void_distance_exceeds_lmax"

    def test_no_duplicate_pairs(self, orchestrator):
        blocked = orchestrator.router.get_blocked_links()
        pairs = [tuple(sorted((e["source"], e["target"]))) for e in blocked]
        assert len(pairs) == len(set(pairs))
