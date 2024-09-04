import os
import sys
from pathlib import Path

import requests
from lixtools.mailin import make_barcode
from qtpy.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ManageHoldersDialog(QDialog):
    def __init__(self, tab_widget):
        super().__init__()
        self.tab_widget = tab_widget
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Manage holders")

        # Create the list widget
        self.list_widget = QListWidget()

        self.list_widget.addItems(
            [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        )

        # Input field to add/edit items
        self.item_input = QLineEdit(self)
        self.item_input.setPlaceholderText("Enter item text")

        # Buttons for add, remove, edit, move up, and move down actions
        add_button = QPushButton("Add", self)
        add_button.clicked.connect(self.add_item)

        remove_button = QPushButton("Remove", self)
        remove_button.clicked.connect(self.remove_item)

        edit_button = QPushButton("Edit", self)
        edit_button.clicked.connect(self.edit_item)

        move_up_button = QPushButton("Move Up", self)
        move_up_button.clicked.connect(self.move_item_up)

        move_down_button = QPushButton("Move Down", self)
        move_down_button.clicked.connect(self.move_item_down)

        # Layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(move_up_button)
        button_layout.addWidget(move_down_button)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.item_input)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def add_item(self):
        text = self.item_input.text()
        if text:
            # Add item to the list
            self.list_widget.addItem(text)

            # Add a new tab with the same text
            # new_tab = QWidget()
            # self.tab_widget.addTab(new_tab, text)
            ex = self.tab_widget.parent()
            spreadsheet_file = "holder_spreadsheet_default.xlsx"
            spreadsheet_path = Path(sys.argv[0]).resolve().parent / Path(
                spreadsheet_file
            )
            ex.parseHolderExcel(str(spreadsheet_path), holder_name=text)

            self.item_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Item text cannot be empty")

    def edit_item(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an item to edit")
            return
        item = selected_items[0]
        new_text = self.item_input.text()
        if new_text:
            # Update the text in the list widget
            row = self.list_widget.row(item)
            item.setText(new_text)

            # Update the corresponding tab's title
            self.tab_widget.setTabText(row, new_text)

            self.item_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Item text cannot be empty")

    def remove_item(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an item to remove")
            return
        for item in selected_items:
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

            # Remove the corresponding tab
            self.tab_widget.removeTab(row)

    def move_item_up(self):
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            current_item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, current_item)
            self.list_widget.setCurrentItem(current_item)

            # Move the corresponding tab up
            current_tab = self.tab_widget.widget(current_row)
            self.tab_widget.removeTab(current_row)
            self.tab_widget.insertTab(current_row - 1, current_tab, current_item.text())
            self.tab_widget.setCurrentIndex(current_row - 1)

    def move_item_down(self):
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            current_item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, current_item)
            self.list_widget.setCurrentItem(current_item)

            # Move the corresponding tab down
            current_tab = self.tab_widget.widget(current_row)
            self.tab_widget.removeTab(current_row)
            self.tab_widget.insertTab(current_row + 1, current_tab, current_item.text())
            self.tab_widget.setCurrentIndex(current_row + 1)

    def get_list(self):
        return [
            self.list_widget.item(i).text() for i in range(self.list_widget.count())
        ]


class AddHolderDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Add Holder")
        self.text_input = QLineEdit(self)

        self.ok_button = QPushButton("OK", self)
        self.cancel_button = QPushButton("Cancel", self)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.text_input)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_text(self):
        return self.text_input.text()


class GenerateHolderQRCodeDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Generate holder QR code")

        # Proposal ID input
        self.proposal_id_label = QLabel("Proposal ID:")
        self.proposal_id_input = QLineEdit(self)
        self.proposal_id_input.setMaxLength(6)

        # SAF ID input
        self.saf_id_label = QLabel("SAF ID:")
        self.saf_id_input = QLineEdit(self)
        self.saf_id_input.setMaxLength(6)

        # Plate ID
        self.plate_id_label = QLabel("Plate ID:")
        self.plate_id_input = QLineEdit(self)
        self.plate_id_input.setMaxLength(2)

        self.ok_button = QPushButton("OK", self)
        self.cancel_button = QPushButton("Cancel", self)

        self.ok_button.clicked.connect(self.validate_inputs)
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.proposal_id_label)
        layout.addWidget(self.proposal_id_input)
        layout.addWidget(self.saf_id_label)
        layout.addWidget(self.saf_id_input)
        layout.addWidget(self.plate_id_label)
        layout.addWidget(self.plate_id_input)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def validate_inputs(self):
        proposal_id = self.proposal_id_input.text()
        saf_id = self.saf_id_input.text()
        plate_id = self.plate_id_input.text()

        if (
            len(proposal_id) == 6
            and len(saf_id) == 6
            and proposal_id.isdigit()
            and saf_id.isdigit()
            and self.validate_saf(proposal_id, saf_id)
        ):
            dialog = QFileDialog()
            # if self.config.get("open_in_work_dir", True):
            dialog.setDirectory(os.getcwd())
            # filename, _ = dialog.getSaveFileName(self, "QR Code")
            filename = dialog.getExistingDirectory(self, "QR Code")
            if filename:
                make_barcode(proposal_id, saf_id, plate_id, path=filename)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Both Proposal ID and SAF ID must be exactly 6 digits.",
            )

    def validate_saf(self, proposal_id, saf_id):
        try:
            resp = requests.get(f"https://api.nsls2.bnl.gov/v1/proposal/{proposal_id}")
            resp.raise_for_status()
            print(resp.json())
            for saf in resp.json()["proposal"]["safs"]:
                if (
                    saf["saf_id"] == str(saf_id)
                    and saf["status"] == "APPROVED"
                    and "LIX" in saf["instruments"]
                ):
                    return True
        except Exception as e:
            print(e)
            return False
        return False

    def get_inputs(self):
        return self.proposal_id_input.text(), self.saf_id_input.text()
