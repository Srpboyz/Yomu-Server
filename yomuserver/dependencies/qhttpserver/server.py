from __future__ import annotations

from logging import getLogger
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
from .stream import StreamResponse, StreamResponseHandler
from .utils import pyqtSlot

if TYPE_CHECKING:
    from .handler import RouteHandler


class QHttpServer(QObject):
    started = pyqtSignal()
    closed = pyqtSignal()

    def __init__(
        self,
        address: QHostAddress,
        port: int,
        name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.name = name or "qhttpserver"
        self.address = address
        self._port = port
        self._is_restarting = False

        self._server = QTcpServer(self)
        self._router = Router()
        self.logger = getLogger(self.name)

        self._server.newConnection.connect(self.on_new_connection)

    @property
    def is_running(self) -> None:
        return self._server.isListening()

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, port: int) -> None:
        self._port = port
        self._is_restarting = True
        self.close()
        self.run()
        self._is_restarting = False

    def on_new_connection(self) -> None:
        client = self._server.nextPendingConnection()
        if client is None:
            return

        client.readyRead.connect(self.on_data_received)

    @pyqtSlot(getLogger(__name__))
    def on_data_received(self) -> None:
        client: QTcpSocket = self.sender()
        data = client.readAll().data()
        try:
            request = HttpRequest.from_raw_data(data)
        except Exception as e:
            self.logger.error(
                f"{client.peerAddress().toString()}:{client.peerPort()} - Failed to parse message",
                exc_info=e,
            )
            response = HttpResponse(status=StatusCode.BAD_REQUEST)
            message = convert_response_to_http(response)
            client.write(message)
            return client.disconnectFromHost()

        if request is None:
            response = HttpResponse(status=StatusCode.BAD_REQUEST)
            message = convert_response_to_http(response)
            client.write(message)
            return client.disconnectFromHost()

        path = request.path
        route = self._router.get_path_handler(path)

        if route is None:
            response = HttpResponse(status=StatusCode.NOT_FOUND)
            return self.send_response(client, request, response)

        method = request.method
        func = route.methods.get(method)
        if func is None:
            response = HttpResponse(status=StatusCode.METHOD_NOT_ALLOWED)
            return self.send_response(client, request, response)

        if route.has_path_params:
            request.path_params = route.get_params(path)

        try:
            response: AsyncHttpResponse | HttpRequest | StreamResponse = func(request)
        except Exception as e:
            self.logger.exception(
                f"Exception occurred while calling {func.__name__}", exc_info=e
            )
            response = HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR)

        if isinstance(response, AsyncHttpResponse):
            response.setParent(self)
            response._set_client(client)
            response.finished.connect(self.send_response)
            response.error_occured.connect(self.on_async_response_error)
            return

        if isinstance(response, StreamResponse):
            StreamResponseHandler(self, client, request, response)
            address, port, status = (
                client.peerAddress().toString(),
                client.peerPort(),
                StatusCode.OK,
            )
            self.log_request(address, port, method, path, status)
            return

        self.send_response(client, request, response)

    def on_async_response_error(self, error: Exception) -> None:
        response: AsyncHttpResponse = self.sender()
        self.logger.exception(
            f"Exception occurred while calling {response.func.__name__}", exc_info=error
        )

        self.send_response(
            response._client,
            response.request,
            HttpResponse(status=StatusCode.INTERNAL_SERVER_ERROR),
        )

    def log_request(
        self, address: str, port: int, method: Method, path: str, status: StatusCode
    ) -> None:
        self.logger.info(
            f"{address}:{port} - {method} {path} HTTP/1.1 {status} {status.to_str()}"
        )

    @pyqtSlot(getLogger(__name__))
    def send_response(
        self, client: QTcpSocket, request: HttpRequest, response: HttpResponse
    ) -> None:
        address, port, method, path, status = (
            client.peerAddress().toString(),
            client.peerPort(),
            request.method,
            request.path,
            response.status,
        )

        self.log_request(address, port, method, path, status)

        message = convert_response_to_http(response)
        client.write(message)
        client.disconnectFromHost()

    def get(self, path: str):
        self.logger.debug(f"Adding GET endpoint: {path}")

        def wrapper(func: Callable):
            self._router.add_route(Method.GET, path, func)
            return func

        return wrapper

    def post(self, path: str):
        self.logger.debug(f"Adding POST endpoint: {path}")

        def wrapper(func: Callable):
            self._router.add_route(Method.POST, path, func)
            return func

        return wrapper

    def put(self, path: str):
        self.logger.debug(f"Adding PUT endpoint: {path}")

        def wrapper(func: Callable):
            self._router.add_route(Method.PUT, path, func)
            return func

        return wrapper

    def delete(self, path: str):
        self.logger.debug(f"Adding DELETE endpoint: {path}")

        def wrapper(func: Callable):
            self._router.add_route(Method.DELETE, path, func)
            return func

        return wrapper

    def add_route_handler(self, handler: RouteHandler) -> None:
        self.logger.debug(f"Adding Route Handler: {handler.__class__.__name__}")
        self._router.add_route_handler(handler)

    def run(self) -> bool:
        self.logger.debug("Yomu server is starting up")
        if self._server.isListening():
            return True

        if not self._server.listen(self.address, self.port):
            self.logger.warning("Yomu server failed to start")
            return False

        self.logger.debug("Yomu server started up")
        if not self._is_restarting:
            self.started.emit()
        return True

    def close(self) -> None:
        if not self._server.isListening():
            return

        self.logger.debug("Closing Yomu server...")
        self._server.close()
        self.logger.debug("Yomu server closed")

        if not self._is_restarting:
            self.closed.emit()
