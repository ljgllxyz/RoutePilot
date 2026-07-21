from __future__ import annotations

from typing import Any

from route_manager.models import RouteDraft, RouteRecord, RouteStore
from route_manager.service import RouteService


class FakeRunner:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or {}
        self.commands: list[str] = []

    def execute_json(self, script: str) -> Any:
        self.commands.append(script)
        return self.payload

    def execute(self, script: str) -> str:
        self.commands.append(script)
        return ""


def route_mapping(prefix: str, gateway: str, index: int, metric: int = 10) -> dict[str, Any]:
    return {
        "DestinationPrefix": prefix,
        "NextHop": gateway,
        "InterfaceIndex": index,
        "InterfaceAlias": f"Ethernet {index}",
        "AddressFamily": "IPv4",
        "RouteMetric": metric,
        "InterfaceMetric": 5,
        "Protocol": "NetMgmt",
        "State": "Alive",
        "Publish": "No",
        "ValidLifetime": "Infinite",
    }


def test_snapshot_separates_active_only_routes_from_persistent_routes() -> None:
    saved = route_mapping("10.0.0.0/8", "192.168.1.1", 7)
    active_only = route_mapping("172.16.0.0/12", "192.168.1.2", 8)
    runner = FakeRunner(
        {
            "Adapters": [],
            "ActiveRoutes": [saved, active_only],
            "PersistentRoutes": [saved],
        }
    )
    snapshot = RouteService(runner).load_snapshot()  # type: ignore[arg-type]
    assert [item.destination_prefix for item in snapshot.temporary_routes] == ["172.16.0.0/12"]
    assert [item.destination_prefix for item in snapshot.persistent_routes] == ["10.0.0.0/8"]


def test_create_temporary_route_targets_active_store_only() -> None:
    runner = FakeRunner()
    service = RouteService(runner)  # type: ignore[arg-type]
    service.create_route(RouteDraft("10.20.1.9/24", "192.168.1.1", 7, 15, RouteStore.TEMPORARY))
    command = runner.commands[-1]
    assert "-DestinationPrefix '10.20.1.0/24'" in command
    assert "-PolicyStore ActiveStore" in command


def test_create_persistent_route_omits_policy_store_to_write_both_stores() -> None:
    runner = FakeRunner()
    service = RouteService(runner)  # type: ignore[arg-type]
    service.create_route(RouteDraft("10.30.0.0/16", "192.168.1.1", 7, 15, RouteStore.PERSISTENT))
    command = runner.commands[-1]
    assert "New-NetRoute" in command
    assert "PolicyStore" not in command


def test_delete_temporary_route_has_persistent_store_safety_check() -> None:
    runner = FakeRunner()
    service = RouteService(runner)  # type: ignore[arg-type]
    service.delete_route(RouteDraft("10.40.0.0/16", "192.168.1.1", 7, 15, RouteStore.TEMPORARY))
    command = runner.commands[-1]
    assert "-PolicyStore PersistentStore" in command
    assert "-PolicyStore ActiveStore" in command
    assert "防止误删" in command


def test_metric_only_update_uses_set_netroute() -> None:
    runner = FakeRunner()
    service = RouteService(runner)  # type: ignore[arg-type]
    old = RouteDraft("10.50.0.0/16", "192.168.1.1", 7, 15, RouteStore.PERSISTENT)
    new = RouteDraft("10.50.0.0/16", "192.168.1.1", 7, 25, RouteStore.PERSISTENT)
    service.update_route(old, new)
    assert len(runner.commands) == 1
    assert "Set-NetRoute -RouteMetric 25" in runner.commands[0]

