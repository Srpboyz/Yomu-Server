from __future__ import annotations


from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsWidget(QWidget):
    settings_updated = pyqtSignal(dict)

    def __init__(self, parent: QWidget, settings: dict) -> None:
        super().__init__(parent)
        self.settings = settings
        self.init_ui()

    def init_ui(self) -> None:
        self.checkbox = QCheckBox(self)
        self.checkbox.setText("Autoconnect")
        self.checkbox.setChecked(self.settings.get("autoconnect", False))
        self.checkbox.checkStateChanged.connect(self.save_settings)

        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        self.port_widget = QSpinBox(self)
        self.port_widget.setMinimum(0)
        self.port_widget.setMaximum(65535)
        self.port_widget.setValue(self.settings.get("http_port", 6969))
        self.port_widget.valueChanged.connect(self.save_settings)

        layout.addWidget(QLabel("HTTP Port"), 1, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.port_widget, alignment=Qt.AlignmentFlag.AlignRight)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.checkbox)
        layout.addSpacing(3)
        layout.addWidget(widget)
        self.setLayout(layout)

    def save_settings(self) -> None:
        updated = False

        autoconnect = self.checkbox.checkState() == Qt.CheckState.Checked
        updated = self.settings.get("autoconnect", False) != autoconnect
        self.settings["autoconnect"] = autoconnect

        new_http_port = self.port_widget.value()
        updated = updated or self.settings.get("http_port", 6969) != new_http_port
        self.settings["http_port"] = new_http_port

        if updated:
            self.settings_updated.emit(self.settings)
