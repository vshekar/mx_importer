from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QItemDelegate


class ComboBoxDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.items = []  # Initial items for the combo box

    def setItems(self, items):
        self.items = items

    def createEditor(self, parent, option, index):
        # Create the combo box editor
        editor = QComboBox(parent)
        # Populate the combo box
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        # Set the current value from the model to the combo box
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setCurrentText(value)

    def setModelData(self, editor: QComboBox, model, index):
        # Update the model when the combo box's value changes
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
