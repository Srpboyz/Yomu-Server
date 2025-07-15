from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QHostAddress

from qhttpserver import QHttpServer
from .routes import *

if TYPE_CHECKING:
    from .core import YomuServerExtension


class HttpServer(QObject):
    started = pyqtSignal()
    closed = pyqtSignal()

    def __init__(
        self, ext: YomuServerExtension, port: int, logger: Logger | None = None
    ) -> None:
        super().__init__(ext)
        self._server = QHttpServer(
            ext, QHostAddress(QHostAddress.SpecialAddress.AnyIPv4), port, logger=logger
        )

        app = ext.app
        self._server.add_route_handler(LibraryHandler(app.sql))
        self._server.add_route_handler(
            SourceHandler(app.network, app.source_manager, app.sql)
        )
        self._server.add_route_handler(
            MangaHandler(app.network, app.downloader, app.sql, app.updater)
        )
        self._server.add_route_handler(ChapterHandler(app.network, app.sql))
        self._server.add_route_handler(WebPageHandler())

        self._server.started.connect(self.started.emit)
        self._server.closed.connect(self.closed.emit)

    def run(self) -> None:
        self._server.run()

    def close(self) -> None:
        self._server.close()
