from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RouteStore(str, Enum):
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"

    @property
    def display_name(self) -> str:
        return "临时路由" if self is RouteStore.TEMPORARY else "永久路由"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _string(value: Any, default: str = "—") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class NetworkAdapter:
    interface_index: int
    name: str
    description: str
    status: str
    mac_address: str
    link_speed: str
    ipv4_addresses: tuple[str, ...] = field(default_factory=tuple)
    ipv6_addresses: tuple[str, ...] = field(default_factory=tuple)
    interface_metric: int = 0
    dhcp: str = "—"
    media_type: str = "—"

    @property
    def is_up(self) -> bool:
        return self.status.lower() == "up"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "NetworkAdapter":
        return cls(
            interface_index=_integer(data.get("InterfaceIndex")),
            name=_string(data.get("Name")),
            description=_string(data.get("Description")),
            status=_string(data.get("Status")),
            mac_address=_string(data.get("MacAddress")),
            link_speed=_string(data.get("LinkSpeed")),
            ipv4_addresses=tuple(str(item) for item in _as_list(data.get("IPv4"))),
            ipv6_addresses=tuple(str(item) for item in _as_list(data.get("IPv6"))),
            interface_metric=_integer(data.get("InterfaceMetric")),
            dhcp=_string(data.get("Dhcp")),
            media_type=_string(data.get("MediaType")),
        )


@dataclass(frozen=True, slots=True)
class RouteRecord:
    destination_prefix: str
    next_hop: str
    interface_index: int
    interface_alias: str
    address_family: str
    route_metric: int
    interface_metric: int
    protocol: str
    state: str
    publish: str
    valid_lifetime: str
    store: RouteStore

    @property
    def identity(self) -> tuple[str, int, str]:
        return (
            self.destination_prefix.casefold(),
            self.interface_index,
            self.next_hop.casefold(),
        )

    @property
    def total_metric(self) -> int:
        return self.route_metric + self.interface_metric

    @classmethod
    def from_mapping(
        cls, data: dict[str, Any], store: RouteStore
    ) -> "RouteRecord":
        return cls(
            destination_prefix=_string(data.get("DestinationPrefix")),
            next_hop=_string(data.get("NextHop")),
            interface_index=_integer(data.get("InterfaceIndex")),
            interface_alias=_string(data.get("InterfaceAlias")),
            address_family=_string(data.get("AddressFamily")),
            route_metric=_integer(data.get("RouteMetric")),
            interface_metric=_integer(data.get("InterfaceMetric")),
            protocol=_string(data.get("Protocol")),
            state=_string(data.get("State")),
            publish=_string(data.get("Publish")),
            valid_lifetime=_string(data.get("ValidLifetime")),
            store=store,
        )


@dataclass(frozen=True, slots=True)
class RouteDraft:
    destination_prefix: str
    next_hop: str
    interface_index: int
    route_metric: int
    store: RouteStore


@dataclass(frozen=True, slots=True)
class RouteSnapshot:
    adapters: tuple[NetworkAdapter, ...] = field(default_factory=tuple)
    temporary_routes: tuple[RouteRecord, ...] = field(default_factory=tuple)
    persistent_routes: tuple[RouteRecord, ...] = field(default_factory=tuple)

    @property
    def default_route_count(self) -> int:
        prefixes = {"0.0.0.0/0", "::/0"}
        all_routes = self.temporary_routes + self.persistent_routes
        return sum(route.destination_prefix in prefixes for route in all_routes)

