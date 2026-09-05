from __future__ import annotations

from enum import StrEnum
from typing import Any, Self
from urllib.parse import parse_qs, urlparse
import json


class Method(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    @classmethod
    def get_method(cls, method: str) -> Self | None:
        try:
            return cls(method.upper())
        except ValueError:
            return None


class HttpRequest[T = dict[str, Any]]:
    def __init__(
        self,
        method: Method,
        version: float,
        path: str,
        headers: dict[str, str],
        body: str,
        params: dict[str, list[str]],
    ) -> None:
        self.method = method
        self.version = version
        self.path = path
        self.headers = headers
        self.body = body

        self.path_params: dict[str, str] = {}
        self.query_params = params.copy()

    @classmethod
    def from_raw_data(cls, data: bytes) -> Self | None:
        request = data.decode("iso-8859-1")
        if not (lines := request.split("\r\n")):
            return None
        http_info = lines[0].split(" ")

        method = Method.get_method(http_info[0])
        if method is None:
            return None

        parsed_url_path = urlparse(http_info[1])
        path = parsed_url_path.path
        query_params = parse_qs(parsed_url_path.query)
        version = float(http_info[2].split("/")[1])

        headers = {}
        for i, line in enumerate(lines[1:], start=1):
            if not line:
                break

            key, value = line.split(": ")
            headers[key] = value
        else:
            i += 1

        body = "\n".join(lines[i:]) if i < len(lines) else ""
        return cls(method, version, path, headers, body, query_params)

    def json(self) -> T | None:
        try:
            return json.loads(self.body)
        except Exception:
            return None

    def __str__(self) -> str:
        return f"<HttpRequest method={self.method.name} version={self.version} path={self.path}>"
