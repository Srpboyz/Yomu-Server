from __future__ import annotations

from logging import Logger
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

from .router import Router
from .request import HttpRequest, Method
from .response import (
    convert_response_to_http,
    AsyncHttpResponse,
    HttpResponse,
    StatusCode,
)

if TYPE_CHECKING:
    from .handler import RouteHandler


class QHttpServer(QObject):
    started = pyqtSignal()
    closed = pyqtSignal()

    def __init__(
        self,
        parent: QObject = None,
        address: QHostAddress | None = None,
        port: int | None = None,
        logger: Logger | None = None,
    ):
        super().__init__(parent)
        self.address = address or QHostAddress(QHostAddress.SpecialAddress.LocalHost)
        self.port = port or 6969
        self.logger = logger

        self._server = QTcpServer(self)
        self._router = Router()

        self._server.newConnection.connect(self._new_connection)

    @property
    def isRunning(self) -> None:
        return self._server.isListening()

    def _new_connection(self) -> None:
        client = self._server.nextPendingConnection()
        if client is None:
            return

        client.readyRead.connect(self._data_received)

    def _data_received(self) -> None:
        client: QTcpSocket = self.sender()
        request = HttpRequest.from_raw_data(client.readAll().data())

        if request is None:
            response = HttpResponse(status=StatusCode.BAD_REQUEST)
            message = convert_response_to_http(response, "HTTP/1.1")
            client.write(message.encode())
            return client.disconnectFromHost()

        path = request.path
        route = self._router.get_path_handler(path)

        if route is None:
            response = HttpResponse(status=StatusCode.NOT_FOUND)
            return self._reply(client, response, request.version)

        func = route.methods.get(request.method)
        if func is None:
            response = HttpResponse(status=StatusCode.METHOD_NOT_ALLOWED)
            return self._reply(client, response, request.version)

        if route.has_path_params:
            request.path_params = route.get_params(path)

        try:
            response = func(request)
        except Exception as e:
            if self.logger:
                self.logger.exception(
                    f"{e.__class__.__name__} occurred while calling {func.__name__}"
                )
            response = HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

        if isinstance(response, AsyncHttpResponse):
            response.setParent(self)
            response._set_client(client)
            response.finished.connect(self._reply)
            response.error_occured.connect(self._async_response_error)
            return

        return self._reply(client, response, request.version)

    def _reply(self, client: QTcpSocket, response: HttpResponse, version: str) -> None:
        message = convert_response_to_http(response, version)
        client.write(message)
        client.disconnectFromHost()

    def _async_response_error(self, error: Exception) -> None:
        response: AsyncHttpResponse = self.sender()
        if self.logger:
            self.logger.exception(
                f"{error.__class__.__name__} occurred while calling {response.func.__name__}"
            )

        self._reply(
            response._client,
            HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR),
            response.request.version,
        )

    def get(self, path: str):
        def wrapper(func: Callable):
            self._router.add_route(Method.GET, path, func)
            return func

        return wrapper

    def post(self, path: str):
        def wrapper(func: Callable):
            self._router.add_route(Method.POST, path, func)
            return func

        return wrapper

    def put(self, path: str):
        def wrapper(func: Callable):
            self._router.add_route(Method.PUT, path, func)
            return func

        return wrapper

    def delete(self, path: str):
        def wrapper(func: Callable):
            self._router.add_route(Method.DELETE, path, func)
            return func

        return wrapper

    def add_route_handler(self, handler: RouteHandler) -> None:
        self._router.add_route_handler(handler)

    def run(self) -> bool:
        if self._server.listen(self.address, self.port):
            self.started.emit()
            return True
        return False

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
            self.closed.emit()
