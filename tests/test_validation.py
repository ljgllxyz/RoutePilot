from __future__ import annotations

import pytest

from route_manager.models import RouteDraft, RouteStore
from route_manager.validation import RouteValidationError, normalize_route_draft


def draft(destination: str, gateway: str, metric: int = 20) -> RouteDraft:
    return RouteDraft(destination, gateway, 7, metric, RouteStore.TEMPORARY)


def test_normalizes_network_and_gateway() -> None:
    result = normalize_route_draft(draft("192.168.50.19/24", "192.168.1.1"))
    assert result.destination_prefix == "192.168.50.0/24"
    assert result.next_hop == "192.168.1.1"


def test_supports_ipv6() -> None:
    result = normalize_route_draft(draft("2001:0db8::12/48", "fe80::1"))
    assert result.destination_prefix == "2001:db8::/48"
    assert result.next_hop == "fe80::1"


def test_rejects_mixed_address_families() -> None:
    with pytest.raises(RouteValidationError, match="相同"):
        normalize_route_draft(draft("10.0.0.0/8", "fe80::1"))


@pytest.mark.parametrize("metric", [-1, 65536])
def test_rejects_metric_out_of_uint16_range(metric: int) -> None:
    with pytest.raises(RouteValidationError, match="65535"):
        normalize_route_draft(draft("10.0.0.0/8", "10.1.1.1", metric))


def test_rejects_missing_prefix() -> None:
    with pytest.raises(RouteValidationError, match="CIDR"):
        normalize_route_draft(draft("not-a-network", "10.1.1.1"))

