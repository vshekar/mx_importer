from qtpy import QtWidgets
from qtpy.QtGui import QColor, QIcon
from typing import Tuple
from qtpy.QtCore import Qt, QSize
import sys
import pandas as pd
import numpy as np
import json
from utils.pandas_model import PuckPandasModel, DewarPandasModel
from utils.db_lib import DBConnection
from gui.config import ConfigurationWindow
from pathlib import Path
import grp, os
import yaml
from gui.custom_table import TableWithCopy, DewarTableWithCopy
import time


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
        self.resize(QtWidgets.QDesktopWidget().availableGeometry().size() * 0.7)  # type: ignore
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

        self.beginDewarScanAction = QtWidgets.QAction("&Begin Dewar Scan", self)
        self.beginDewarScanAction.triggered.connect(self.setupDewarScan)

    def setupDewarScan(self):
        empty_frame = {None: [""]}
        data = pd.DataFrame.from_dict(empty_frame)
        self.model = DewarPandasModel(data, parent=self)
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self.tableView.setModel(self.model)
        self.tableView.resizeColumnsToContents()
        next_index = self.model.index(0, 0)
        self.tableView.setCurrentIndex(next_index)

    def saveExcel(self):
        filepath, _ = QtWidgets.QFileDialog().getSaveFileName(self, "Save file")
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
            required_columns_list = [
                "puckname",
                "position",
                "samplename",
                "model",
                "sequence",
                "proposalnum",
            ]
            required_columns = set(required_columns_list)
            header_correct = required_columns.issubset(
                (col.strip().lower() for col in data.columns if isinstance(col, str))
            )
            if not rows.all() and not header_correct:
                import_offset = data.loc[rows].first_valid_index()
                if isinstance(import_offset, (int, np.integer)):
                    data = pd.read_excel(
                        filename, engine=engine, skiprows=import_offset + 1
                    )
            data.rename(
                columns={
                    col: col.strip().lower()
                    for col in data.columns
                    if isinstance(col, str)
                },
                inplace=True,
            )
            self.model = PuckPandasModel(data)
            self.model.setPuckLists(self.pucklists)
            self.validateExcel()
            self.tableView.setModel(self.model)
            self.tableView.resizeColumnsToContents()

    def validateExcel(self):
        if not isinstance(self.model, PuckPandasModel):
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
        try:
            if isinstance(self.model, PuckPandasModel):
                self.model.preprocessData()
                self.model.validateData(self.config)
        except Exception as e:
            self.showModalMessage(
                "Error", f"Data not validated, will not upload.\nException: {e}"
            )
            return

        if isinstance(self.model, PuckPandasModel):
            beamline_id = self.config.get("beamline", "99id1").lower()
            dbConnection = DBConnection(
                beamline_id=beamline_id,
                host=self.config.get(
                    "database_host", os.environ.get("MONGODB_HOST", "localhost")
                ),
            )
            self.progress_dialog = QtWidgets.QProgressDialog(
                "Uploading Puck data...",
                "Cancel",
                0,
                self.model.rowCount(),
                self,
            )
            # self.progress_dialog.setModal(True)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            prevPuckName = None
            puck_id = None
            self.currentPucks = set()
            self.progress_dialog.show()
            self.progress_dialog.setValue(0)
            time.sleep(
                0.25
            )  # Dumb sleep because progress dialog doesn't initialize fast enough
            for i, row in enumerate(self.model.rows()):
                print(f"Processing row {i}")
                self.progress_dialog.setValue(i + 1)
                if self.progress_dialog.wasCanceled():
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
        else:
            self.showModalMessage("Error", "Invalid data, will not upload to database")

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QtWidgets.QMenu("&File", self)
        dataMenu = QtWidgets.QMenu("&Data", self)
        dewarScanMenu = QtWidgets.QMenu("&Dewar", self)
        menuBar.addMenu(fileMenu)
        menuBar.addMenu(dataMenu)
        fileMenu.addAction(self.importExcelAction)
        fileMenu.addAction(self.saveExcelAction)
        fileMenu.addAction(self.exitAction)

        dataMenu.addAction(self.validateExcelAction)
        dataMenu.addAction(self.submitPuckDataAction)
        if self.config["admin_group"] in [
            grp.getgrgid(g).gr_name for g in os.getgroups()
        ]:
            dataMenu.addAction(self.configWindowAction)
            menuBar.addMenu(dewarScanMenu)
            dewarScanMenu.addAction(self.beginDewarScanAction)

    def _createTableView(self, dewar=False):
        # view = QtWidgets.QTableView()
        if dewar:
            view = DewarTableWithCopy()
        else:
            view = TableWithCopy()
        view.resize(1200, 1200)
        view.horizontalHeader().setStretchLastSection(True)
        view.setAlternatingRowColors(True)
        view.setSelectionMode(QtWidgets.QTableView.SelectionMode.ExtendedSelection)
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
    app.setWindowIcon(QIcon(str(Path.cwd() / Path("gui/assets/icon.png"))))
    ex = ControlMain(config_path=config_path)
    ex.show()
    sys.exit(app.exec_())
