from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QBuffer, Qt, QUrl
from PyQt6.QtGui import QImage

from yomu.core.network import Request, Response
from qhttpserver import (
    get,
    post,
    AsyncHttpResponse,
    HttpResponse,
    HttpRequest,
    RouteHandler,
    StatusCode,
)

from .utils import convert_manga_to_json, convert_chapter_to_json

if TYPE_CHECKING:
    from yomu.core.network import Network
    from yomu.core.downloader import Downloader
    from yomu.core.sql import Sql
    from yomu.core.updater import Updater
    from yomu.source import Source


class MangaHandler(RouteHandler):
    BASE_PATH = "/api/manga"

    def __init__(
        self, network: Network, downloader: Downloader, sql: Sql, updater: Updater
    ) -> None:
        super().__init__()
        self.network = network
        self.downloader = downloader
        self.sql = sql
        self.updater = updater

    @get("/<id:int>")
    def get_manga(self, request: HttpRequest):
        manga_id = request.path_params["id"]

        manga = self.sql.get_manga_by_id(manga_id)
        if manga is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        return HttpResponse(json=convert_manga_to_json(manga))

    @get("/<id:int>/chapters")
    def get_chapters(self, request: HttpRequest):
        manga_id = request.path_params["id"]

        manga = self.sql.get_manga_by_id(manga_id)
        if manga is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        chapters = self.sql.get_chapters(manga)
        return HttpResponse(
            json=sorted(
                map(lambda chapter: convert_chapter_to_json(chapter), chapters),
                key=lambda chapter: chapter["number"],
            )
        )

    @post("/<id:int>/update")
    def update_manga(self, request: HttpRequest):
        manga = self.sql.get_manga_by_id(request.path_params["id"])
        if manga is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        details = self.updater.update_manga_details(manga)
        chapters = self.updater.update_manga_chapters(manga)

        if not details and not chapters:
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

        return HttpResponse()

    @get("/<id:int>/thumbnail")
    def load_thumbnail(self, request: HttpRequest):
        manga = self.sql.get_manga_by_id(request.path_params["id"])
        if manga is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)
        source = manga.source

        path = self.downloader.resolve_path(manga)
        r: Request = (
            Request(QUrl.fromLocalFile(os.path.join(path, "thumbnail.png")))
            if manga.library and os.path.exists(path)
            else manga.get_thumbnail()
        )
        r.setPriority(Request.Priority.LowPriority)
        response = self.network.handle_request(r)

        server_response = AsyncHttpResponse(request, self._thumbnail_received, source)
        response.finished.connect(server_response.wait_for_signal)
        return server_response

    def _thumbnail_received(self, _, reply: Response, source: Source):
        error = reply.error()
        if error != Response.Error.NoError:
            if error != Response.Error.OperationCanceledError:
                source.thumbnail_request_error(reply)
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)

        data = source.parse_thumbnail(reply)

        image = QImage()
        if not image.loadFromData(data):
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)
        image = image.scaledToWidth(720, Qt.TransformationMode.SmoothTransformation)

        buffer = QBuffer(reply)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "JPG"):
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)

        data = buffer.data()

        headers = {
            header.data().decode(): value.data().decode()
            for (header, value) in reply.headers.toListOfPairs()
        }
        headers["content-type"] = "image/jpeg"
        headers["content-length"] = len(data)

        return HttpResponse(headers=headers, body=data)
