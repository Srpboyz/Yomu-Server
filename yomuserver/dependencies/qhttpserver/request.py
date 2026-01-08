from __future__ import annotations

from enum import StrEnum
from urllib.parse import parse_qs, urlparse
import json


class Method(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"

    @classmethod
    def get_method(cls, method: str) -> Method | None:
        try:
            return cls(method.upper())
        except ValueError:
            return None


class HttpRequest:
    def __init__(
        self,
        method: Method,
        version: float,
        path: str,
        headers: dict,
        body: str | None,
        params: dict,
    ) -> None:
        self.method = method
        self.version = version
        self.path = path
        self.headers = headers
        self.body = body

        self.path_params = {}
        self.query_params: dict = params.copy()

    @classmethod
    def from_raw_data(cls, data: bytes) -> HttpRequest | None:
        request = data.decode()
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

        body = "\n".join(lines[i:]) if i < len(lines) else None
        return cls(method, version, path, headers, body, query_params)

    def json(self) -> dict | None:
        if not self.body:
            return None

        try:
            data = json.loads(self.body)
        except Exception:
            return None
        else:
            return data

    def __str__(self) -> str:
        return f"<HttpRequest method={self.method.name} version={self.version} path={self.path}>"
