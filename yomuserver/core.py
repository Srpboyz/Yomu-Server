from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from yomu.core.app import YomuApp
from yomu.extension import YomuExtension

from .http import HttpServer
from .websocket import WebsocketServer
from .settings import SettingsDialog

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow


class Action(QAction):
    def show(self) -> None:
        self.setVisible(True)

    def hide(self) -> None:
        self.setVisible(False)


class YomuServerExtension(YomuExtension):
    def __init__(self, app: YomuApp, *args, **kwargs) -> None:
        super().__init__(app, *args, **kwargs)

        try:
            with open(os.path.join(os.path.dirname(__file__), "settings.json")) as f:
                self.settings = json.load(f)
        except Exception:
            self.settings = {"http_port": 6969, "ws_port": 42069, "autoconnect": False}

        http_port = self.settings.get("http_port", 6969)
        ws_port = self.settings.get("ws_port", 42069)

        self.http_server = HttpServer(self, http_port, app.logger)
        self.websocket_server = WebsocketServer(self, app, ws_port)
        self.websocket_server.started.connect(self.http_server.run)
        self.websocket_server.closed.connect(self.http_server.close)

        self.menu = QMenu()

        open_window = Action("Open Window", self.menu)
        open_window.triggered.connect(self._open_window)

        stop_action = Action("Stop Server", self.menu)
        stop_action.triggered.connect(self.websocket_server.close)
        self.websocket_server.started.connect(stop_action.show)
        self.websocket_server.closed.connect(stop_action.hide)
        stop_action.hide()

        start_action = Action("Start Server", self.menu)
        start_action.triggered.connect(self.run)
        self.websocket_server.started.connect(start_action.hide)
        self.websocket_server.closed.connect(start_action.show)

        self.menu.addActions([open_window, stop_action, start_action])
        self.menu.addAction("Exit").triggered.connect(app.quit)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(app.windowIcon())
        self.tray_icon.setToolTip("Yomu")
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._activated)
        self.tray_icon.show()

        self.settings_requested.connect(self.display_settings)
        app.window_created.connect(self._window_created)
        if self.settings.get("autoconnect", False):
            app.aboutToStart.connect(self.run)

    @property
    def name(self) -> str:
        return "Yomu Server"

    def eventFilter(self, window: ReaderWindow, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close and len(self.app.windows) < 2:
            window.hide()
            event.ignore()
            return True
        return False

    def _window_created(self, window: ReaderWindow) -> None:
        window.installEventFilter(self)

    def _open_window(self) -> None:
        if (window := self.app.window) is not None:
            window.activateWindow()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if (window := self.app.window) is not None:
                window.activateWindow()

    def update_settings(self, settings: dict) -> None:
        self.settings = settings
        with open(os.path.join(os.path.dirname(__file__), "settings.json"), "w") as f:
            json.dump(settings, f, indent=4)

    def display_message(
        self, message: str, *, duration: int = 3000, error: bool = False
    ) -> None:
        icon = QSystemTrayIcon.MessageIcon.Critical if error else self.tray_icon.icon()
        self.tray_icon.showMessage("Yomu", message, icon, duration)

    def display_settings(self, window: ReaderWindow) -> None:
        settings = deepcopy(self.settings)

        dialog = SettingsDialog(window, settings)
        dialog.settings_updated.connect(
            self.update_settings, Qt.ConnectionType.QueuedConnection
        )
        dialog.exec()

    def run(self) -> None:
        self.websocket_server.run()

    def unload(self) -> None:
        self.menu.deleteLater()
