from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QTcpSocket
from .request import HttpRequest

__all__ = ("StreamResponse",)


class StreamResponse(QObject):
    ready = pyqtSignal()
    data_received = pyqtSignal(bytes)
    finished = pyqtSignal()


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
        response.finished.connect(self.on_stream_finished)
        response.destroyed.connect(self.deleteLater)
        response.ready.emit()

    def on_stream_finished(self) -> None:
        self.client.flush()
        self.client.disconnectFromHost()
        self.deleteLater()

    def send_message(self, message: bytes) -> None:
        self.client.write(message)
        self.client.flush()
