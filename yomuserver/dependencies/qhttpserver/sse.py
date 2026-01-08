from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QTcpSocket
from .request import HttpRequest

__all__ = ("SSEResponse",)


class SSEResponse(QObject):
    event_occurred = pyqtSignal((str, str))
    finished = pyqtSignal()


class SSEResponseHandler(QObject):
    def __init__(
        self,
        parent: QObject,
        client: QTcpSocket,
        request: HttpRequest,
        response: SSEResponse,
    ) -> None:
        super().__init__(parent)
        self.request = request
        self.client = client
        client.disconnected.connect(self.deleteLater)

        self.response = response
        response.setParent(self)
        response.event_occurred.connect(self.send_message)
        response.finished.connect(self.sse_finished)

        self._send_initial_message()

    def _send_initial_message(self) -> None:
        self.client.write(
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
        self.client.flush()

    def send_message(self, event: str, message: str) -> None:
        self.client.write(f"event: {event}\ndata: {message}\n\n".encode())
        self.client.flush()

    def sse_finished(self) -> None:
        self.client.write(b"event: done\ndata:{}\n\n")
        self.client.flush()
        self.client.disconnectFromHost()
