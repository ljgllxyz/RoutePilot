from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .models import NetworkAdapter, RouteDraft, RouteRecord, RouteStore
from .validation import RouteValidationError, normalize_route_draft
from .widgets import make_button


class RouteDialog(QDialog):
    def __init__(
        self,
        store: RouteStore,
        adapters: tuple[NetworkAdapter, ...],
        route: RouteRecord | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.route = route
        self._draft: RouteDraft | None = None
        self.setWindowTitle(("编辑" if route else "新增") + store.display_name)
        self.setModal(True)
        self.setMinimumWidth(580)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("dialogHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(25, 20, 25, 18)
        header_layout.setSpacing(3)
        title = QLabel(("编辑" if route else "新增") + store.display_name)
        title.setObjectName("dialogTitle")
        subtitle = QLabel("配置目标网络、下一跳和出口适配器")
        subtitle.setObjectName("dialogSubtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        form_widget = QWidget()
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(25, 20, 25, 18)
        form.setSpacing(15)

        notice = QFrame()
        notice.setObjectName("storeNotice")
        notice_layout = QVBoxLayout(notice)
        notice_layout.setContentsMargins(13, 10, 13, 10)
        notice_layout.setSpacing(2)
        notice_title = QLabel("临时存储 · ActiveStore" if store is RouteStore.TEMPORARY else "永久存储 · ActiveStore + PersistentStore")
        notice_title.setObjectName("storeNoticeTitle")
        notice_text = QLabel(
            "只在当前 Windows 会话有效，重启后自动失效。"
            if store is RouteStore.TEMPORARY
            else "立即生效并写入永久存储，Windows 重启后会自动恢复。"
        )
        notice_text.setObjectName("storeNoticeText")
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_text)
        form.addWidget(notice)

        self.destination = QLineEdit()
        self.destination.setPlaceholderText("例如：192.168.50.0/24 或 2001:db8::/32")
        form.addLayout(self._field("目标网络 / CIDR", self.destination, "输入主机地址时会自动规范为对应网段"))

        self.gateway = QLineEdit()
        self.gateway.setPlaceholderText("例如：192.168.1.1；直连路由可填写 0.0.0.0")
        form.addLayout(self._field("下一跳网关", self.gateway, "IPv6 直连路由填写 ::"))

        self.adapter = QComboBox()
        for item in adapters:
            state = "●" if item.is_up else "○"
            ip = item.ipv4_addresses[0] if item.ipv4_addresses else "无 IPv4 地址"
            self.adapter.addItem(
                f"{state}  {item.name}  ·  接口 {item.interface_index}  ·  {ip}",
                item.interface_index,
            )
        if route and self.adapter.findData(route.interface_index) < 0:
            self.adapter.addItem(
                f"○  原接口已不可用  ·  接口 {route.interface_index}",
                route.interface_index,
            )
        form.addLayout(self._field("出口网络适配器", self.adapter, "已连接的适配器会优先排列"))

        self.metric = QSpinBox()
        self.metric.setRange(0, 65535)
        self.metric.setValue(256)
        self.metric.setAccelerated(True)
        form.addLayout(self._field("路由跃点数", self.metric, "数值越小，路由优先级通常越高；还会叠加接口跃点"))

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        form.addWidget(self.error_label)
        root.addWidget(form_widget)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(25, 12, 25, 20)
        footer_layout.addStretch()
        cancel = make_button("取消")
        self.save = make_button("保存路由", "primaryButton")
        cancel.clicked.connect(self.reject)
        self.save.clicked.connect(self.accept)
        footer_layout.addWidget(cancel)
        footer_layout.addWidget(self.save)
        root.addWidget(footer)

        if route:
            self.destination.setText(route.destination_prefix)
            self.gateway.setText(route.next_hop)
            self.metric.setValue(route.route_metric)
            index = self.adapter.findData(route.interface_index)
            if index >= 0:
                self.adapter.setCurrentIndex(index)
        elif self.adapter.count() == 0:
            self.error_label.setText("没有可用的网络适配器，暂时无法新增路由。")
            self.error_label.show()
            self.save.setEnabled(False)

    @staticmethod
    def _field(label_text: str, field: QWidget, hint_text: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        hint = QLabel(hint_text)
        hint.setObjectName("fieldHint")
        layout.addWidget(label)
        layout.addWidget(field)
        layout.addWidget(hint)
        return layout

    @property
    def draft(self) -> RouteDraft:
        if self._draft is None:
            raise RuntimeError("RouteDialog 尚未产生有效数据。")
        return self._draft

    def accept(self) -> None:
        try:
            adapter_index = self.adapter.currentData()
            if adapter_index is None:
                raise RouteValidationError("请选择一个出口网络适配器。")
            self._draft = normalize_route_draft(
                RouteDraft(
                    destination_prefix=self.destination.text(),
                    next_hop=self.gateway.text(),
                    interface_index=int(adapter_index),
                    route_metric=self.metric.value(),
                    store=self.store,
                )
            )
        except (RouteValidationError, ValueError) as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        super().accept()

