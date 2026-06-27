from dataclasses import dataclass, field
from typing import Any, Optional

#hop entry
@dataclass
class HopEntry:

    hop_index: int
    tx_planet: str
    rx_planet: str
    tx_tower: str
    rx_tower: str
    encoded_payload: str
    internal_fiber_delay_ms: float
    hop_latency_ms: float

    def to_dict(self) -> dict:
        return {
            "hop_index": self.hop_index,
            "tx_planet": self.tx_planet,
            "rx_planet": self.rx_planet,
            "tx_tower": self.tx_tower,
            "rx_tower": self.rx_tower,
            "encoded_payload": self.encoded_payload,
            "internal_fiber_delay_ms": self.internal_fiber_delay_ms,
            "hop_latency_ms": self.hop_latency_ms
        }


#packet
@dataclass
class Packet:
    origin_id: str
    destination_id: str
    current_id: str
    payload: Any
    hop_log: list[HopEntry] = field(default_factory=list)
    delivered: bool = False
    undeliverable: bool = False
    total_latency_ms: float = 0.0
    route_taken: list[str] = field(default_factory=list)

    def append_hop(self, hop: HopEntry) -> None:
        """Append a hop entry to the hop log."""
        self.hop_log.append(hop)
        self.total_latency_ms += hop.hop_latency_ms

    def mark_delivered(self) -> None:
        """Mark packet as successfully delivered."""
        self.delivered = True
        self.current_id = self.destination_id

    def mark_undeliverable(self) -> None:
        """Mark packet as undeliverable (no valid route)."""
        self.undeliverable = True

    def to_dict(self) -> dict:
        return {
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "current_id": self.current_id,
            "payload": self.payload,
            "delivered": self.delivered,
            "undeliverable": self.undeliverable,
            "total_latency_ms": round(self.total_latency_ms, 4),
            "route_taken": self.route_taken,
            "hop_log": [h.to_dict() for h in self.hop_log]
        }

    def __repr__(self) -> str:
        status = "delivered" if self.delivered else (
            "undeliverable" if self.undeliverable else "in-transit"
        )
        return (
            f"Packet({self.origin_id} -> {self.destination_id} "
            f"| status={status} | hops={len(self.hop_log)})"
        )