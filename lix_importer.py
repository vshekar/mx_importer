import getpass
import grp
import json
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import yaml
from qtpy import QtWidgets
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QIcon

from gui.config import ConfigurationWindow
from gui.custom_table import DewarTableWithCopy, TableWithCopy
from utils.db_lib import DBConnection
from utils.pandas_model import DewarPandasModel, PuckPandasModel
from utils.lix_models import LIXPlatePandasModel


class Mode(Enum):
    MANUAL = "Manual"
    AUTOMATED = "Automated"


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
        self.setWindowTitle(f"Import sample information @ LIX")
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self._createActions()
        self._createMenuBar()
        self.model = None
        self.mode = Mode.MANUAL
        self.resize(QtWidgets.QDesktopWidget().availableGeometry().size() * 0.7)  # type: ignore
        self.status_bar = self.statusBar()
        self.mode_status = QtWidgets.QLabel(f"MODE: {self.mode.value}")
        self.status_bar.addPermanentWidget(self.mode_status)
        # Default mode to start the application
        self._set_mode(Mode.MANUAL)

    def _createActions(self):
        # File menu actions
        self.saveExcelAction = QtWidgets.QAction("&Save table as Excel file", self)
        self.saveExcelAction.triggered.connect(self.saveExcel)
        self.exitAction = QtWidgets.QAction("&Exit", self)
        self.exitAction.triggered.connect(QtWidgets.QApplication.quit)

        # Puck menu actions
        self.importExcelAction = QtWidgets.QAction("&Import Plate spreadsheet file", self)
        self.importExcelAction.triggered.connect(lambda: self.importExcel("plate"))
        self.importHolderExcelAction = QtWidgets.QAction("&Import holder spreadsheet file", self)
        self.importHolderExcelAction.triggered.connect(lambda: self.importExcel("holder"))
        self.validateExcelAction = QtWidgets.QAction(
            "&Validate imported Excel file", self
        )
        self.validateExcelAction.triggered.connect(self.validateExcel)
        self.submitPuckDataAction = QtWidgets.QAction("&Submit Puck data", self)
        self.submitPuckDataAction.triggered.connect(self.submitPuckData)
        self.configWindowAction = QtWidgets.QAction("&Configuration", self)
        self.configWindowAction.triggered.connect(self.openConfigWindow)

    def _set_mode(self, mode):
        self.mode = mode
        self.mode_status.setText(f"MODE: {self.mode.value}")

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

    def importExcel(self, excel_type: str):
        dialog = QtWidgets.QFileDialog()
        if self.config.get("open_in_work_dir", True):
            dialog.setDirectory(os.getcwd())
        filename, _ = dialog.getOpenFileName(
            self, "Import file", filter="Excel (*.xls *.xlsx)"
        )
        if filename:
            excel_file = pd.ExcelFile(filename)
            for sheet_name in excel_file.sheet_names:
                data: "pd.DataFrame" = excel_file.parse(sheet_name)
                if data.empty:
                    continue
                # Check if any row besides header row contains "puckname"
                rows = (data.applymap(lambda x: str(x).lower() == "puckname")).any(
                    axis=1
                )

                self.model = LIXPlatePandasModel(data)
                self.validateExcel()
                self.tableView.setModel(self.model)
                break
            self.tableView.resizeColumnsToContents()

    def validateExcel(self):
        if not isinstance(self.model, LIXPlatePandasModel):
            return
        try:
            # self.model.preprocessData()
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
                owner=self.owner,
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
        dataMenu = QtWidgets.QMenu("&Puck Import", self)
        dewarScanMenu = QtWidgets.QMenu("&Shipping Dewar", self)
        menuBar.addMenu(fileMenu)
        menuBar.addMenu(dataMenu)
        fileMenu.addActions([self.saveExcelAction, self.exitAction])

        dataMenu.addActions(
            [
                self.importExcelAction,
                self.validateExcelAction,
                self.submitPuckDataAction,
            ]
        )

        if self.config["admin_group"] in [
            grp.getgrgid(g).gr_name for g in os.getgroups()
        ]:
            dataMenu.addAction(self.configWindowAction)
            menuBar.addMenu(dewarScanMenu)

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
            config=self.config, puck_list={"whitelist": [], "blacklist": []}
        )
        self.config = self.configWindow.config
        with self.config_path.open("w") as f:
            yaml.safe_dump(self.config, f)


def start_app(config_path):
    print("Starting LIX")
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path.cwd() / Path("gui/assets/icon.png"))))
    ex = ControlMain(config_path=config_path)
    ex.show()
    sys.exit(app.exec_())
