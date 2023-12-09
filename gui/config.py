import json
from pathlib import Path

import pandas as pd
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)

from .listWidget import ListWidget


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

    def toggleEtchedlist(self, value):
        self.etchedlistWidget.setDisabled(value)
        self.config["disable_etchedlist"] = value

    def toggleWorkingDir(self, value):
        self.config["open_in_work_dir"] = value

    def generate_layout(self):
        self.disableWhitelistCheckBox = QCheckBox(self)
        self.disableBlacklistCheckBox = QCheckBox(self)
        self.disableEtchedlistCheckBox = QCheckBox(self)
        self.disableWhitelistCheckBox.toggled.connect(self.toggleWhitelist)
        self.disableBlacklistCheckBox.toggled.connect(self.toggleBlacklist)
        self.disableEtchedlistCheckBox.toggled.connect(self.toggleEtchedlist)

        self.whitelistWidget = ListWidget(self, puck_list=self.puck_list["whitelist"])
        self.whitelistWidget.set_not_allowed_list(self.puck_list["blacklist"])
        self.blacklistWidget = ListWidget(self, puck_list=self.puck_list["blacklist"])
        self.blacklistWidget.set_not_allowed_list(self.puck_list["whitelist"])
        self.etchedlistWidget = ListWidget(self, puck_list=self.puck_list["etched"])
        self.etchedlistWidget.set_not_allowed_list(self.puck_list["blacklist"])

        self.whitelistWidget.updated_list.connect(
            self.blacklistWidget.set_not_allowed_list
        )
        self.blacklistWidget.updated_list.connect(
            self.whitelistWidget.set_not_allowed_list
        )
        self.etchedlistWidget.updated_list.connect(
            self.blacklistWidget.set_not_allowed_list
        )

        self.disableWhitelistCheckBox.setChecked(
            self.config.get("disable_whitelist", False)
        )
        self.disableBlacklistCheckBox.setChecked(
            self.config.get("disable_blacklist", False)
        )
        self.disableEtchedlistCheckBox.setChecked(
            self.config.get("disable_etchedlist", False)
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
        layout.addRow("Disable etched list", self.disableEtchedlistCheckBox)
        layout.addRow("Etched list", self.etchedlistWidget)
        layout.addRow("Disable Blacklist", self.disableBlacklistCheckBox)
        layout.addRow("Blacklist", self.blacklistWidget)
        return layout

    def okClicked(self):
        self.applyClicked()
        self.accept()

    def applyClicked(self):
        self.puck_list["whitelist"] = self.whitelistWidget.puck_list
        self.puck_list["blacklist"] = self.blacklistWidget.puck_list
        self.puck_list["etched"] = self.etchedlistWidget.puck_list
        list_path = Path(self.config["list_path"])
        self.write_to_excel(list_path, self.puck_list)

    def cancelClicked(self):
        self.reject()

    def write_to_excel(self, list_path, puck_list):
        with pd.ExcelWriter(list_path, engine="auto", mode="w") as writer:
            for internal_key, external_key in {
                "etched": "etched",
                "whitelist": "white_list",
                "blacklist": "black_list",
            }.items():
                # Ensure the list is not empty
                if not puck_list[internal_key]:
                    puck_list[internal_key] = [""]  # Placeholder for an empty sheet

                df = pd.DataFrame({external_key: puck_list[internal_key]})
                df.to_excel(writer, sheet_name=external_key, index=False, header=False)
