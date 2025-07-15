from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING

from yomu.core.network import Request, Response
from yomu.source import Source
from qhttpserver import (
    get,
    post,
    AsyncHttpResponse,
    HttpResponse,
    HttpRequest,
    RouteHandler,
    StatusCode,
)

from .utils import convert_manga_to_json, convert_source_to_json

if TYPE_CHECKING:
    from yomu.core.sourcemanager import SourceManager
    from yomu.core.network import Network
    from yomu.core.sql import Sql


class SourceHandler(RouteHandler):
    BASE_PATH = "/api/sources"

    def __init__(self, network: Network, source_manager: SourceManager, sql: Sql):
        super().__init__()
        self.network = network
        self.source_manager = source_manager
        self.sql = sql

    @get("/")
    def get_sources(self, request: HttpRequest):
        return HttpResponse(
            json=list(map(convert_source_to_json, self.source_manager.sources))
        )

    @get("/<id:int>/icon")
    def get_source_icon(self, request: HttpRequest):
        source = self.source_manager.get_source(request.path_params["id"])
        if source is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(inspect.getfile(source.__class__))),
            "icon.ico",
        )

        with open(icon_path, "rb") as f:
            image_data = f.read()

        headers = {"Content-Type": "image/png", "Content-Length": len(image_data)}
        return HttpResponse(headers=headers, body=image_data)

    @get("/<id:int>/latest/<page:int>/")
    def get_latest(self, request: HttpRequest):
        params = request.path_params
        source = self.source_manager.get_source(params["id"])
        if source is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        page = params["page"]
        r = source.get_latest(page)
        r.setPriority(Request.Priority.HighPriority)
        response = self.network.handle_request(r)

        server_response = AsyncHttpResponse(
            request, self._latest_mangas_received, source
        )
        response.finished.connect(server_response.wait_for_signal)
        return server_response

    def _latest_mangas_received(self, _, reply: Response, source: Source):
        error = reply.error()
        if error != Response.Error.NoError:
            if error != Response.Error.OperationCanceledError:
                source.latest_request_error(reply)
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)

        manga_list = source.parse_latest(reply)
        mangas = self.sql.add_and_get_mangas(source, manga_list.mangas)

        body = {
            "mangas": list(map(convert_manga_to_json, mangas)),
            "has_next_page": manga_list.has_next_page,
        }
        return HttpResponse(json=body)

    @get("/<id:int>/search/<name>/")
    def get_search(self, request: HttpRequest):
        params = request.path_params
        source = self.source_manager.get_source(params["id"])
        if source is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        name = params["name"]
        r = source.search_for_manga(name)
        r.setPriority(Request.Priority.HighPriority)
        reply = self.network.handle_request(r)

        response = AsyncHttpResponse(request, self._search_mangas_received, source)
        reply.finished.connect(response.wait_for_signal)
        return response

    def _search_mangas_received(self, _, reply: Response, source: Source):
        error = reply.error()
        if error != Response.Error.NoError:
            if error != Response.Error.OperationCanceledError:
                source.search_request_error(reply)
            return HttpResponse(StatusCode.INTERNAL_SERVER_ERROR)

        manga_list = source.parse_search_results(reply)
        mangas = self.sql.add_and_get_mangas(source, manga_list.mangas)

        body = {
            "mangas": list(map(convert_manga_to_json, mangas)),
            "has_next_page": manga_list.has_next_page,
        }
        return HttpResponse(json=body)

    @post("/<id:int>/filters")
    def update_filters(self, request: HttpRequest):
        source = self.source_manager.get_source(request.path_params["id"])
        if source is None:
            return HttpResponse(status=StatusCode.NOT_FOUND)

        new_filters = {}
        for filter in request.json():
            if filter["type"] == "LIST":
                values = filter["value"]
                if isinstance(values, list) and all(
                    (isinstance(value, str) for value in values)
                ):
                    new_filters[filter["key"]] = values
            elif filter["type"] == "CHECKBOX":
                new_filters[filter["key"]] = filter["value"]

        self.source_manager.update_source_filters(source, new_filters)

        return HttpResponse()
