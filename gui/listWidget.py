from qtpy.QtWidgets import (
    QLineEdit,
    QListView,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QAbstractItemView,
    QAction,
    QMenu,
)
from qtpy.QtGui import QStandardItemModel, QStandardItem
from qtpy.QtCore import QSortFilterProxyModel, Signal, Qt


class ListWidget(QWidget):
    updated_list = Signal(object)

    def __init__(self, *args, puck_list=None, not_allowed=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_model = QStandardItemModel(self)
        self.list_model.setHorizontalHeaderLabels(["Puck Name"])
        self.list_model.itemChanged.connect(self.check_item)

        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.list_model)

        if not not_allowed:
            not_allowed = []
        self.not_allowed = set(not_allowed)
        if not puck_list:
            puck_list = []
        self.puck_list = puck_list

        for puck_name in self.puck_list:
            item = QStandardItem(puck_name)
            item.setData(
                puck_name, Qt.UserRole
            )  # Setting old name to replace new name if there is a validation error
            self.list_model.appendRow(item)

        self.list_view = QListView(self)
        self.list_view.setModel(self.proxy_model)
        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.open_menu)

        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("Filter pucks...")
        self.search_box.textChanged.connect(self.filter_pucks)

        self.add_button = QPushButton("Add puck", self)
        self.add_button.clicked.connect(self.add_puck)

        vert_layout = QVBoxLayout(self)
        hor_layout = QHBoxLayout(self)

        hor_layout.addWidget(self.search_box)
        hor_layout.addWidget(self.add_button)

        vert_layout.addLayout(hor_layout)
        vert_layout.addWidget(self.list_view)

        self.setLayout(vert_layout)
        self.resetting_name = False

    def open_menu(self, position):
        menu = QMenu(self)
        delete_pucks_action = QAction("Delete selected pucks(s)", self)
        delete_pucks_action.triggered.connect(self.delete_selected)
        menu.addAction(delete_pucks_action)
        menu.exec_(self.list_view.mapToGlobal(position))

    def delete_selected(self):
        indexes = self.list_view.selectedIndexes()
        items_to_remove = []
        for index in indexes:
            items_to_remove.append(self.list_model.item(index.row()))

        for item in items_to_remove:
            index = self.list_model.indexFromItem(item)
            self.list_model.removeRow(index.row())
            self.puck_list.pop(index.row())
            self.updated_list.emit(self.puck_list)

    def filter_pucks(self, a0: str):
        self.proxy_model.setFilterFixedString(a0)

    def add_puck(self, value):
        new_puck = self.search_box.text()
        if new_puck in self.not_allowed:
            self.generate_error_message("Puck name already exists in the other list")
            return
        item = QStandardItem(new_puck)
        self.list_model.appendRow(item)
        self.search_box.clear()
        self.puck_list.append(new_puck)
        self.updated_list.emit(self.puck_list)

    def set_not_allowed_list(self, not_allowed=None):
        if not not_allowed:
            not_allowed = []

        self.not_allowed = set(not_allowed)

    def generate_error_message(self, message):
        error_message = QMessageBox()
        error_message.setWindowTitle("Error")
        error_message.setText(message)
        error_message.exec_()

    def check_item(self, item: QStandardItem):
        new_name = item.data(0)
        old_name = item.data(Qt.UserRole)
        if new_name in self.not_allowed:
            self.generate_error_message("Puck name already exists in the other list")
            self.resetting_name = True
            item.setData(old_name, 0)
            return
        if new_name in set(self.puck_list) and not self.resetting_name:
            self.generate_error_message("Puck name already exists!")
            self.resetting_name = True
            item.setData(old_name, 0)
            return
        item.setData(new_name, Qt.UserRole)
        self.resetting_name = False  # Done resetting name
