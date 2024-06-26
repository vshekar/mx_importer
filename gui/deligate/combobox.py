import typing

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QItemDelegate

if typing.TYPE_CHECKING:
    from lix_importer import ControlMain
    from utils.lix_models import LIXHolderPandasModel, LIXPlatePandasModel


class ComboBoxDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.items = []  # Initial items for the combo box

    def setItems(self, items):
        self.items = items

    def createEditor(self, parent, option, index):
        # Create the combo box editor
        editor = QComboBox(parent)
        current_model: "LIXPlatePandasModel | LIXHolderPandasModel" = (
            self.parent().tabView.widget(self.parent().tabView.currentIndex()).model()
        )
        # Populate the combo box
        self.items = [""] + current_model.get_current_samples()
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor: QComboBox, index):
        # Set the current value from the model to the combo box
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setCurrentText(value)

    def setModelData(self, editor: QComboBox, model, index):
        # Update the model when the combo box's value changes
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
