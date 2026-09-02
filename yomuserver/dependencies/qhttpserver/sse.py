from PyQt6.QtCore import pyqtSignal, QTimer
from .stream import StreamResponse

__all__ = ("SSEResponse",)


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

        timer = QTimer(self)
        timer.setInterval(20_000)
        timer.timeout.connect(self.keep_alive)
        timer.start()

    def on_event_occured(self, event: str, message: str) -> None:
        self.data_received.emit(f"event: {event}\r\ndata: {message}\r\n\r\n".encode())

    def keep_alive(self) -> None:
        self.data_received.emit("event: heartbeat\r\ndata: ping\r\n\r\n".encode())
