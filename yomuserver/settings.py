from __future__ import annotations


from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PortWidget(QWidget):
    def __init__(self, parent: SettingsDialog, name: str, port: int):
        super().__init__(parent)

        self.port_widget = QSpinBox(self)
        self.port_widget.setMinimum(0)
        self.port_widget.setMaximum(65535)
        self.port_widget.setValue(port)

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel(name), 1, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.port_widget, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

    def get_port(self) -> int:
        return self.port_widget.value()


class SettingsDialog(QDialog):
    settings_updated = pyqtSignal(dict)

    def __init__(self, window: QWidget, settings: dict) -> None:
        super().__init__(window)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.settings = settings
        self.init_ui()

        self.setContentsMargins(*[10 for _ in range(4)])
        self.resize(400, 200)

        self.accepted.connect(self.save_settings)

    def init_ui(self) -> None:
        self.checkbox = QCheckBox(self)
        self.checkbox.setText("Autoconnect")
        self.checkbox.setChecked(self.settings.get("autoconnect", False))

        self.http_port = PortWidget(
            self, "HTTP Port", self.settings.get("http_port", 6969)
        )

        self.ws_port = PortWidget(
            self, "Websocket Port", self.settings.get("ws_port", 42069)
        )

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.http_port)
        layout.addWidget(self.ws_port)
        layout.addWidget(buttonbox, 1, Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layout)

    def save_settings(self) -> None:
        updated = False

        autoconnect = self.checkbox.checkState() == Qt.CheckState.Checked
        updated = self.settings.get("autoconnect", False) != autoconnect
        self.settings["autoconnect"] = autoconnect

        new_http_port = self.http_port.get_port()
        updated = updated or self.settings.get("http_port", 6969) != new_http_port
        self.settings["http_port"] = new_http_port

        new_ws_port = self.ws_port.get_port()
        updated = updated or self.settings.get("ws_port", 42069) != new_ws_port
        self.settings["ws_port"] = new_ws_port

        if updated:
            self.settings_updated.emit(self.settings)
