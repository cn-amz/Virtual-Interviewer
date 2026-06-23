from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublicEndpoint:
    url: str
    provider: str
    notes: list[str]


class PublicEndpointProvider(Protocol):
    def expose(self, local_port: int, protocol: str, purpose: str) -> PublicEndpoint:
        ...


class LocalOnlyProvider:
    def expose(self, local_port: int, protocol: str, purpose: str) -> PublicEndpoint:
        scheme = "http" if protocol in {"http", "ws"} else protocol
        return PublicEndpoint(
            url=f"{scheme}://localhost:{local_port}",
            provider="local",
            notes=[f"Local-only endpoint for {purpose}. Use a tunnel or cloud provider for judges."],
        )


class ReservedProvider:
    def __init__(self, name: str):
        self.name = name

    def expose(self, local_port: int, protocol: str, purpose: str) -> PublicEndpoint:
        return PublicEndpoint(
            url="",
            provider=self.name,
            notes=[
                f"{self.name} provider is reserved for {purpose}.",
                f"Forward local port {local_port} with protocol {protocol} during deployment.",
            ],
        )
