from __future__ import annotations

from typing import TYPE_CHECKING

from qhttpserver import (
    HttpResponse,
    HttpRequest,
    RouteHandler,
    StatusCode,
    get,
    post,
    delete,
)

from .utils import convert_manga_to_json

if TYPE_CHECKING:
    from yomu.core.sql import Sql


class LibraryHandler(RouteHandler):
    BASE_PATH = "/api/library"

    def __init__(self, sql: Sql):
        super().__init__()
        self.sql = sql

    @get("/")
    def get_library(self, request: HttpRequest):
        mangas = self.sql.get_library()
        return HttpResponse(json=list(map(convert_manga_to_json, mangas)))

    @post("/<id:int>/")
    def add_manga_to_library(self, request: HttpRequest):
        manga_id = request.path_params["id"]

        manga = self.sql.get_manga_by_id(manga_id)
        if manga is None:
            return HttpResponse(StatusCode.NOT_FOUND)

        if manga.library or self.sql.set_library(manga, library=True):
            return HttpResponse(status=StatusCode.SUCCESS)
        return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

    @delete("/<id:int>/")
    def remove_manga_from_library(self, request: HttpRequest):
        manga_id = request.path_params["id"]

        manga = self.sql.get_manga_by_id(manga_id)
        if manga is None:
            return HttpResponse(StatusCode.NOT_FOUND)

        ret = self.sql.set_library(manga, library=False)
        if not manga.library or ret:
            return HttpResponse(status=StatusCode.SUCCESS)
        return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
