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

from .utils import convert_category_to_json, convert_manga_to_json

if TYPE_CHECKING:
    from yomu.core.sql import Sql


class LibraryHandler(RouteHandler):
    BASE_PATH = "/api/category"

    def __init__(self, sql: Sql):
        super().__init__()
        self.sql = sql

    @get("/")
    def get_categories(self, request: HttpRequest):
        categories = self.sql.get_categories()
        return HttpResponse(json=list(map(convert_category_to_json, categories)))

    @post("/<name>/")
    def create_category(self, request: HttpRequest):
        name = request.path_params["name"]
        if self.sql.create_category(name) is None:
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
        return HttpResponse(status=StatusCode.SUCCESS)

    # @delete("/<id:int>/")
    # def delete_category(self, request: HttpRequest):
    #     category_id = request.path_params["id"]
    #     if self.sql.delete_category(category_id) is None:
    #         return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
    #     return HttpResponse(status=StatusCode.SUCCESS)

    # @post("/<id:int>/")
    # def add_manga_to_category(self, request: HttpRequest):
    #     params = request.path_params
    #     manga_id = params.get("id")

    #     manga = self.sql.get_manga_by_id(manga_id)
    #     if manga is None:
    #         return HttpResponse(StatusCode.NOT_FOUND)

    #     if manga.library or self.sql.set_library(manga, library=True):
    #         return HttpResponse(status=StatusCode.SUCCESS)
    #     return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

    # @delete("/<id:int>/")
    # def remove_manga_from_category(self, request: HttpRequest):
    #     params = request.path_params
    #     manga_id = params.get("id")

    #     manga = self.sql.get_manga_by_id(manga_id)
    #     if manga is None:
    #         return HttpResponse(StatusCode.NOT_FOUND)

    #     ret = self.sql.set_library(manga, library=False)
    #     if not manga.library or ret:
    #         return HttpResponse(status=StatusCode.SUCCESS)
    #     return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
