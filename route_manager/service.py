from __future__ import annotations

import ipaddress
from collections.abc import Iterable

from .models import (
    NetworkAdapter,
    RouteDraft,
    RouteRecord,
    RouteSnapshot,
    RouteStore,
)
from .powershell import PowerShellError, PowerShellRunner, ps_quote
from .validation import normalize_route_draft


SNAPSHOT_SCRIPT = r"""
function Convert-RouteRecord($route) {
    [pscustomobject]@{
        DestinationPrefix = [string]$route.DestinationPrefix
        NextHop = [string]$route.NextHop
        InterfaceIndex = [int]$route.InterfaceIndex
        InterfaceAlias = [string]$route.InterfaceAlias
        AddressFamily = [string]$route.AddressFamily
        RouteMetric = [int]$route.RouteMetric
        InterfaceMetric = [int]$route.InterfaceMetric
        Protocol = [string]$route.Protocol
        State = [string]$route.State
        Publish = [string]$route.Publish
        ValidLifetime = [string]$route.ValidLifetime
    }
}

$adapters = @(
    Get-NetAdapter -IncludeHidden -ErrorAction Stop |
    Sort-Object -Property ifIndex |
    ForEach-Object {
        $adapter = $_
        $ipInterface = Get-NetIPInterface -InterfaceIndex $adapter.ifIndex -ErrorAction SilentlyContinue |
            Sort-Object @{ Expression = { if ($_.AddressFamily -eq 'IPv4') { 0 } else { 1 } } } |
            Select-Object -First 1
        $ipv4 = @(Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Sort-Object IPAddress |
            ForEach-Object { [string]$_.IPAddress + '/' + [string]$_.PrefixLength })
        $ipv6 = @(Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv6 -ErrorAction SilentlyContinue |
            Where-Object { $_.AddressState -ne 'Duplicate' } |
            Sort-Object IPAddress |
            ForEach-Object { [string]$_.IPAddress + '/' + [string]$_.PrefixLength })
        [pscustomobject]@{
            InterfaceIndex = [int]$adapter.ifIndex
            Name = [string]$adapter.Name
            Description = [string]$adapter.InterfaceDescription
            Status = [string]$adapter.Status
            MacAddress = [string]$adapter.MacAddress
            LinkSpeed = [string]$adapter.LinkSpeed
            IPv4 = $ipv4
            IPv6 = $ipv6
            InterfaceMetric = if ($null -ne $ipInterface) { [int]$ipInterface.InterfaceMetric } else { 0 }
            Dhcp = if ($null -ne $ipInterface) { [string]$ipInterface.Dhcp } else { '' }
            MediaType = [string]$adapter.MediaType
        }
    }
)
$activeRoutes = @(Get-NetRoute -PolicyStore ActiveStore -ErrorAction Stop |
    ForEach-Object { Convert-RouteRecord $_ })
$persistentRoutes = @(Get-NetRoute -PolicyStore PersistentStore -ErrorAction Stop |
    ForEach-Object { Convert-RouteRecord $_ })

[pscustomobject]@{
    Adapters = $adapters
    ActiveRoutes = $activeRoutes
    PersistentRoutes = $persistentRoutes
} | ConvertTo-Json -Depth 6 -Compress
"""


def _list(value: object) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _route_sort_key(route: RouteRecord) -> tuple[int, int, int, int, str]:
    try:
        network = ipaddress.ip_network(route.destination_prefix, strict=False)
        return (
            network.version,
            int(network.network_address),
            network.prefixlen,
            route.total_metric,
            route.interface_alias.casefold(),
        )
    except ValueError:
        return (9, 0, 0, route.total_metric, route.destination_prefix.casefold())


class RouteService:
    def __init__(self, runner: PowerShellRunner | None = None) -> None:
        self.runner = runner or PowerShellRunner()

    def load_snapshot(self) -> RouteSnapshot:
        payload = self.runner.execute_json(SNAPSHOT_SCRIPT)
        if not isinstance(payload, dict):
            raise PowerShellError("没有从 Windows 获取到网络配置数据。")

        adapters = tuple(
            sorted(
                (NetworkAdapter.from_mapping(item) for item in _list(payload.get("Adapters"))),
                key=lambda adapter: (not adapter.is_up, adapter.interface_index),
            )
        )
        aliases = {adapter.interface_index: adapter.name for adapter in adapters}

        persistent = [
            RouteRecord.from_mapping(item, RouteStore.PERSISTENT)
            for item in _list(payload.get("PersistentRoutes"))
        ]
        persistent_ids = {route.identity for route in persistent}

        temporary: list[RouteRecord] = []
        for item in _list(payload.get("ActiveRoutes")):
            route = RouteRecord.from_mapping(item, RouteStore.TEMPORARY)
            if route.identity not in persistent_ids:
                temporary.append(route)

        temporary = [self._with_alias(route, aliases) for route in temporary]
        persistent = [self._with_alias(route, aliases) for route in persistent]
        temporary.sort(key=_route_sort_key)
        persistent.sort(key=_route_sort_key)
        return RouteSnapshot(adapters, tuple(temporary), tuple(persistent))

    @staticmethod
    def _with_alias(route: RouteRecord, aliases: dict[int, str]) -> RouteRecord:
        if route.interface_alias != "—" or route.interface_index not in aliases:
            return route
        return RouteRecord(
            destination_prefix=route.destination_prefix,
            next_hop=route.next_hop,
            interface_index=route.interface_index,
            interface_alias=aliases[route.interface_index],
            address_family=route.address_family,
            route_metric=route.route_metric,
            interface_metric=route.interface_metric,
            protocol=route.protocol,
            state=route.state,
            publish=route.publish,
            valid_lifetime=route.valid_lifetime,
            store=route.store,
        )

    def create_route(self, draft: RouteDraft) -> RouteDraft:
        route = normalize_route_draft(draft)
        command = (
            "New-NetRoute "
            f"-DestinationPrefix {ps_quote(route.destination_prefix)} "
            f"-InterfaceIndex {route.interface_index} "
            f"-NextHop {ps_quote(route.next_hop)} "
            f"-RouteMetric {route.route_metric} "
        )
        # Microsoft documents that omitting PolicyStore creates the route in both
        # stores. PersistentStore cannot be supplied directly to New-NetRoute.
        if route.store is RouteStore.TEMPORARY:
            command += "-PolicyStore ActiveStore "
        command += "-Confirm:$false -ErrorAction Stop | Out-Null"
        self.runner.execute(command)
        return route

    def delete_route(self, route: RouteRecord | RouteDraft) -> None:
        draft = self._draft(route)
        selector = self._selector(draft)
        if draft.store is RouteStore.TEMPORARY:
            script = (
                f"$saved = @({selector} -PolicyStore PersistentStore -ErrorAction SilentlyContinue);"
                "if ($saved.Count -gt 0) { throw '该路由已存在于永久存储区，为防止误删请在永久路由页面操作。' };"
                f"$routes = @({selector} -PolicyStore ActiveStore -ErrorAction SilentlyContinue);"
                "if ($routes.Count -eq 0) { throw '要删除的临时路由已不存在。' };"
                "$routes | Remove-NetRoute -Confirm:$false -ErrorAction Stop"
            )
        else:
            script = (
                f"$saved = @({selector} -PolicyStore PersistentStore -ErrorAction SilentlyContinue);"
                "if ($saved.Count -eq 0) { throw '要删除的永久路由已不存在。' };"
                "$saved | Remove-NetRoute -Confirm:$false -ErrorAction Stop;"
                f"$active = @({selector} -PolicyStore ActiveStore -ErrorAction SilentlyContinue);"
                "if ($active.Count -gt 0) { $active | Remove-NetRoute -Confirm:$false -ErrorAction Stop }"
            )
        self.runner.execute(script)

    def update_route(
        self, original: RouteRecord | RouteDraft, replacement: RouteDraft
    ) -> RouteDraft:
        old = self._draft(original)
        new = normalize_route_draft(replacement)
        if old.store is not new.store:
            raise ValueError("编辑路由时不能更改存储类型。")

        if self._same_identity(old, new):
            if old.route_metric == new.route_metric:
                return new
            self._update_metric(old, new.route_metric)
            return new

        self.create_route(new)
        try:
            self.delete_route(old)
        except Exception as exc:
            try:
                self.delete_route(new)
            except Exception as rollback_exc:
                raise PowerShellError(
                    f"替换旧路由失败，而且新路由回滚失败：{rollback_exc}"
                ) from exc
            raise
        return new

    def _update_metric(self, route: RouteDraft, metric: int) -> None:
        selector = self._selector(route)
        if route.store is RouteStore.TEMPORARY:
            script = (
                f"$saved = @({selector} -PolicyStore PersistentStore -ErrorAction SilentlyContinue);"
                "if ($saved.Count -gt 0) { throw '该路由已属于永久路由，不能从临时路由页面修改。' };"
                f"$active = @({selector} -PolicyStore ActiveStore -ErrorAction SilentlyContinue);"
                "if ($active.Count -eq 0) { throw '要修改的临时路由已不存在。' };"
                f"$active | Set-NetRoute -RouteMetric {metric} -Confirm:$false -ErrorAction Stop"
            )
        else:
            script = (
                f"$saved = @({selector} -PolicyStore PersistentStore -ErrorAction SilentlyContinue);"
                "if ($saved.Count -eq 0) { throw '要修改的永久路由已不存在。' };"
                f"$saved | Set-NetRoute -RouteMetric {metric} -Confirm:$false -ErrorAction Stop;"
                f"$active = @({selector} -PolicyStore ActiveStore -ErrorAction SilentlyContinue);"
                f"if ($active.Count -gt 0) {{ $active | Set-NetRoute -RouteMetric {metric} -Confirm:$false -ErrorAction Stop }}"
            )
        self.runner.execute(script)

    @staticmethod
    def _same_identity(left: RouteDraft, right: RouteDraft) -> bool:
        return (
            left.destination_prefix.casefold(),
            left.interface_index,
            left.next_hop.casefold(),
        ) == (
            right.destination_prefix.casefold(),
            right.interface_index,
            right.next_hop.casefold(),
        )

    @staticmethod
    def _draft(route: RouteRecord | RouteDraft) -> RouteDraft:
        if isinstance(route, RouteDraft):
            return normalize_route_draft(route)
        return normalize_route_draft(
            RouteDraft(
                destination_prefix=route.destination_prefix,
                next_hop=route.next_hop,
                interface_index=route.interface_index,
                route_metric=route.route_metric,
                store=route.store,
            )
        )

    @staticmethod
    def _selector(route: RouteDraft) -> str:
        return (
            "Get-NetRoute "
            f"-DestinationPrefix {ps_quote(route.destination_prefix)} "
            f"-InterfaceIndex {route.interface_index} "
            f"-NextHop {ps_quote(route.next_hop)}"
        )


def adapter_choices(adapters: Iterable[NetworkAdapter]) -> list[NetworkAdapter]:
    return sorted(adapters, key=lambda adapter: (not adapter.is_up, adapter.interface_index))

