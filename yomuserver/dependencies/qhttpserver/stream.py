from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QTcpSocket
from .request import HttpRequest

__all__ = ("StreamResponse", "SSEResponse")


class StreamResponse(QObject):
    ready = pyqtSignal()
    data_received = pyqtSignal(bytes)
    finished = pyqtSignal()


class SSEResponse(StreamResponse):
    event_occurred = pyqtSignal((str, str))

    def __init__(self) -> None:
        super().__init__()
        self.ready.connect(self.on_ready)
        self.event_occurred.connect(self.on_event_occured)

    def on_ready(self) -> None:
        self.data_received.emit(
            (
                f"HTTP/1.1 200 OK\r\n"
                "Content-Type: text/event-stream\r\n"
                "Cache-Control: no-cache\r\n"
                "Connection: keep-alive\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Access-Control-Allow-Credentials: false\r\n"
                "\r\n"
            ).encode()
        )
        self.on_event_occured("open", "connected")

    def on_event_occured(self, event: str, message: str) -> None:
        self.data_received.emit(f"event: {event}\r\ndata: {message}\r\n\r\n".encode())


class StreamResponseHandler(QObject):
    def __init__(
        self,
        parent: QObject,
        client: QTcpSocket,
        request: HttpRequest,
        response: StreamResponse,
    ) -> None:
        super().__init__(parent)
        self.request = request
        self.client = client
        client.disconnected.connect(self.deleteLater)

        self.response = response
        response.setParent(self)
        response.data_received.connect(self.send_message)
        response.finished.connect(self.sse_finished)
        response.ready.emit()

    def send_message(self, message: bytes) -> None:
        self.client.write(message)
        self.client.flush()

    def sse_finished(self) -> None:
        self.client.flush()
        self.client.disconnectFromHost()
