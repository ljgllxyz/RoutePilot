from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .models import NetworkAdapter, RouteRecord, RouteSnapshot, RouteStore


def make_button(text: str, style: str = "secondaryButton") -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(style)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


class StatCard(QFrame):
    def __init__(self, label: str, icon: str, icon_style: str, hint: str) -> None:
        super().__init__()
        self.setObjectName("statCard")
        self.setMinimumHeight(116)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        icon_label = QLabel(icon)
        icon_label.setObjectName(icon_style)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        title = QLabel(label)
        title.setObjectName("statLabel")
        self.value = QLabel("—")
        self.value.setObjectName("statValue")
        hint_label = QLabel(hint)
        hint_label.setObjectName("statHint")
        text_layout.addWidget(title)
        text_layout.addWidget(self.value)
        text_layout.addWidget(hint_label)
        text_layout.addStretch()
        layout.addLayout(text_layout, 1)

    def set_value(self, value: int | str) -> None:
        self.value.setText(str(value))


class RouteTableModel(QAbstractTableModel):
    COLUMNS = (
        ("目标网络", "destination_prefix"),
        ("下一跳", "next_hop"),
        ("网络适配器", "interface_alias"),
        ("接口", "interface_index"),
        ("路由跃点", "route_metric"),
        ("综合跃点", "total_metric"),
        ("协议", "protocol"),
        ("状态", "state"),
        ("协议族", "address_family"),
    )

    def __init__(self, routes: Sequence[RouteRecord] = ()) -> None:
        super().__init__()
        self.routes = list(routes)

    def set_routes(self, routes: Sequence[RouteRecord]) -> None:
        self.beginResetModel()
        self.routes = list(routes)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.routes)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section][0]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.routes):
            return None
        route = self.routes[index.row()]
        field = self.COLUMNS[index.column()][1]
        value = getattr(route, field)

        if role == Qt.ItemDataRole.DisplayRole:
            if field == "interface_alias":
                return value if value != "—" else f"接口 {route.interface_index}"
            return str(value)
        if role == Qt.ItemDataRole.UserRole:
            return value
        if role == Qt.ItemDataRole.ForegroundRole:
            if field == "state":
                return QColor("#159b68") if str(value).lower() == "alive" else QColor("#7d8798")
            if field == "destination_prefix":
                return QColor("#172033")
        if role == Qt.ItemDataRole.FontRole and field == "destination_prefix":
            font = QFont("Cascadia Mono")
            font.setPointSize(10)
            font.setWeight(QFont.Weight.DemiBold)
            return font
        if role == Qt.ItemDataRole.TextAlignmentRole and field in {
            "interface_index",
            "route_metric",
            "total_metric",
        }:
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            return (
                f"{route.destination_prefix} → {route.next_hop}\n"
                f"接口：{route.interface_alias} ({route.interface_index})\n"
                f"路由跃点：{route.route_metric}，接口跃点：{route.interface_metric}"
            )
        return None

    def route_at(self, row: int) -> RouteRecord | None:
        return self.routes[row] if 0 <= row < len(self.routes) else None


class RouteFilterProxy(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._query = ""
        self._family = "全部"
        self.setSortRole(Qt.ItemDataRole.UserRole)
        self.setDynamicSortFilter(True)

    def set_query(self, query: str) -> None:
        self._query = query.strip().casefold()
        self.invalidateFilter()

    def set_family(self, family: str) -> None:
        self._family = family
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if not isinstance(model, RouteTableModel):
            return True
        route = model.route_at(source_row)
        if route is None:
            return False
        if self._family != "全部" and route.address_family.casefold() != self._family.casefold():
            return False
        if not self._query:
            return True
        haystack = " ".join(
            (
                route.destination_prefix,
                route.next_hop,
                route.interface_alias,
                str(route.interface_index),
                route.protocol,
                route.state,
                route.address_family,
            )
        ).casefold()
        return self._query in haystack


class RoutePage(QWidget):
    add_requested = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    refresh_requested = pyqtSignal()

    def __init__(self, store: RouteStore) -> None:
        super().__init__()
        self.store = store
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel(store.display_name)
        title.setObjectName("pageTitle")
        subtitle_text = (
            "当前会话有效，系统重启后自动清除"
            if store is RouteStore.TEMPORARY
            else "保存到系统永久存储，重启后仍然生效"
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.refresh_button = make_button("↻  刷新")
        self.add_button = make_button("＋  新增路由", "primaryButton")
        self.refresh_button.clicked.connect(self.refresh_requested)
        self.add_button.clicked.connect(lambda: self.add_requested.emit(self.store))
        header.addWidget(self.refresh_button)
        header.addWidget(self.add_button)
        root.addLayout(header)

        card = QFrame()
        card.setObjectName("tableCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 14, 16, 14)
        toolbar_layout.setSpacing(9)
        self.search = QLineEdit()
        self.search.setObjectName("searchInput")
        self.search.setPlaceholderText("搜索目标、网关或网卡…")
        self.family_filter = QComboBox()
        self.family_filter.addItems(["全部", "IPv4", "IPv6"])
        self.edit_button = make_button("编辑")
        self.delete_button = make_button("删除", "dangerButton")
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        toolbar_layout.addWidget(self.search)
        toolbar_layout.addWidget(self.family_filter)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.edit_button)
        toolbar_layout.addWidget(self.delete_button)
        card_layout.addWidget(toolbar)

        self.model = RouteTableModel()
        self.proxy = RouteFilterProxy()
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(47)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(320)
        card_layout.addWidget(self.table, 1)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(17, 10, 17, 12)
        self.count_label = QLabel("共 0 条路由")
        self.count_label.setObjectName("mutedLabel")
        hint = QLabel("双击路由可快速编辑")
        hint.setObjectName("mutedLabel")
        footer_layout.addWidget(self.count_label)
        footer_layout.addStretch()
        footer_layout.addWidget(hint)
        card_layout.addWidget(footer)
        root.addWidget(card, 1)

        self.search.textChanged.connect(self.proxy.set_query)
        self.family_filter.currentTextChanged.connect(self.proxy.set_family)
        self.table.selectionModel().selectionChanged.connect(self._selection_changed)
        self.table.doubleClicked.connect(lambda _: self._emit_edit())
        self.edit_button.clicked.connect(self._emit_edit)
        self.delete_button.clicked.connect(self._emit_delete)

    def set_routes(self, routes: Sequence[RouteRecord]) -> None:
        self.model.set_routes(routes)
        # Keep the initial view deterministic: network prefixes in natural
        # ascending order, while the user can still click any header to sort.
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.count_label.setText(f"共 {len(routes)} 条路由")
        self.table.clearSelection()
        self._selection_changed()

    def selected_route(self) -> RouteRecord | None:
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return None
        source_index = self.proxy.mapToSource(selected[0])
        return self.model.route_at(source_index.row())

    def _selection_changed(self, *_args) -> None:
        enabled = self.selected_route() is not None
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def _emit_edit(self) -> None:
        route = self.selected_route()
        if route:
            self.edit_requested.emit(route)

    def _emit_delete(self) -> None:
        route = self.selected_route()
        if route:
            self.delete_requested.emit(route)

    def set_busy(self, busy: bool) -> None:
        for widget in (
            self.add_button,
            self.refresh_button,
            self.edit_button,
            self.delete_button,
        ):
            widget.setEnabled(not busy)
        if not busy:
            self._selection_changed()


class AdapterTableModel(QAbstractTableModel):
    COLUMNS = (
        "状态",
        "适配器名称",
        "接口",
        "IPv4 地址",
        "IPv6 地址",
        "MAC 地址",
        "链路速度",
        "跃点",
    )

    def __init__(self) -> None:
        super().__init__()
        self.adapters: list[NetworkAdapter] = []

    def set_adapters(self, adapters: Sequence[NetworkAdapter]) -> None:
        self.beginResetModel()
        self.adapters = list(adapters)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.adapters)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        adapter = self.adapters[index.row()]
        values = (
            "●  已连接" if adapter.is_up else "○  未连接",
            adapter.name,
            adapter.interface_index,
            "\n".join(adapter.ipv4_addresses) or "—",
            "\n".join(adapter.ipv6_addresses) or "—",
            adapter.mac_address,
            adapter.link_speed,
            adapter.interface_metric,
        )
        if role == Qt.ItemDataRole.DisplayRole:
            return str(values[index.column()])
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == 0:
            return QColor("#159b68") if adapter.is_up else QColor("#8993a4")
        if role == Qt.ItemDataRole.FontRole and index.column() == 1:
            font = QFont()
            font.setWeight(QFont.Weight.DemiBold)
            return font
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() in (2, 7):
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            return adapter.description
        return None


class AdapterPage(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("网络适配器")
        title.setObjectName("pageTitle")
        subtitle = QLabel("查看 Windows 当前识别的物理与虚拟网络接口")
        subtitle.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.refresh_button = make_button("↻  刷新适配器", "primaryButton")
        self.refresh_button.clicked.connect(self.refresh_requested)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        card = QFrame()
        card.setObjectName("tableCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.setContentsMargins(17, 14, 17, 14)
        self.summary = QLabel("正在读取网络适配器…")
        self.summary.setObjectName("sectionTitle")
        self.detail = QLabel("")
        self.detail.setObjectName("mutedLabel")
        top.addWidget(self.summary)
        top.addStretch()
        top.addWidget(self.detail)
        layout.addLayout(top)

        self.model = AdapterTableModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        root.addWidget(card, 1)

    def set_adapters(self, adapters: Sequence[NetworkAdapter]) -> None:
        self.model.set_adapters(adapters)
        up = sum(adapter.is_up for adapter in adapters)
        self.summary.setText(f"已发现 {len(adapters)} 个网络适配器")
        self.detail.setText(f"{up} 个已连接  ·  {len(adapters) - up} 个未连接")

    def set_busy(self, busy: bool) -> None:
        self.refresh_button.setEnabled(not busy)


class DashboardPage(QWidget):
    navigate_requested = pyqtSignal(int)
    add_requested = pyqtSignal(object)
    refresh_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("路由总览")
        title.setObjectName("pageTitle")
        subtitle = QLabel("集中查看和管理这台 Windows 设备的网络路径")
        subtitle.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.refresh_button = make_button("↻  刷新")
        self.add_button = make_button("＋  新增临时路由", "primaryButton")
        self.refresh_button.clicked.connect(self.refresh_requested)
        self.add_button.clicked.connect(lambda: self.add_requested.emit(RouteStore.TEMPORARY))
        header.addWidget(self.refresh_button)
        header.addWidget(self.add_button)
        root.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.adapter_card = StatCard("已连接适配器", "⌁", "statIconBlue", "可用网络接口")
        self.temporary_card = StatCard("临时路由", "↝", "statIconGreen", "重启后清除")
        self.persistent_card = StatCard("永久路由", "◆", "statIconPurple", "跨重启保留")
        self.default_card = StatCard("默认路由", "◎", "statIconOrange", "IPv4 / IPv6")
        for card in (
            self.adapter_card,
            self.temporary_card,
            self.persistent_card,
            self.default_card,
        ):
            stats.addWidget(card, 1)
        root.addLayout(stats)

        body = QHBoxLayout()
        body.setSpacing(14)
        routes_card = QFrame()
        routes_card.setObjectName("tableCard")
        routes_layout = QVBoxLayout(routes_card)
        routes_layout.setContentsMargins(0, 0, 0, 0)
        routes_header = QHBoxLayout()
        routes_header.setContentsMargins(17, 14, 14, 11)
        route_titles = QVBoxLayout()
        rt = QLabel("优先路由")
        rt.setObjectName("sectionTitle")
        rs = QLabel("按综合跃点排序的前 8 条路由")
        rs.setObjectName("sectionSubtitle")
        route_titles.addWidget(rt)
        route_titles.addWidget(rs)
        routes_header.addLayout(route_titles)
        routes_header.addStretch()
        open_routes = make_button("查看全部", "ghostButton")
        open_routes.clicked.connect(lambda: self.navigate_requested.emit(2))
        routes_header.addWidget(open_routes)
        routes_layout.addLayout(routes_header)
        self.route_model = RouteTableModel()
        self.route_table = QTableView()
        self.route_table.setModel(self.route_model)
        self.route_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.route_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.route_table.setAlternatingRowColors(True)
        self.route_table.verticalHeader().setVisible(False)
        self.route_table.verticalHeader().setDefaultSectionSize(43)
        self.route_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for column in (3, 5, 6, 7, 8):
            self.route_table.setColumnHidden(column, True)
        routes_layout.addWidget(self.route_table, 1)
        body.addWidget(routes_card, 3)

        adapters_card = QFrame()
        adapters_card.setObjectName("card")
        adapters_card.setMinimumWidth(270)
        adapters_layout = QVBoxLayout(adapters_card)
        adapters_layout.setContentsMargins(18, 16, 18, 16)
        adapter_header = QHBoxLayout()
        at = QLabel("活动适配器")
        at.setObjectName("sectionTitle")
        adapter_header.addWidget(at)
        adapter_header.addStretch()
        open_adapters = make_button("详情", "ghostButton")
        open_adapters.clicked.connect(lambda: self.navigate_requested.emit(1))
        adapter_header.addWidget(open_adapters)
        adapters_layout.addLayout(adapter_header)
        self.adapters_container = QVBoxLayout()
        self.adapters_container.setSpacing(7)
        adapters_layout.addLayout(self.adapters_container)
        adapters_layout.addStretch()
        body.addWidget(adapters_card, 1)
        root.addLayout(body, 1)

    def update_snapshot(self, snapshot: RouteSnapshot) -> None:
        up = [adapter for adapter in snapshot.adapters if adapter.is_up]
        self.adapter_card.set_value(len(up))
        self.temporary_card.set_value(len(snapshot.temporary_routes))
        self.persistent_card.set_value(len(snapshot.persistent_routes))
        self.default_card.set_value(snapshot.default_route_count)
        routes = sorted(
            snapshot.temporary_routes + snapshot.persistent_routes,
            key=lambda route: route.total_metric,
        )[:8]
        self.route_model.set_routes(routes)

        while self.adapters_container.count():
            item = self.adapters_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        shown = up[:6]
        if not shown:
            empty = QLabel("暂无已连接的网络适配器")
            empty.setObjectName("mutedLabel")
            self.adapters_container.addWidget(empty)
        for adapter in shown:
            row = QFrame()
            row.setStyleSheet("QFrame { background:#f8fafc; border-radius:8px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 9, 10, 9)
            dot = QLabel("●")
            dot.setStyleSheet("color:#20b77a; font-size:10px; border:none; background:transparent;")
            names = QVBoxLayout()
            name = QLabel(adapter.name)
            name.setStyleSheet("font-weight:600; border:none; background:transparent;")
            ip = QLabel(adapter.ipv4_addresses[0] if adapter.ipv4_addresses else f"接口 {adapter.interface_index}")
            ip.setObjectName("mutedLabel")
            names.addWidget(name)
            names.addWidget(ip)
            row_layout.addWidget(dot)
            row_layout.addLayout(names, 1)
            self.adapters_container.addWidget(row)

    def set_busy(self, busy: bool) -> None:
        self.refresh_button.setEnabled(not busy)
        self.add_button.setEnabled(not busy)
