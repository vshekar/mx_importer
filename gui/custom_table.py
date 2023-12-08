import typing

import numpy as np
from PyQt5 import QtCore, QtGui
from qtpy.QtCore import QAbstractItemModel, QModelIndex, Qt
from qtpy.QtWidgets import QApplication, QMessageBox, QTableView


class TableWithCopy(QTableView):
    """
    this class extends QTableWidget
    * supports copying multiple cell's text onto the clipboard
    * formatted specifically to work with multiple-cell paste into programs
      like google sheets, excel, or numbers
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setModel(self, model: QAbstractItemModel) -> None:
        super().setModel(model)
        model.dataChanged.connect(self.resizeColumnsToContents)

    def rowCount(self):
        return self.model().rowCount()

    def columnCount(self):
        return self.model().columnCount()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key.Key_C and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            copied_cells = sorted(self.selectedIndexes())

            copy_text = ""
            max_column = copied_cells[-1].column()
            for c in copied_cells:
                # copy_text += self.model().item(c.row(), c.column()).text()
                copy_text += self.model().itemData(c)[0]
                if c.column() == max_column:
                    copy_text += "\n"
                else:
                    copy_text += "\t"

            QApplication.clipboard().setText(copy_text)

        if event.key() == Qt.Key.Key_V and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            destination_cells = sorted(self.selectedIndexes())
            rows = QApplication.clipboard().text().split("\n")
            if len(rows) > 1:
                rows = rows[:-1]
            else:
                rows = rows
            for i, row in enumerate(rows):
                rows[i] = row.split("\t")  # type: ignore

            num_cols = len(rows[0])

            if len(rows) == 0:
                return

            if len(rows) == 1 and num_cols == 1:
                for d in destination_cells:
                    self.model().setData(d, rows[0], role=Qt.ItemDataRole.EditRole)
                return

            selected_rows = destination_cells[-1].row() - destination_cells[0].row() + 1
            selected_cols = (
                destination_cells[-1].column() - destination_cells[0].column() + 1
            )
            if len(rows) != selected_rows or num_cols != selected_cols:
                QMessageBox.information(
                    self,
                    "Error",
                    f"Mismatch: Copied data has {len(rows)} rows and {num_cols} columns."
                    f"Trying to paste to {destination_cells[-1].row()} rows and {destination_cells[-1].column()} columns",
                )
                return

            for d in destination_cells:
                self.model().setData(
                    d,
                    rows[d.row() - destination_cells[0].row()][
                        d.column() - destination_cells[0].column()
                    ],
                    role=Qt.ItemDataRole.EditRole,
                )


class DewarTableWithCopy(TableWithCopy):
    pass
