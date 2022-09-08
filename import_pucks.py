from qtpy import QtWidgets
import sys
import pandas as pd
import json
from pandas_model import PandasModel

class ControlMain(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tableView = self._createTableView()
        self.setCentralWidget(self.tableView)
        self._createActions()
        self._createMenuBar()

    def _createActions(self):
        self.importExcelAction = QtWidgets.QAction("&Import Excel file", self)
        self.importExcelAction.triggered.connect(self.importExcel)
        self.exitAction = QtWidgets.QAction("&Exit", self)

    def importExcel(self):
        filename, _ = QtWidgets.QFileDialog().getOpenFileName(self,'Import file', filter="Excel (*.xls *.xlsx)")
        data = pd.read_excel(filename)

        model = PandasModel(data)
        self.tableView.setModel(model)
        
    def _validateData(self, data):
        with open('masterlist.json', 'r') as f:
            masterList = json.load(f)
        if "puckName" in data:
            enteredPucks = set(data['puckName'])
            missingPucks = enteredPucks - set(masterList['pucks'])
            if missingPucks:
                 

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QtWidgets.QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.importExcelAction)
        fileMenu.addAction(self.exitAction)

    def _createTableView(self):
        view = QtWidgets.QTableView()
        view.resize(800, 500)
        view.horizontalHeader().setStretchLastSection(True)
        view.setAlternatingRowColors(True)
        view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        return view

if __name__=="__main__":
    app = QtWidgets.QApplication(sys.argv)
    ex = ControlMain()
    ex.show()
    sys.exit(app.exec_())