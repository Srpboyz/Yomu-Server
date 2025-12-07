from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QBuffer, Qt, QUrl
from PyQt6.QtGui import QImage

from yomu.core.network import Response, Request
from yomu.core.downloader import Downloader
from yomu.source.models import Page as SourcePage

from qhttpserver import (
    get,
    post,
    AsyncHttpResponse,
    HttpResponse,
    HttpRequest,
    RouteHandler,
    StatusCode,
)

from .utils import convert_chapter_to_json

if TYPE_CHECKING:
    from yomu.core.models import Chapter
    from yomu.core.network import Network
    from yomu.core.sql import Sql
    from yomu.source import Source


class ChapterHandler(RouteHandler):
    BASE_PATH = "/api/chapter"

    def __init__(self, network: Network, sql: Sql) -> None:
        super().__init__()
        self.network = network
        self.sql = sql

    def mark_read_status(self, id: int, read: bool) -> bool:
        chapter = self.sql.get_chapter_by_id(id)
        if chapter is None:
            return False

        self.sql.mark_chapters_read_status([chapter], read=read)
        return chapter.read

    @get("/<id:int>")
    def get_chapter(self, request: HttpRequest):
        chapter = self.sql.get_chapter_by_id(request.path_params["id"])
        if chapter is None:
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
        return HttpResponse(json=convert_chapter_to_json(chapter))

    @post("/<id:int>/read")
    def mark_chapter_as_read(self, request: HttpRequest):
        chapter_id = request.path_params["id"]
        if not self.mark_read_status(chapter_id, True):
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
        return HttpResponse()

    @post("/<id:int>/unread")
    def mark_chapter_as_unread(self, request: HttpRequest):
        chapter_id = request.path_params["id"]
        if not self.mark_read_status(chapter_id, False):
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
        return HttpResponse()

    @get("/<id:int>/pages")
    def get_chapter_pages(self, request: HttpRequest):
        chapter = self.sql.get_chapter_by_id(request.path_params["id"])
        if chapter is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        if chapter.downloaded:
            return HttpResponse(json=os.listdir(Downloader.resolve_path(chapter)))

        r = chapter.source.get_chapter_pages(chapter)
        r.setPriority(Request.Priority.HighPriority)
        response = self.network.handle_request(r)

        server_response = AsyncHttpResponse(
            request, self._chapter_pages_received, chapter
        )
        response.finished.connect(server_response.wait_for_signal)
        return server_response

    def _chapter_pages_received(self, _, response: Response, chapter: Chapter):
        pages = chapter.source.parse_chapter_pages(response, chapter)
        return HttpResponse(json=[page.url for page in pages])

    @get("/<id:int>/page")
    def load_images(self, request: HttpRequest):
        chapter = self.sql.get_chapter_by_id(request.path_params["id"])
        if chapter is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        source = chapter.source
        url = request.query_params["url"][0]

        if chapter.downloaded:
            page = None
            r = Request(
                QUrl.fromLocalFile(os.path.join(Downloader.resolve_path(chapter), url))
            )
        else:
            page = SourcePage(number=0, url=url)
            r = source.get_page(page)
            r.setPriority(Request.Priority.HighPriority)

        response = self.network.handle_request(r)
        server_response = AsyncHttpResponse(
            request, self._page_image_received, source, page
        )
        response.finished.connect(server_response.wait_for_signal)
        return server_response

    def _page_image_received(
        self, _, response: Response, source: Source, page: SourcePage | None
    ):
        error = response.error()
        if error != Response.Error.NoError:
            if error != Response.Error.OperationCanceledError:
                source.page_request_error(response, page)
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)

        data = (
            source.parse_page(response, page)
            if not response.url().isLocalFile()
            else response.read_all()
        )

        image = QImage()
        if not image.loadFromData(data):
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)
        image = image.scaledToWidth(720, Qt.TransformationMode.SmoothTransformation)

        buffer = QBuffer(response)
        buffer.open(QBuffer.OpenModeFlag.ReadWrite)
        if not image.save(buffer, "JPG"):
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)

        data = buffer.data()

        headers = {
            header.data().decode(): value.data().decode()
            for (header, value) in response.headers.toListOfPairs()
        }
        headers["content-type"] = "image/jpeg"
        headers["content-length"] = len(data)

        return HttpResponse(headers=headers, body=data)
