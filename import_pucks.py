from qtpy import QtWidgets
from qtpy.QtGui import QColor
from typing import Tuple
from qtpy.QtCore import Qt
import sys
import pandas as pd
import json
from utils.pandas_model import PandasModel
from utils.db_lib import DBConnection
from gui.config import ConfigurationWindow
from pathlib import Path
import grp, os
import yaml
from gui.custom_table import TableWithCopy


class ControlMain(QtWidgets.QMainWindow):
    def __init__(self, *args, config_path, **kwargs):
        self.config_path = config_path
        try:
            with self.config_path.open("r") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(
                f"Exception occured while reading config file {self.config_path}: {e}"
            )
            raise e
        self.config = config
        super().__init__(*args, **kwargs)
        self.setWindowTitle(f"Import Pucks at {self.config.get('beamline', '99id1')}")
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self._createActions()
        self._createMenuBar()
        self.model = None
        self.resize(QtWidgets.QDesktopWidget().availableGeometry().size() * 0.7)
        self.validatePuckLists()

    def validatePuckLists(self):
        pucklist_path = Path(self.config["list_path"])
        if not pucklist_path.exists():
            self.showModalMessage(
                "Error",
                f"Puck list file {pucklist_path} not found. White list and black list are empty",
            )
            self.pucklists = {"blacklist": [], "whitelist": []}
        else:
            with pucklist_path.open("r") as f:
                self.pucklists = json.load(f)
                for label in ["whitelist", "blacklist"]:
                    if label not in self.pucklists.keys():
                        self.pucklists[label] = []

    def _createActions(self):
        self.importExcelAction = QtWidgets.QAction("&Import Excel file", self)
        self.importExcelAction.triggered.connect(self.importExcel)
        self.saveExcelAction = QtWidgets.QAction("&Save table as Excel file", self)
        self.saveExcelAction.triggered.connect(self.saveExcel)

        self.validateExcelAction = QtWidgets.QAction(
            "&Validate imported Excel file", self
        )
        self.validateExcelAction.triggered.connect(self.validateExcel)
        self.submitPuckDataAction = QtWidgets.QAction("&Submit Puck data", self)
        self.submitPuckDataAction.triggered.connect(self.submitPuckData)
        self.exitAction = QtWidgets.QAction("&Exit", self)
        self.exitAction.triggered.connect(QtWidgets.QApplication.quit)
        self.configWindowAction = QtWidgets.QAction("&Configuration", self)
        self.configWindowAction.triggered.connect(self.openConfigWindow)

    def saveExcel(self):
        filepath, _ = QtWidgets.QFileDialog().getSaveFileName(
            self, "Save file", filter="Excel (*.xls, *.xlsx)"
        )
        if filepath:
            filepath = Path(filepath)
            if not filepath.suffix:
                filepath = filepath.parent / (filepath.name + ".xlsx")
            engine = "openpyxl"
            if filepath.suffix == "xls":
                engine = "xlrd"

            if self.model:
                self.model._dataframe.to_excel(filepath, engine=engine, index=False)

    def importExcel(self):
        filename, _ = QtWidgets.QFileDialog().getOpenFileName(
            self, "Import file", filter="Excel (*.xls *.xlsx)"
        )
        if filename:
            if filename.endswith("xls"):
                engine = "xlrd"
            else:
                engine = "openpyxl"
            data = pd.read_excel(filename, engine=engine)
            # Check if any row besides header row contains "puckname"
            rows = (data.applymap(lambda x: str(x).lower() == "puckname")).any(axis=1)
            required_columns = set(
                [
                    "puckname",
                    "samplename",
                    "proposalnum",
                    "position",
                    "model",
                    "sequence",
                ]
            )
            header_correct = required_columns.issubset(
                (col.lower() for col in data.columns)
            )
            if not rows.all() and not header_correct:
                import_offset = data.loc[rows].first_valid_index()
                data = pd.read_excel(
                    filename, engine=engine, skiprows=import_offset + 1
                )
            self.model = PandasModel(data)
            self.model.setPuckLists(self.pucklists)
            self.tableView.setModel(self.model)
            self.tableView.resizeColumnsToContents()
            self.validateExcel()

    def validateExcel(self):
        if not isinstance(self.model, PandasModel):
            return
        try:
            self.model.preprocessData()
            self.model.validateData(self.config)
            self.showModalMessage("Success", "Validated excel sucessfully")

        except TypeError as e:
            self.showModalMessage("Error", e)

    def showModalMessage(self, title, message):
        self.msg = QtWidgets.QMessageBox()
        self.msg.setText(str(message))
        self.msg.setModal(True)
        self.msg.setWindowTitle(title)
        self.msg.show()

    def submitPuckData(self):
        self.currentPucks = set()
        if not self.model.validData:
            return

        beamline_id = self.config.get("beamline", "99id1").lower()
        dbConnection = DBConnection(beamline_id=beamline_id)
        progress_dialog = QtWidgets.QProgressDialog(
            "Uploading Puck data...",
            "Cancel",
            0,
            self.model.rowCount(),
            self,
        )
        progress_dialog.setModal(True)
        prevPuckName = None
        puck_id = None
        for i, row in enumerate(self.model.rows()):
            progress_dialog.setValue(i + 1)
            if progress_dialog.wasCanceled():
                break
            # Check if puck exists, otherwise create one
            if row["puckname"] != prevPuckName:
                puck_id = dbConnection.getOrCreateContainerID(
                    row["puckname"], 16, "16_pin_puck"
                )
                prevPuckName = row["puckname"]

            # Create sample
            sampleName: str = row["samplename"]
            model = row["model"]
            seq = row["sequence"]
            propNum = row["proposalnum"]
            sampleID = dbConnection.createSample(
                str(sampleName),
                "pin",
                model=None if pd.isna(model) else str(model),
                sequence=None if pd.isna(seq) else str(seq),
                proposalID=propNum,
                container=puck_id,
            )
            if puck_id not in self.currentPucks:
                dbConnection.emptyContainer(puck_id)
                self.currentPucks.add(puck_id)
            dbConnection.insertIntoContainer(
                puck_id, int(row["position"]) - 1, sampleID
            )

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QtWidgets.QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.importExcelAction)
        fileMenu.addAction(self.saveExcelAction)
        fileMenu.addAction(self.validateExcelAction)
        fileMenu.addAction(self.submitPuckDataAction)
        if self.config["admin_group"] in [
            grp.getgrgid(g).gr_name for g in os.getgroups()
        ]:
            fileMenu.addAction(self.configWindowAction)
        fileMenu.addAction(self.exitAction)

    def _createTableView(self):
        # view = QtWidgets.QTableView()
        view = TableWithCopy()
        view.resize(1200, 1200)
        view.horizontalHeader().setStretchLastSection(True)
        view.setAlternatingRowColors(True)
        view.setSelectionMode(QtWidgets.QTableView.ExtendedSelection)
        return view

    def openConfigWindow(self):
        self.configWindow = ConfigurationWindow(
            config=self.config, puck_list=self.pucklists
        )
        self.config = self.configWindow.config
        with self.config_path.open("w") as f:
            yaml.safe_dump(self.config, f)


def start_app(config_path):
    app = QtWidgets.QApplication(sys.argv)
    ex = ControlMain(config_path=config_path)
    ex.show()
    sys.exit(app.exec_())
