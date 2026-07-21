from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .admin import is_admin
from .dialogs import RouteDialog
from .models import RouteRecord, RouteSnapshot, RouteStore
from .service import RouteService
from .widgets import AdapterPage, DashboardPage, RoutePage


class TaskThread(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task: Callable[[], Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task = task

    def run(self) -> None:
        try:
            self.succeeded.emit(self.task())
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)


class MainWindow(QMainWindow):
    def __init__(self, service: RouteService | None = None) -> None:
        super().__init__()
        self.service = service or RouteService()
        self.snapshot = RouteSnapshot()
        self._worker: TaskThread | None = None
        self._is_admin = is_admin()

        self.setWindowTitle("RoutePilot · Windows 路由管理器")
        self.setMinimumSize(1120, 700)
        self.resize(1440, 900)
        self._build_ui()

        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)
        self.escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.escape_shortcut.activated.connect(self._leave_fullscreen)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(17, 24, 17, 20)
        side.setSpacing(8)

        brand = QHBoxLayout()
        brand.setSpacing(11)
        mark = QLabel("⇄")
        mark.setObjectName("brandMark")
        mark.setFixedSize(47, 47)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("RoutePilot")
        name.setObjectName("brandTitle")
        subtitle = QLabel("WINDOWS ROUTE MANAGER")
        subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(name)
        brand_text.addWidget(subtitle)
        brand.addWidget(mark)
        brand.addLayout(brand_text)
        side.addLayout(brand)
        side.addSpacing(27)

        section = QLabel("工作台")
        section.setObjectName("navSection")
        side.addWidget(section)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        nav_items = (
            ("▦   路由总览", 0),
            ("⌁   网络适配器", 1),
            ("↝   临时路由", 2),
            ("◆   永久路由", 3),
        )
        self.nav_buttons: list[QPushButton] = []
        for text, index in nav_items:
            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked, page=index: self.set_page(page))
            self.button_group.addButton(button, index)
            self.nav_buttons.append(button)
            side.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        side.addStretch()

        shortcut_hint = QLabel("F11  全屏 / 退出全屏")
        shortcut_hint.setObjectName("adminSubtitle")
        shortcut_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(shortcut_hint)
        side.addSpacing(8)

        admin_card = QFrame()
        admin_card.setObjectName("adminCard")
        admin_layout = QHBoxLayout(admin_card)
        admin_layout.setContentsMargins(13, 11, 13, 11)
        admin_layout.setSpacing(10)
        dot = QLabel()
        dot.setObjectName("adminDot")
        if not self._is_admin:
            dot.setStyleSheet("background:#e39a35;")
        admin_text = QVBoxLayout()
        admin_text.setSpacing(1)
        admin_title = QLabel("管理员模式" if self._is_admin else "只读模式")
        admin_title.setObjectName("adminTitle")
        admin_subtitle = QLabel("路由写入权限已就绪" if self._is_admin else "未获得管理员权限")
        admin_subtitle.setObjectName("adminSubtitle")
        admin_text.addWidget(admin_title)
        admin_text.addWidget(admin_subtitle)
        admin_layout.addWidget(dot)
        admin_layout.addLayout(admin_text, 1)
        side.addWidget(admin_card)
        root_layout.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.busy_bar = QProgressBar()
        self.busy_bar.setObjectName("busyBar")
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setTextVisible(False)
        self.busy_bar.hide()
        content_layout.addWidget(self.busy_bar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")
        self.dashboard = DashboardPage()
        self.adapters_page = AdapterPage()
        self.temporary_page = RoutePage(RouteStore.TEMPORARY)
        self.persistent_page = RoutePage(RouteStore.PERSISTENT)
        for page in (
            self.dashboard,
            self.adapters_page,
            self.temporary_page,
            self.persistent_page,
        ):
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)

        footer = QFrame()
        footer.setStyleSheet("QFrame { background:#ffffff; border-top:1px solid #e5eaf2; }")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 7, 22, 7)
        self.status_label = QLabel("准备读取 Windows 网络配置…")
        self.status_label.setObjectName("footerStatus")
        self.updated_label = QLabel("")
        self.updated_label.setObjectName("footerStatus")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.updated_label)
        content_layout.addWidget(footer)
        root_layout.addWidget(content, 1)

        self.dashboard.navigate_requested.connect(self.set_page)
        self.dashboard.refresh_requested.connect(self.refresh_snapshot)
        self.dashboard.add_requested.connect(self.open_add_dialog)
        self.adapters_page.refresh_requested.connect(self.refresh_snapshot)
        for page in (self.temporary_page, self.persistent_page):
            page.refresh_requested.connect(self.refresh_snapshot)
            page.add_requested.connect(self.open_add_dialog)
            page.edit_requested.connect(self.open_edit_dialog)
            page.delete_requested.connect(self.confirm_delete)

    def set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)

    def refresh_snapshot(self) -> None:
        self._run_task("正在读取 Windows 网络配置…", self.service.load_snapshot, self._apply_snapshot)

    def _apply_snapshot(self, snapshot: RouteSnapshot) -> None:
        self.snapshot = snapshot
        self.dashboard.update_snapshot(snapshot)
        self.adapters_page.set_adapters(snapshot.adapters)
        self.temporary_page.set_routes(snapshot.temporary_routes)
        self.persistent_page.set_routes(snapshot.persistent_routes)
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(
            f"已读取 {len(snapshot.adapters)} 个适配器和 "
            f"{len(snapshot.temporary_routes) + len(snapshot.persistent_routes)} 条路由"
        )
        self.updated_label.setText(f"最后刷新  {now}")

    def open_add_dialog(self, store: RouteStore) -> None:
        if not self._ensure_write_access():
            return
        dialog = RouteDialog(store, self.snapshot.adapters, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        draft = dialog.draft

        def task() -> RouteSnapshot:
            self.service.create_route(draft)
            return self.service.load_snapshot()

        self._run_task(f"正在新增{store.display_name}…", task, self._mutation_done("路由已新增"))

    def open_edit_dialog(self, route: RouteRecord) -> None:
        if not self._ensure_write_access():
            return
        dialog = RouteDialog(route.store, self.snapshot.adapters, route=route, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        draft = dialog.draft

        def task() -> RouteSnapshot:
            self.service.update_route(route, draft)
            return self.service.load_snapshot()

        self._run_task(f"正在修改{route.store.display_name}…", task, self._mutation_done("路由已更新"))

    def confirm_delete(self, route: RouteRecord) -> None:
        if not self._ensure_write_access():
            return
        detail = (
            f"确定删除下面这条{route.store.display_name}吗？\n\n"
            f"{route.destination_prefix}  →  {route.next_hop}\n"
            f"网络适配器：{route.interface_alias}（接口 {route.interface_index}）"
        )
        if route.store is RouteStore.PERSISTENT:
            detail += "\n\n删除后，当前活动副本也会一并移除。"
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setWindowTitle("确认删除路由")
        confirm.setText(detail)
        delete_button = confirm.addButton("删除路由", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = confirm.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        confirm.setDefaultButton(cancel_button)
        confirm.exec()
        if confirm.clickedButton() is not delete_button:
            return

        def task() -> RouteSnapshot:
            self.service.delete_route(route)
            return self.service.load_snapshot()

        self._run_task(f"正在删除{route.store.display_name}…", task, self._mutation_done("路由已删除"))

    def _mutation_done(self, message: str) -> Callable[[RouteSnapshot], None]:
        def callback(snapshot: RouteSnapshot) -> None:
            self._apply_snapshot(snapshot)
            self.status_label.setText(message)

        return callback

    def _run_task(
        self,
        label: str,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
    ) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.status_label.setText("已有操作正在执行，请稍候…")
            return
        self.status_label.setText(label)
        self._set_busy(True)
        worker = TaskThread(task, self)
        self._worker = worker
        worker.succeeded.connect(on_success)
        worker.failed.connect(self._show_error)
        worker.finished.connect(self._task_finished)
        worker.start()

    def _task_finished(self) -> None:
        worker = self._worker
        self._worker = None
        self._set_busy(False)
        if worker is not None:
            worker.deleteLater()

    def _show_error(self, message: str) -> None:
        self.status_label.setText("操作失败")
        QMessageBox.critical(
            self,
            "Windows 网络配置操作失败",
            message + "\n\n路由未按预期变更。请检查网关、网络接口和管理员权限。",
        )

    def _set_busy(self, busy: bool) -> None:
        self.busy_bar.setVisible(busy)
        self.dashboard.set_busy(busy)
        self.adapters_page.set_busy(busy)
        self.temporary_page.set_busy(busy)
        self.persistent_page.set_busy(busy)

    def _ensure_write_access(self) -> bool:
        if self._is_admin:
            return True
        QMessageBox.warning(
            self,
            "需要管理员权限",
            "修改 Windows 路由需要管理员权限。请关闭程序后，以管理员身份重新运行。",
        )
        return False

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _leave_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "操作进行中", "请等待当前网络配置操作完成后再退出。")
            event.ignore()
            return
        event.accept()
