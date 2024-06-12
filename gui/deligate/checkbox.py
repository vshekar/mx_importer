from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QItemDelegate,
    QStyle,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QWidget,
)


class CheckBoxDelegate(QItemDelegate):
    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index
    ) -> QWidget:
        editor = QCheckBox(parent)
        return editor

    def setEditorData(self, editor: QCheckBox, index):
        # Set the current state of the checkbox
        checked = bool(index.model().data(index, Qt.ItemDataRole.EditRole))
        editor.setChecked(checked)

    def setModelData(self, editor: QCheckBox, model, index):
        # Update the model when the checkbox state changes
        model.setData(index, editor.isChecked(), Qt.ItemDataRole.EditRole)

    def paint(self, painter, option, index):
        # Custom painting for the checkbox
        checked = bool(index.model().data(index, Qt.ItemDataRole.DisplayRole))
        if checked:
            checkState = Qt.CheckState.Checked
        else:
            checkState = Qt.CheckState.Unchecked

        self.drawCheck(painter, option, option.rect, checkState)

    def editorEvent(self, event, model, option, index):
        # Ignore any editor events to make the checkbox read-only
        return False

    """
    def paint(self, painter, option, index):
        # Custom painting for the checkbox
        checked = bool(index.model().data(index, Qt.ItemDataRole.DisplayRole))
        checkState = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked

        # Create and configure the checkbox
        checkbox = QStyleOptionButton()
        checkbox.state |= QStyle.State_Enabled
        checkbox.rect = option.rect
        checkbox.state |= (
            QStyle.State_On if checkState == Qt.CheckState.Checked else QStyle.State_Off
        )

        # Draw the checkbox
        QApplication.style().drawControl(QStyle.CE_CheckBox, checkbox, painter)



    def editorEvent(self, event, model, option, index):
        # Handle mouse clicks to change the checkbox state
        if event.type() == QEvent.Type.MouseButtonRelease:
            checked = not bool(index.model().data(index, Qt.ItemDataRole.EditRole))
            text = "X" if checked else ""
            model.setData(index, text, Qt.ItemDataRole.EditRole)
            return True
        return False  
    """
