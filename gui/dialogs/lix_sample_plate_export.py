from PyQt5.QtGui import QRegExpValidator
from qtpy.QtCore import QRegExp, Qt
from qtpy.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LixSamplePlateExportDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QGridLayout()

        proposal_id_label = QLabel("Proposal ID")
        self.proposal_line_edit = QLineEdit()
        reg_ex = QRegExp("^[0-9]{6}$")
        proposal_validator = QRegExpValidator(reg_ex)
        self.proposal_line_edit.setValidator(proposal_validator)
        layout.addWidget(proposal_id_label, 0, 0)
        layout.addWidget(self.proposal_line_edit, 0, 1)

        saf_id_label = QLabel("SAF ID")
        self.saf_id_edit = QLineEdit()
        saf_id_validator = QRegExpValidator(reg_ex)
        self.saf_id_edit.setValidator(saf_id_validator)
        layout.addWidget(saf_id_label, 1, 0)
        layout.addWidget(self.saf_id_edit, 1, 1)

        plate_id_label = QLabel("Plate ID")
        self.plate_id_edit = QLineEdit()
        plate_id_reg_ex = QRegExp("^[a-zA-Z0-9]{2}$")
        plate_id_validator = QRegExpValidator(plate_id_reg_ex)
        self.plate_id_edit.setValidator(plate_id_validator)
        layout.addWidget(plate_id_label, 2, 0)
        layout.addWidget(self.plate_id_edit, 2, 1)

        # OK and Cancel buttons
        btn_layout = QVBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout, 3, 1, 1, 2)

        # Connect button signals to their respective slots
        self.ok_button.clicked.connect(self.on_ok)
        self.cancel_button.clicked.connect(self.reject)

        self.setLayout(layout)

    def on_ok(self):
        # Validate inputs
        if self.validate_inputs():
            self.accept()  # Close the dialog and set the result to Accepted
        else:
            # Show some error message or simply ignore
            print("Validation failed, please check your inputs.")

    def validate_inputs(self):
        # Check if all line edits are valid
        return (
            self.proposal_line_edit.hasAcceptableInput()
            and self.saf_id_edit.hasAcceptableInput()
            and self.plate_id_edit.hasAcceptableInput()
        )

    def get_values(self):
        return (
            self.proposal_line_edit.text(),
            self.saf_id_edit.text(),
            self.plate_id_edit.text(),
        )
