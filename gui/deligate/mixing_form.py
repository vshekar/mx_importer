import typing

import numpy as np
from PyQt5.QtCore import QObject
from qtpy.QtCore import Qt
from qtpy.QtGui import QIntValidator
from qtpy.QtWidgets import (
    QDialog,
    QGridLayout,
    QItemDelegate,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
)

if typing.TYPE_CHECKING:
    from lix_importer import ControlMain
    from utils.lix_models import LIXPlatePandasModel


class MixingVolumeEditDialog(QDialog):
    def __init__(self, parent=None, max_volumes={}):
        """
        Widget to specify the volumes to be mixed. Pass max_volumes dict to specify
        how much more you can add
        """
        super().__init__(parent)
        self.setLayout(QGridLayout(self))
        self.max_volumes = max_volumes

        self.line_edits: "dict[str, QLineEdit]" = {}
        for i, (row, max_vol) in enumerate(self.max_volumes.items()):
            if not np.isnan(max_vol):
                line_edit = QLineEdit("0")
                line_edit.setValidator(QIntValidator(0, int(max_vol), self))
                self.line_edits[row] = line_edit

                self.layout().addWidget(QLabel(f"{row} (Max vol {max_vol})"), i, 0)
                self.layout().addWidget(self.line_edits[row], i, 1)

        self.button = QPushButton("Submit", self)
        self.layout().addWidget(self.button)
        self.button.clicked.connect(self.validate_and_submit)

    def validate_and_submit(self):
        """
        Validation rules after submitting
        """
        errorMessage = ""
        isValid = True
        for row, max_vol in self.max_volumes.items():
            line_edit = self.line_edits[row]
            value = line_edit.text()
            max_vol = self.max_volumes.get(row, 50)

            # Reset style to clear previous error states
            line_edit.setStyleSheet("")

            if not value.isdigit() or not (0 <= int(value) <= max_vol):
                isValid = False
                errorMessage += f"{row} value must be between 0 and {max_vol}.\n"
                # Highlight the line_edit with an error
                line_edit.setStyleSheet("border: 1px solid red;")

        if not isValid:
            QMessageBox.warning(self, "Input Validation Error", errorMessage)
        else:
            self.accept()

    def setText(self, text):
        for token in text.split(","):
            if len(token.split(":")) == 2:
                row, amount = token.strip().split(":")
                if row in self.line_edits:
                    self.line_edits[row].setText(amount)

    def getText(self):
        output = []
        for row, line_edit in self.line_edits.items():
            if int(line_edit.text()) != 0:
                output.append(f"{row}:{line_edit.text()}")
        return ",".join(output)


class MixingDelegate(QItemDelegate):
    def __init__(self, parent) -> None:
        self.main_app = parent
        super().__init__(parent)

    def createEditor(self, parent, option, index):

        current_model: "LIXPlatePandasModel" = (
            self.parent().tabView.widget(self.parent().tabView.currentIndex()).model()
        )
        max_volumes = current_model.get_mixing_data(index)
        dialog = MixingVolumeEditDialog(parent, max_volumes)
        dialog.setText(index.model().data(index, Qt.ItemDataRole.EditRole))

        if dialog.exec_():
            newValue = dialog.getText()
            index.model().setData(index, newValue, Qt.ItemDataRole.EditRole)

        return None  # No in-place editor, so return None

    def parent(self) -> "ControlMain":
        return super().parent()
