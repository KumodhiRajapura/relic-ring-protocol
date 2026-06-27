from dataclasses import dataclass, field
from typing import Any


@dataclass
class Packet:
    origin_id: str
    destination_id: str
    current_id: str
    payload: Any
    hop_log: list[dict] = field(default_factory=list)
    delivered: bool = False
    undeliverable: bool = False
    total_latency_ms: float = 0.0
    route_taken: list[str] = field(default_factory=list)

    def mark_delivered(self) -> None:
        self.delivered = True
        self.current_id = self.destination_id

    def mark_undeliverable(self) -> None:
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
            "hop_log": self.hop_log,
        }

    def __repr__(self) -> str:
        status = "delivered" if self.delivered else (
            "undeliverable" if self.undeliverable else "in-transit"
        )
        return (
            f"Packet({self.origin_id} -> {self.destination_id} "
            f"| status={status} | hops={len(self.hop_log)})"
        )
