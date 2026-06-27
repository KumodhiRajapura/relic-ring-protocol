import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.universe import Universe, Planet, Tower
from core.latency import (
    find_closest_tower_pair, calc_void_distance,
    calc_void_travel_time, calc_fiber_transit_time,
    calc_hop_latency
)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "universe-config.json")


@pytest.fixture
def universe():
    return Universe(CONFIG_PATH)


@pytest.fixture
def aegis(universe):
    return universe.get_planet("Aegis")


@pytest.fixture
def boreas(universe):
    return universe.get_planet("Boreas")


@pytest.fixture
def caelum(universe):
    return universe.get_planet("Caelum")


class TestVoidDistance:
    def test_aegis_boreas_positive(self, aegis, boreas):
        L = calc_void_distance(aegis, boreas)
        assert L > 0

    def test_never_negative(self, aegis, boreas):
        L = calc_void_distance(aegis, boreas)
        assert L >= 0

    def test_symmetrical(self, aegis, boreas):
        assert calc_void_distance(aegis, boreas) == calc_void_distance(boreas, aegis)

    def test_known_value(self, aegis, boreas):
        L = calc_void_distance(aegis, boreas)
        assert 17_000_000 < L < 19_000_000


class TestVoidTravelTime:
    def test_positive(self, aegis, boreas):
        L = calc_void_distance(aegis, boreas)
        Tv = calc_void_travel_time(aegis, boreas, L, 300000.0)
        assert Tv > 0

    def test_refraction_adds_time(self, aegis, boreas):
        L = calc_void_distance(aegis, boreas)
        Tv = calc_void_travel_time(aegis, boreas, L, 300000.0)
        Tv_no_atm = (L / 300000.0) * 1000.0
        assert Tv > Tv_no_atm


class TestFiberTransit:
    def test_same_tower_one_hit(self, aegis):
        Tp, s, m = calc_fiber_transit_time(aegis, 0, 0, 0.67, 300000.0, 7.0)
        assert s == 0
        assert m == 1
        assert Tp == 7.0

    def test_different_towers(self, aegis):
        Tp, s, m = calc_fiber_transit_time(aegis, 0, 2, 0.67, 300000.0, 7.0)
        assert s == 2
        assert m == 3
        assert Tp > 0

    def test_shortest_arc(self, aegis):
        _, s1, _ = calc_fiber_transit_time(aegis, 0, 1, 0.67, 300000.0, 7.0)
        _, s2, _ = calc_fiber_transit_time(aegis, 0, 7, 0.67, 300000.0, 7.0)
        assert s1 == s2 == 1


class TestHopLatency:
    def test_aegis_boreas(self, aegis, boreas):
        result = calc_hop_latency(aegis, boreas, 300000.0, 0.67, 7.0)
        assert result["latency"]["total_ms"] > 0
        assert result["void_distance_km"] > 0
        assert result["send_tower"] >= 0
        assert result["recv_tower"] >= 0

    def test_dead_planet_raises(self, aegis, boreas):
        boreas.alive = False
        with pytest.raises(RuntimeError):
            calc_hop_latency(aegis, boreas, 300000.0, 0.67, 7.0)
        boreas.alive = True

    def test_lmax_exceeded_raises(self, aegis, caelum):
        with pytest.raises(ValueError):
            calc_hop_latency(aegis, caelum, 300000.0, 0.67, 7.0, max_void_hop_km=100.0)

    def test_breakdown_keys(self, aegis, boreas):
        result = calc_hop_latency(aegis, boreas, 300000.0, 0.67, 7.0)
        assert "fiber_origin_ms" in result["latency"]
        assert "void_ms" in result["latency"]
        assert "fiber_destination_ms" in result["latency"]
        assert "total_ms" in result["latency"]