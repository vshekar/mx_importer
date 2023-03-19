from qtpy import QtWidgets
from qtpy.QtGui import QColor
from typing import Tuple
from qtpy.QtCore import Qt
import sys
import pandas as pd
import json
from utils.pandas_model import PandasModel
from utils.db_lib import DBConnection
from utils.devices import Dewar


class ControlMain(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Import Pucks")
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self._createActions()
        self._createMenuBar()
        self.model = None
        # self.dewar = Dewar('XF:lob5lab9-ES:AMX', name='XF:lob5lab9-ES:AMX')

    def _createActions(self):
        self.importExcelAction = QtWidgets.QAction("&Import Excel file", self)
        self.importExcelAction.triggered.connect(self.importExcel)
        self.validateExcelAction = QtWidgets.QAction(
            "&Validate imported Excel file", self
        )
        self.validateExcelAction.triggered.connect(self.validateExcel)
        self.submitPuckDataAction = QtWidgets.QAction("&Submit Puck data", self)
        self.submitPuckDataAction.triggered.connect(self.submitPuckData)
        self.exitAction = QtWidgets.QAction("&Exit", self)
        self.exitAction.triggered.connect(QtWidgets.QApplication.quit)

    def importExcel(self):
        filename, _ = QtWidgets.QFileDialog().getOpenFileName(
            self, "Import file", filter="Excel (*.xls *.xlsx)"
        )
        if filename:
            if filename.endswith('xls'):
                engine = 'xlrd'
            else:
                engine = 'openpyxl'
            data = pd.read_excel(filename, engine=engine)
            self.model = PandasModel(data)
            self.tableView.setModel(self.model)
            self.validateExcel()

    def validateExcel(self):
        if not isinstance(self.model, PandasModel):
            return
        try:
            self.model.preprocessData()
            self.model.validateData()

        except TypeError as e:
            self.msg = QtWidgets.QMessageBox()
            self.msg.setText(str(e))
            self.msg.setModal(True)
            self.msg.setWindowTitle("Error")
            self.msg.show()

    def submitPuckData(self):
        self.currentPucks = set()
        if not self.model.validData:
            return
        dbConnection = DBConnection()
        prevPuckName = None
        puckID = None
        for row in self.model.rows():
            # Check if puck exists, otherwise create one
            if row['puckName'] != prevPuckName:
                puckID = dbConnection.getOrCreateContainer(row['puckName'], 16, "16_pin_puck")
                prevPuckName = row['puckName']

            # Create sample
            sampleName: str = row["sampleName"]
            model = row["model"]
            seq = row["sequence"]
            propNum = row["proposalNum"]
            sampleID = dbConnection.createSample(
                sampleName,
                "pin",
                model=model,
                sequence=seq,
                proposalID=propNum,
            )
            if puckID not in self.currentPucks:
                dbConnection.emptyContainer(puckID)
                self.currentPucks.add(puckID)
            dbConnection.insertIntoContainer(
                puckID, row["position"], sampleID
            )

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QtWidgets.QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.importExcelAction)
        fileMenu.addAction(self.validateExcelAction)
        fileMenu.addAction(self.submitPuckDataAction)
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
