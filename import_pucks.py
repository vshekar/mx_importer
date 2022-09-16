from qtpy import QtWidgets
from qtpy.QtGui import QColor
from typing import Tuple
from qtpy.QtCore import Qt
import sys
import pandas as pd
import json
from pandas_model import PandasModel
from db_lib import DBConnection


class ControlMain(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Import Pucks")
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self._createActions()
        self._createMenuBar()
        self.owner = "vshekar1"

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

    def importExcel(self):
        filename, _ = QtWidgets.QFileDialog().getOpenFileName(
            self, "Import file", filter="Excel (*.xls *.xlsx)"
        )
        data = pd.read_excel(filename)
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
        for row in self.model.rows():
            # Check if puck exists, otherwise create one
            puckData = dbConnection.getContainerbyName(row["puckName"], self.owner)
            puckID = puckData["uid"] if "uid" in puckData else ""
            if not puckID:
                puckID = dbConnection.createContainer(
                    row["puckName"], 16, self.owner, "16_pin_puck"
                )

            # Create sample
            sampleName: str = row["sampleName"]
            model = row["model"]
            seq = row["sequence"]
            propNum = row["proposalNum"]
            sampleID = dbConnection.createSample(
                sampleName,
                self.owner,
                "pin",
                model=model,
                sequence=seq,
                proposalID=propNum,
            )
            if puckID not in self.currentPucks:
                dbConnection.emptyContainer(puckID)
                self.currentPucks.add(puckID)
            dbConnection.insertIntoContainer(
                puckID, self.owner, row["position"], sampleID
            )

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
