from qtpy import QtWidgets
from qtpy.QtGui import QColor
from typing import Tuple
from qtpy.QtCore import Qt
import sys
import pandas as pd
import json
from pandas_model import PandasModel


class ControlMain(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Import Pucks")
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self._createActions()
        self._createMenuBar()

    def _createActions(self):
        self.importExcelAction = QtWidgets.QAction("&Import Excel file", self)
        self.importExcelAction.triggered.connect(self.importExcel)
        self.validateExcelAction = QtWidgets.QAction(
            "&Validate imported Excel file", self
        )
        self.validateExcelAction.triggered.connect(self.validateExcel)
        self.exitAction = QtWidgets.QAction("&Exit", self)

    def importExcel(self):
        filename, _ = QtWidgets.QFileDialog().getOpenFileName(
            self, "Import file", filter="Excel (*.xls *.xlsx)"
        )
        data = pd.read_excel(filename)
        self.model = PandasModel(data)
        self.tableView.setModel(self.model)
        self.validateExcel()

    def validateExcel(self):
        if isinstance(self.model, PandasModel):
            try:
                self.model.preprocessData()
                self.model.validateData()
            except TypeError as e:
                self.msg = QtWidgets.QMessageBox()
                self.msg.setText(str(e))
                self.msg.setModal(True)
                self.msg.setWindowTitle("Error")
                self.msg.show()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QtWidgets.QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.importExcelAction)
        fileMenu.addAction(self.validateExcelAction)
        fileMenu.addAction(self.exitAction)

    def _createTableView(self):
        view = QtWidgets.QTableView()
        view.resize(800, 500)
        view.horizontalHeader().setStretchLastSection(True)
        view.setAlternatingRowColors(True)
        view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        return view


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ex = ControlMain()
    ex.show()
    sys.exit(app.exec_())
