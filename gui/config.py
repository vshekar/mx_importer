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

    def toggleBlacklist(self, value):
        self.blacklistWidget.setDisabled(value)

    def generate_layout(self):
        self.disableWhitelistCheckBox = QCheckBox(self)
        self.disableBlacklistCheckBox = QCheckBox(self)
        self.disableWhitelistCheckBox.clicked.connect(self.toggleWhitelist)
        self.disableBlacklistCheckBox.clicked.connect(self.toggleBlacklist)

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

        layout = QFormLayout()
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
        with list_path.open('w') as f:
            json.dump(self.puck_list, f, indent=4)
        

    def cancelClicked(self):
        self.reject()
