from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
import json

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QHostAddress
from PyQt6.QtWebSockets import QWebSocketServer, QWebSocket

from .routes import utils

if TYPE_CHECKING:
    from yomu.core.app import YomuApp
    from yomu.core.models import Category, Chapter, Manga
    from yomu.source import Source


class MessageType(StrEnum):
    SOURCE_FILTERS_UPDATED = "SOURCE_FILTERS_UPDATED"

    LIBRARY_ADD = "LIBRARY_ADD"
    LIBRARY_REMOVE = "LIBRARY_REMOVE"
    MANGA_DETAILS_UPDATE = "MANGA_DETAILS_UPDATE"

    CHAPTER_LIST_UPDATE = "CHAPTER_LIST_UPDATE"
    CHAPTER_READ_STATUS_CHANGED = "CHAPTER_READ_STATUS_CHANGED"

    CATEGORY_CREATED = "CATEGORY_CREATED"
    CATEGORY_DELETED = "CATEGORY_DELETED"
    CATEGORY_MANGA_ADDED = "CATEGORY_MANGA_ADDED"
    CATEGORY_MANGA_REMOVED = "CATEGORY_MANGA_REMOVED"


class MessageHandler(QObject):
    def __init__(self, server: WebsocketServer, app: YomuApp):
        super().__init__(server)
        self.server = server

        app.source_filters_updated.connect(self.handle_source_filters_update)

        app.manga_library_status_changed.connect(self.handle_manga_library_status)
        app.manga_details_updated.connect(self.handle_updated_manga_details)

        app.chapter_list_updated.connect(self.handle_chapter_list_update)
        app.chapter_read_status_changed.connect(self.handle_chapter_read_status_status)

        app.category_created.connect(self.handle_category_created)
        app.category_deleted.connect(self.handle_category_deleted)
        app.category_manga_added.connect(self.handle_category_manga_added)
        app.category_manga_removed.connect(self.handle_category_manga_removed)

    def handle_source_filters_update(self, source: Source, filters: dict) -> None:
        self.server.send_message(
            MessageType.SOURCE_FILTERS_UPDATED, {"id": source.id, **filters}
        )

    def handle_manga_library_status(self, manga: Manga) -> None:
        if manga.library:
            message_type = MessageType.LIBRARY_ADD
            data = utils.convert_manga_to_json(manga)
        else:
            message_type = MessageType.LIBRARY_REMOVE
            data = {"id": manga.id}

        self.server.send_message(message_type, data)

    def handle_updated_manga_details(self, manga: Manga) -> None:
        self.server.send_message(
            MessageType.MANGA_DETAILS_UPDATE,
            {
                "id": manga.id,
                "title": manga.title,
                "description": manga.description,
                "author": manga.author,
                "artist": manga.artist,
                "thumbnail": manga.thumbnail,
                "initialized": manga.initialized,
            },
        )

    def handle_chapter_list_update(self, manga: Manga) -> None:
        self.server.send_message(MessageType.CHAPTER_LIST_UPDATE, {"id": manga.id})

    def handle_chapter_read_status_status(self, chapter: Chapter) -> None:
        self.server.send_message(
            MessageType.CHAPTER_READ_STATUS_CHANGED, {"id": chapter.id}
        )

    def handle_category_created(self, category: Category) -> None:
        self.server.send_message(
            MessageType.CATEGORY_CREATED, utils.convert_category_to_json(category)
        )

    def handle_category_deleted(self, category: Category) -> None:
        self.server.send_message(MessageType.CATEGORY_DELETED, {"id": category.id})

    def handle_category_manga_added(self, category: Category, manga: Manga) -> None:
        self.server.send_message(
            MessageType.CATEGORY_MANGA_ADDED,
            {"category_id": category.id, "manga_id": manga.id},
        )

    def handle_category_manga_removed(self, category: Category, manga: Manga) -> None:
        self.server.send_message(
            MessageType.CATEGORY_MANGA_REMOVED,
            {"category_id": category.id, "manga_id": manga.id},
        )


class WebsocketServer(QObject):
    started = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent: QObject, app: YomuApp, port: int) -> None:
        super().__init__(parent)
        self._server = QWebSocketServer(
            "YomuServer", QWebSocketServer.SslMode.NonSecureMode, self
        )
        self.port = port

        self._server.newConnection.connect(self._accept_connection)
        self._server.closed.connect(self.closed.emit)

        self._clients: set[QWebSocket] = set()
        self._message_handler = MessageHandler(self, app)

    def _accept_connection(self) -> None:
        client = self._server.nextPendingConnection()
        self._clients.add(client)
        client.disconnected.connect(self._client_disconnected)

    def _client_disconnected(self) -> None:
        client = self.sender()
        self._clients.discard(client)
        client.deleteLater()

    def send_message(self, message_type: MessageType, data: dict) -> None:
        message = json.dumps({"type": message_type, "data": data})
        for client in self._clients:
            client.sendTextMessage(message)

    def run(self) -> bool:
        address = QHostAddress(QHostAddress.SpecialAddress.AnyIPv4)
        started = self._server.listen(address, self.port)
        if started:
            self.started.emit()
        return started

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
