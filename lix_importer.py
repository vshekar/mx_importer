import getpass
import grp
import json
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import yaml
from qtpy import QtWidgets
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor, QIcon

from gui.config import ConfigurationWindow
from gui.custom_table import LIXHolderTableWithCopy, LIXTableWithCopy
from gui.deligate import CheckBoxDelegate, ComboBoxDelegate, MixingDelegate
from gui.dialogs.lix_sample_plate_export import LixSamplePlateExportDialog
from utils.db_lib import DBConnection
from utils.lix_models import (
    LIXHolderPandasModel,
    LIXPlatePandasModel,
    make_plate_QR_code,
    write_excel,
)
from utils.pandas_model import DewarPandasModel, PuckPandasModel


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
        self.tabView = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabView)
        self._createActions()
        self._createMenuBar()
        self.model = None
        self.mode = Mode.MANUAL
        self.resize(QtWidgets.QDesktopWidget().availableGeometry().size() * 0.7)  # type: ignore
        self.status_bar = self.statusBar()
        self.mode_status = QtWidgets.QLabel(f"MODE: {self.mode.value}")
        self.status_bar.addPermanentWidget(self.mode_status)
        self.well_names = "ABCDEFGH"
        # Default mode to start the application
        self._set_mode(Mode.MANUAL)

    def _createActions(self):
        # File menu actions
        self.saveExcelAction = QtWidgets.QAction("&Save table as Excel file", self)
        self.saveExcelAction.triggered.connect(self.saveExcel)
        self.newPlateAction = QtWidgets.QAction("&Create new plate", self)
        self.newPlateAction.triggered.connect(self.createNewPlate)
        self.newHolderAction = QtWidgets.QAction("&Create new holder", self)
        self.newHolderAction.triggered.connect(self.createNewHolder)
        self.exitAction = QtWidgets.QAction("&Exit", self)
        self.exitAction.triggered.connect(QtWidgets.QApplication.quit)

        # Puck menu actions
        self.importExcelAction = QtWidgets.QAction(
            "&Import Plate spreadsheet file", self
        )
        self.importExcelAction.triggered.connect(lambda: self.importExcel("plate"))
        self.importHolderExcelAction = QtWidgets.QAction(
            "&Import holder spreadsheet file", self
        )
        self.importHolderExcelAction.triggered.connect(
            lambda: self.importExcel("holder")
        )
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

    def createNewPlate(self):
        spreadsheet_path = Path(sys.argv[0]).resolve().parent / Path(
            "plate_spreadsheet_default.xlsx"
        )
        self.parseExcel(str(spreadsheet_path))

    def createNewHolder(self):
        spreadsheet_path = Path(sys.argv[0]).resolve().parent / Path(
            "holder_spreadsheet_default.xlsx"
        )
        self.parseHolderExcel(str(spreadsheet_path))

    def saveExcel(self):
        dialog = LixSamplePlateExportDialog()
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            proposal_id, saf_id, plate_id = dialog.get_values()
            print(f"Proposal ID: {proposal_id}, SAF ID: {saf_id}, Plate ID: {plate_id}")
            self.generateExcel(proposal_id, saf_id, plate_id)
        else:
            print("Dialog canceled.")

    def generateExcel(self, proposal_id, saf_id, plate_id):
        filepath, _ = QtWidgets.QFileDialog().getSaveFileName(self, "Save file")
        if filepath:
            filepath = Path(filepath)
            if not filepath.suffix:
                filepath = filepath.parent / (filepath.name + ".xlsx")

            sheet_name, barcode_path = make_plate_QR_code(
                proposal_id, saf_id, plate_id, filepath.parent
            )

            if self._dataframe is not None:
                write_excel(self._dataframe, filepath, sheet_name, barcode_path)

    def importExcel(self, excel_type: str):
        dialog = QtWidgets.QFileDialog()
        if self.config.get("open_in_work_dir", True):
            dialog.setDirectory(os.getcwd())
        filename, _ = dialog.getOpenFileName(
            self, "Import file", filter="Excel (*.xls *.xlsx)"
        )
        if filename:
            if excel_type == "plate":
                self.parseExcel(filename)
            elif excel_type == "holder":
                self.parseHolderExcel(filename)
            else:
                raise Exception("Unrecognized input file type")

    def parseHolderExcel(self, filename):
        excel_file = pd.ExcelFile(filename)
        self.tables: Dict[str, LIXHolderTableWithCopy] = {}
        self.models = {}
        self.tabView.clear()
        holder_index = 0
        for sheet_name in excel_file.sheet_names:
            data: "pd.DataFrame" = excel_file.parse(sheet_name)
            if data.empty:
                continue
            self._dataframe = data

            mask = self._dataframe["holderName"].notna() & (
                self._dataframe["holderName"] != ""
            )
            self._dataframe["volume"] = self._dataframe["volume"].fillna(0).astype(int)
            self._dataframe["sampleName"] = (
                self._dataframe["sampleName"].fillna("").astype(str)
            )
            self._dataframe["bufferName"] = (
                self._dataframe["bufferName"].fillna("").astype(str)
            )
            start_index, end_index = None, None
            for index in self._dataframe[mask].index:
                if start_index is None:
                    start_index = index
                else:
                    end_index = index
                    self.addHolderTable(start_index, end_index, holder_index)
                    holder_index += 1
                    start_index = index
            self.addHolderTable(
                start_index, self._dataframe.index[-1] + 1, holder_index
            )
            break

    def addHolderTable(self, start_index, end_index, holder_index):
        filtered_data = self._dataframe.iloc[start_index:end_index]
        holder_name = self._dataframe["holderName"].iloc[start_index]
        model = LIXHolderPandasModel(
            filtered_data, holder_index, holder_name=holder_name
        )
        model.updated_holder_name.connect(self.updateTabName)
        self.addTableTab(model, holder_name)

    def updateTabName(self, tab_index, new_tab_name):
        self.tabView.setTabText(tab_index, new_tab_name)

    def addTableTab(self, model, title):
        table_view = self._createTableView()
        table_view.setItemDelegateForColumn(
            model.getColumnIndex("bufferName"), ComboBoxDelegate(self)
        )
        table_view.buffer_combobox = ComboBoxDelegate(self)
        table_view.setModel(model)
        self.tabView.addTab(table_view, title)
        self.tables[title] = table_view

    def parseExcel(self, filename):
        excel_file = pd.ExcelFile(filename)
        self.tables: Dict[str, LIXTableWithCopy] = {}
        self.models = {}
        self.tabView.clear()
        for sheet_name in excel_file.sheet_names:
            data: "pd.DataFrame" = excel_file.parse(sheet_name)
            if data.empty:
                continue
            # self.model = LIXPlatePandasModel(data)
            self._dataframe = data
            for well_name in self.well_names:
                filtered_data = data[data["Well"].str.startswith(well_name, na=False)]
                model = LIXPlatePandasModel(filtered_data, well_name=well_name)
                self.validateModel(model)
                table_view = self._createTableView()
                table_view.setModel(model)
                table_view.setItemDelegateForColumn(
                    filtered_data.columns.get_loc("Stock"), CheckBoxDelegate(self)
                )
                table_view.buffer_combobox = ComboBoxDelegate(self)
                table_view.setItemDelegateForColumn(
                    filtered_data.columns.get_loc("Buffer"), table_view.buffer_combobox
                )
                table_view.buffer_combobox.setItems(
                    [""]
                    + filtered_data[
                        filtered_data["Stock"].isna() & ~filtered_data["Sample"].isna()
                    ]["Sample"].to_list()
                )

                table_view.mixing_delegate = MixingDelegate(self)
                table_view.setItemDelegateForColumn(
                    data.columns.get_loc("Mixing"), table_view.mixing_delegate
                )
                table_view.resizeColumnsToContents()
                self.tabView.addTab(table_view, well_name)
                self.tables[well_name] = table_view
            break

    def validateExcel(self):
        for table_view in self.tables.values():
            self.validateModel(table_view.model())

    def validateModel(self, model):
        if not isinstance(model, LIXPlatePandasModel):
            return
        try:
            model.checkValidTemplate()
            model.preprocessData()
            model.validateData(self.config)
            # self.showModalMessage("Success", "Validated excel sucessfully")

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
        dataMenu = QtWidgets.QMenu("&Data Import", self)
        menuBar.addMenu(fileMenu)
        menuBar.addMenu(dataMenu)
        fileMenu.addActions(
            [
                self.saveExcelAction,
                self.exitAction,
                self.newPlateAction,
                self.newHolderAction,
            ]
        )

        dataMenu.addActions(
            [
                self.importExcelAction,
                self.importHolderExcelAction,
                self.validateExcelAction,
            ]
        )

        if self.config["admin_group"] in [
            grp.getgrgid(g).gr_name for g in os.getgroups()
        ]:
            dataMenu.addAction(self.configWindowAction)

    def _createTableView(self, dewar=False):
        # view = QtWidgets.QTableView()
        view = LIXTableWithCopy()
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
    spreadsheet_path = Path(sys.argv[0]).resolve().parent / Path(
        "holder_spreadsheet_default.xlsx"
    )
    ex.parseHolderExcel(str(spreadsheet_path))
    ex.show()
    sys.exit(app.exec_())
