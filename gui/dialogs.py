from qtpy import QtWidgets
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QIcon


class ConfirmDialog(QtWidgets.QDialog):
    def __init__(self, title, message, path_options, parent=None):
        super().__init__(parent)

        # Set the dialog title
        self.setWindowTitle(title)

        # Create layout and add widgets
        layout = QtWidgets.QVBoxLayout(self)

        # Add a label for the message
        label = QtWidgets.QLabel(message)
        layout.addWidget(label)

        self.combo_box = QtWidgets.QComboBox()
        self.combo_box.addItems(path_options)
        layout.addWidget(self.combo_box)

        # Create Confirm and Cancel buttons
        self.confirmButton = QtWidgets.QPushButton("Confirm", self)
        self.cancelButton = QtWidgets.QPushButton("Cancel", self)

        # Connect buttons to dialog slots
        self.confirmButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        # Add buttons to the layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.confirmButton)
        button_layout.addWidget(self.cancelButton)
        layout.addLayout(button_layout)

    def showDialog(self):
        result = self.exec_()
        return result, self.combo_box.currentText()
