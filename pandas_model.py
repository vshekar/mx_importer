from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtGui import QColor
import pandas as pd
import typing
import json
import re


class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe """

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.validData = False
        self._dataframe = dataframe
        self.colors = {}

    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe)

        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._dataframe.iloc[index.row(), index.column()])
        if role == Qt.BackgroundRole:
            color = self.colors.get((index.row(), index.column()))
            if color is not None:
                return color

        return None

    def rows(self):
        for i, row in self._dataframe.iterrows():
            yield row

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        if role == Qt.EditRole:
            self._dataframe.iloc[index.row(), index.column()] = value
            return True
        return False

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])

        return None

    def changeColor(self, row, column, color):
        ix = self.index(row, column)
        self.colors[(row, column)] = color
        self.dataChanged.emit(ix, ix, (Qt.BackgroundRole,))

    def resetColors(self):
        cells = list(self.colors.keys())
        self.colors = {}
        for row, col in cells:
            ix = self.index(row, col)
            self.dataChanged.emit(ix, ix, (Qt.BackgroundRole,))

    def validateData(self):
        self.resetColors()
        if not self._matchMasterlist(self._dataframe):
            raise TypeError("Pucks submitted do not match master list")

        if not self._checkSampleNames(self._dataframe):
            raise TypeError(
                """Invalid Sample names found. Only numbers, letters, dash ("-"), 
                and underscore ("_") are allowed. Total length is sample name cannot exceed 25"""
            )

        if not self._checkDuplicateSamples(self._dataframe):
            raise TypeError("Duplicate sample names found.")

        if not self._checkProposalNumbers(self._dataframe):
            raise TypeError(
                "Invalid proposal numbers, either are not unique or not all of them are integers"
            )
        self.validData = True

    def preprocessData(self):
        required_columns = set(
            ["puckName", "sampleName", "proposalNum", "position", "model", "sequence"]
        )
        if not required_columns.issubset(self._dataframe.columns):
            raise TypeError(
                f"Missing columns: {required_columns - set(self._dataframe.columns)}"
            )
        # Remove all whitespaces from string columns
        for col in required_columns:
            self._dataframe[col] = self._dataframe[col].astype('string')
            if col != "sampleName":
                self._dataframe[col].str.replace(r"\s+", "", regex=True)
            else:
                self._dataframe[col].str.replace(r"(\.|\s)+", "", regex=True)

    def _checkProposalNumbers(self, data: pd.DataFrame):
        # if not pd.api.types.is_integer_dtype(data["proposalNum"]):
        #    return False
        try:
            data["proposalNum"] = data["proposalNum"].astype(int)
        except:
            return False
        if len(data["proposalNum"].unique()) > 1:
            return False
        return True

    def _changeCellColors(self, column_index, row_indices, color=QColor(Qt.red)):
        for idx in row_indices:
            self.changeColor(idx, column_index, color)

    def _checkDuplicateSamples(self, data: pd.DataFrame):
        duplicate_rows = data[data["sampleName"].duplicated(keep=False)]
        if len(duplicate_rows):
            column_index = data.columns.get_loc("sampleName")
            self._changeCellColors(column_index, duplicate_rows.index)
            return False
        return True

    def _checkSampleNames(self, data: pd.DataFrame):
        sampleNameRegex = "[0-9a-zA-Z-_]{0,25}"
        non_matching_rows = data[~data["sampleName"].str.fullmatch(sampleNameRegex)]
        if len(non_matching_rows):
            column_index = data.columns.get_loc("sampleName")
            self._changeCellColors(column_index, non_matching_rows.index)
            return False
        return True

    def _matchMasterlist(self, data: pd.DataFrame):
        with open("masterlist.json", "r") as f:
            masterList = json.load(f)
        enteredPucks = set(data["puckName"])
        missingPucks = enteredPucks - set(masterList["pucks"])
        if missingPucks:
            indices = []
            column_index = data.columns.get_loc("puckName")
            for puck in missingPucks:
                indices.extend(data.index[data["puckName"] == puck].tolist())
            self._changeCellColors(column_index, indices)
            return False
        return True
