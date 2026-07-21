from __future__ import annotations

import ipaddress

from .models import RouteDraft


class RouteValidationError(ValueError):
    """Raised when route input cannot be safely passed to Windows."""


def normalize_route_draft(draft: RouteDraft) -> RouteDraft:
    try:
        network = ipaddress.ip_network(draft.destination_prefix.strip(), strict=False)
    except ValueError as exc:
        raise RouteValidationError(
            "目标网络格式不正确，请使用 CIDR 格式，例如 192.168.10.0/24。"
        ) from exc

    try:
        gateway = ipaddress.ip_address(draft.next_hop.strip())
    except ValueError as exc:
        raise RouteValidationError("下一跳不是有效的 IPv4 或 IPv6 地址。") from exc

    if network.version != gateway.version:
        raise RouteValidationError("目标网络与下一跳必须使用相同的 IP 协议版本。")
    if draft.interface_index <= 0:
        raise RouteValidationError("请选择一个有效的网络适配器。")
    if not 0 <= draft.route_metric <= 65535:
        raise RouteValidationError("路由跃点数必须在 0 到 65535 之间。")

    return RouteDraft(
        destination_prefix=network.with_prefixlen,
        next_hop=gateway.compressed,
        interface_index=int(draft.interface_index),
        route_metric=int(draft.route_metric),
        store=draft.store,
    )

