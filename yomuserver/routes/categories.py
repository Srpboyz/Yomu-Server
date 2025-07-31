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


class CategoryHandler(RouteHandler):
    BASE_PATH = "/api/category"

    def __init__(self, sql: Sql):
        super().__init__()
        self.sql = sql

    @get("/")
    def get_categories(self, request: HttpRequest):
        categories = self.sql.get_categories()
        return HttpResponse(json=list(map(convert_category_to_json, categories)))

    @post("/create/<name>/")
    def create_category(self, request: HttpRequest):
        name = request.path_params["name"]

        category = self.sql.create_category(name)
        if category is None:
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
        return HttpResponse(
            status=StatusCode.SUCCESS, json=convert_category_to_json(category)
        )

    @delete("/<id:int>/")
    def delete_category(self, request: HttpRequest):
        category_id = request.path_params["id"]
        for category in self.sql.get_categories():
            if category.id == category_id:
                break
        else:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        if self.sql.delete_category(category) is None:
            return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
        return HttpResponse(status=StatusCode.SUCCESS)

    @get("/<id:int>/mangas")
    def get_category_mangas(self, request: HttpRequest):
        category_id = request.path_params["id"]
        for category in self.sql.get_categories():
            if category.id == category_id:
                break
        else:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        mangas = self.sql.get_category_mangas(category)
        return HttpResponse(
            status=StatusCode.SUCCESS, json=list(map(convert_manga_to_json, mangas))
        )

    @post("/<category_id:int>/manga/<manga_id:int>/")
    def add_manga_to_category(self, request: HttpRequest):
        params = request.path_params

        category_id = params.get("category_id")
        for category in self.sql.get_categories():
            if category.id == category_id:
                break
        else:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        manga = self.sql.get_manga_by_id(params.get("manga_id"))
        if manga is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)
        if not manga.library:
            return HttpResponse(status=StatusCode.BAD_REQUEST)

        if self.sql.add_manga_to_category(manga, category):
            return HttpResponse(status=StatusCode.SUCCESS)
        return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

    @delete("/<category_id:int>/manga/<manga_id:int>/")
    def remove_manga_from_category(self, request: HttpRequest):
        params = request.path_params

        category_id = params.get("category_id")
        for category in self.sql.get_categories():
            if category.id == category_id:
                break
        else:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        manga = self.sql.get_manga_by_id(params.get("manga_id"))
        if manga is None:
            return HttpResponse(StatusCode.NOT_FOUND)
        if not manga.library:
            return HttpResponse(StatusCode.BAD_REQUEST)

        if self.sql.remove_manga_from_category(manga, category):
            return HttpResponse(status=StatusCode.SUCCESS)
        return HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)
