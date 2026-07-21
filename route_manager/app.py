from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow
from .theme import APP_STYLE


def create_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#3978f6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 15, 15)
    pen = QPen(QColor("#ffffff"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(16, 24, 47, 24)
    painter.drawLine(40, 17, 47, 24)
    painter.drawLine(47, 24, 40, 31)
    painter.drawLine(48, 41, 17, 41)
    painter.drawLine(24, 34, 17, 41)
    painter.drawLine(17, 41, 24, 48)
    painter.end()
    return QIcon(pixmap)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("RoutePilot")
    app.setApplicationDisplayName("RoutePilot · Windows 路由管理器")
    app.setOrganizationName("RoutePilot")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    app.setWindowIcon(create_app_icon())

    window = MainWindow()
    window.setWindowIcon(create_app_icon())
    window.showMaximized()
    window.refresh_snapshot()
    return app.exec()

