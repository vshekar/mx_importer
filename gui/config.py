from qtpy.QtWidgets import (
    QDialog,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QCheckBox,
)
from .listWidget import ListWidget
from pathlib import Path
import json
import pandas as pd


class ConfigurationWindow(QDialog):
    def __init__(self, *args, config, puck_list, **kwargs):
        self.config = config
        self.puck_list = puck_list
        super().__init__(*args, **kwargs)
        self.setModal(True)

        self.okButton = QPushButton("OK")
        self.applyButton = QPushButton("Apply")
        self.cancelButton = QPushButton("Cancel")

        self.okButton.clicked.connect(self.okClicked)
        self.applyButton.clicked.connect(self.applyClicked)
        self.cancelButton.clicked.connect(self.cancelClicked)

        self.setWindowTitle("Preferences")
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.applyButton)
        hbox.addWidget(self.cancelButton)
        hbox.addStretch()
        vbox = QVBoxLayout()
        formLayout = self.generate_layout()
        vbox.addLayout(formLayout)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        self.show()

    def toggleWhitelist(self, value):
        self.whitelistWidget.setDisabled(value)
        self.config["disable_whitelist"] = value

    def toggleBlacklist(self, value):
        self.blacklistWidget.setDisabled(value)
        self.config["disable_blacklist"] = value

    def toggleWorkingDir(self, value):
        self.config["open_in_work_dir"] = value

    def generate_layout(self):
        self.disableWhitelistCheckBox = QCheckBox(self)
        self.disableBlacklistCheckBox = QCheckBox(self)
        self.disableWhitelistCheckBox.toggled.connect(self.toggleWhitelist)
        self.disableBlacklistCheckBox.toggled.connect(self.toggleBlacklist)

        self.whitelistWidget = ListWidget(self, puck_list=self.puck_list["whitelist"])
        self.whitelistWidget.set_not_allowed_list(self.puck_list["blacklist"])
        self.blacklistWidget = ListWidget(self, puck_list=self.puck_list["blacklist"])
        self.blacklistWidget.set_not_allowed_list(self.puck_list["whitelist"])

        self.whitelistWidget.updated_list.connect(
            self.blacklistWidget.set_not_allowed_list
        )
        self.blacklistWidget.updated_list.connect(
            self.whitelistWidget.set_not_allowed_list
        )

        self.disableWhitelistCheckBox.setChecked(
            self.config.get("disable_whitelist", False)
        )
        self.disableBlacklistCheckBox.setChecked(
            self.config.get("disable_blacklist", False)
        )

        self.openInWorkingDirCheckBox = QCheckBox(self)
        self.openInWorkingDirCheckBox.setChecked(
            self.config.get("open_in_work_dir", True)
        )
        self.openInWorkingDirCheckBox.toggled.connect(self.toggleWorkingDir)

        layout = QFormLayout()
        layout.addRow("Open in working dir", self.openInWorkingDirCheckBox)
        layout.addRow("Disable Whitelist", self.disableWhitelistCheckBox)
        layout.addRow("Whitelist", self.whitelistWidget)
        layout.addRow("Disable Blacklist", self.disableBlacklistCheckBox)
        layout.addRow("Blacklist", self.blacklistWidget)
        return layout

    def okClicked(self):
        self.applyClicked()
        self.accept()

    def applyClicked(self):
        self.puck_list["whitelist"] = self.whitelistWidget.puck_list
        self.puck_list["blacklist"] = self.blacklistWidget.puck_list
        list_path = Path(self.config["list_path"])

    def cancelClicked(self):
        self.reject()