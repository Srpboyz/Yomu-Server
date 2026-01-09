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

        query = self.sql.create_query()
        query.exec(
            """CREATE TABLE IF NOT EXISTS pages (chapter_id INTEGER NOT NULL,
                                                 number INTEGER NOT NULL,
                                                 url TEXT NOT NULL,
                                                 PRIMARY KEY(chapter_id, number),
                                                 FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE);"""
        )

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
            return HttpResponse(
                json={"pages": len(os.listdir(Downloader.resolve_path(chapter)))}
            )

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
        page_count = len(pages)

        query = self.sql.create_query()
        query.prepare(
            """INSERT INTO pages VALUES (:chapter_id, :number, :url)
               ON CONFLICT(chapter_id, number) DO UPDATE
               SET url = COALESCE(EXCLUDED.url, url)
            """
        )
        query.addBindValue([chapter.id] * page_count)
        query.addBindValue(list(range(page_count)))
        query.addBindValue(
            [page.url for page in sorted(pages, key=lambda page: page.number)]
        )
        if not query.execBatch():
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

        return HttpResponse(json={"pages": page_count})

    @get("/<id:int>/page/<index:int>")
    def load_images(self, request: HttpRequest):
        chapter = self.sql.get_chapter_by_id(request.path_params["id"])
        if chapter is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        source = chapter.source
        index: int = request.path_params["index"]

        if chapter.downloaded:
            page = None
            r = Request(
                QUrl.fromLocalFile(
                    os.path.join(Downloader.resolve_path(chapter), f"{index}.png")
                )
            )
        else:
            query = self.sql.create_query()
            query.prepare(
                "SELECT url FROM pages WHERE chapter_id = :chapter_id AND number = :number"
            )
            query.bindValue(":chapter_id", chapter.id)
            query.bindValue(":number", index)
            if not query.exec() or not query.first():
                return HttpResponse(status=StatusCode.NOT_FOUND)

            page = SourcePage(number=0, url=query.value("url"))
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
