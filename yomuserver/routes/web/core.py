from __future__ import annotations

import mimetypes
import os

from qhttpserver import HttpResponse, HttpRequest, RouteHandler, StatusCode, get


STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class WebPageHandler(RouteHandler):
    BASE_PATH = ""

    def send_html(self) -> HttpResponse:
        with open(os.path.join(STATIC_FOLDER, "index.html")) as f:
            html = f.read()
        return HttpResponse(body=html)

    @get("/")
    def get_homepage(self, request: HttpRequest):
        return self.send_html()

    @get("/sources")
    def get_sourcelist_page(self, request: HttpRequest):
        return self.send_html()

    @get("/source/<source_id:int>")
    def get_sources_page(self, request: HttpRequest):
        return self.send_html()

    @get("/manga/<manga_id:int>/")
    def get_mangacard_page(self, request: HttpRequest):
        return self.send_html()

    @get("/reader/<chapter_id:int>/")
    def get_reader_page(self, request: HttpRequest):
        return self.send_html()

    @get("/<file>")
    def get_file(self, request: HttpRequest):
        if (file := request.path_params.get("file")) is None:
            return HttpResponse(StatusCode.BAD_REQUEST)

        path = os.path.join(STATIC_FOLDER, file)

        try:
            with open(path, "rb") as f:
                file_content = f.read()
        except OSError:
            return HttpResponse(StatusCode.NOT_FOUND)

        headers = {"content-type": mimetypes.guess_file_type(path)[0]}
        return HttpResponse(headers=headers, body=file_content)

    @get("/assets/<file>")
    def get_asset(self, request: HttpRequest):
        if (file := request.path_params.get("file")) is None:
            return HttpResponse(StatusCode.BAD_REQUEST)

        path = os.path.join(STATIC_FOLDER, "assets", file)

        try:
            with open(path, "rb") as f:
                file_content = f.read()
        except OSError:
            return HttpResponse(StatusCode.NOT_FOUND)

        headers = {"content-type": mimetypes.guess_file_type(path)[0]}
        return HttpResponse(headers=headers, body=file_content)
