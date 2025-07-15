from __future__ import annotations

from enum import IntEnum
from typing import Callable
import json as serializer

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QTcpSocket
from .request import HttpRequest


class StatusCode(IntEnum):
    # Success
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFORMATION = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206

    # Client Error
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    REQUEST_TIMEOUT = 408

    # Server Error
    INTERNAL_SERVER_ERROR = 500


class HttpResponse:
    def __init__(
        self,
        status: StatusCode = StatusCode.SUCCESS,
        headers: dict | None = None,
        body: bytes | str | None = None,
        json: dict | list | None = None,
    ):
        self.status = status
        self.headers = headers or {}

        if json is not None:
            self.body = serializer.dumps(json).encode()
        elif isinstance(body, str):
            self.body = body.encode()
        elif body is None:
            self.body = b""
        else:
            self.body = body


class AsyncHttpResponse(QObject):
    finished = pyqtSignal((QTcpSocket, HttpResponse, str))
    error_occured = pyqtSignal(Exception)

    def __init__(self, request: HttpRequest, func: Callable, *args, **kwargs) -> None:
        super().__init__()

        if not isinstance(request, HttpRequest):
            raise TypeError(f"Expected type HttpRequest not `{type(request)}`")

        self.request = request
        self.func = func
        self.extra_args = args
        self.extra_kwargs = kwargs
        self._client = None

    def wait_for_signal(self, *args) -> None:
        sender = self.sender()
        try:
            response = self.func(
                self.request, sender, *args, *self.extra_args, **self.extra_kwargs
            )
        except Exception as e:
            return self.error_occured.emit(e)

        if not isinstance(response, HttpResponse):
            return self.error_occured.emit(
                TypeError(f"Expected type `HttpResponse` not `{type(response)}`"),
            )

        self.finished.emit(self._client, response, self.request.version)

    def _set_client(self, client: QTcpSocket):
        self._client = client
        client.disconnected.connect(self.deleteLater)


def convert_response_to_http(response: HttpResponse, version: str) -> bytes:
    status = response.status
    status_name = response.status.name.replace("_", " ").title()

    headers = "\r\n".join(f"{key}: {value}" for key, value in response.headers.items())
    if len(headers):
        headers += "\r\n"

    body = response.body.encode() if isinstance(response.body, str) else response.body
    return f"{version} {status.value} {status_name}\r\n{headers}\r\n".encode() + body
