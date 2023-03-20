from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtGui import QColor
import pandas as pd
import typing
import json
import re
from typing import Dict, Tuple


class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe """

    def __init__(self, dataframe: pd.DataFrame, parent=None) -> None:
        QAbstractTableModel.__init__(self, parent)
        self.validData = False
        self._dataframe = dataframe
        self.colors: Dict[Tuple[int, int], QColor ] = {}

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

    def data(self, index: QModelIndex, role=Qt.ItemDataRole) -> str | QColor | None:
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
    ) -> str | None:
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])

        return None

    def changeColor(self, row: int, column: int, color: QColor) -> None:
        ix = self.index(row, column)
        self.colors[(row, column)] = color
        self.dataChanged.emit(ix, ix, (Qt.BackgroundRole,))

    def resetColors(self) -> None:
        cells = list(self.colors.keys())
        self.colors = {}
        for row, col in cells:
            ix = self.index(row, col)
            self.dataChanged.emit(ix, ix, (Qt.BackgroundRole,))

    def validateData(self) -> None:
        self.resetColors()
        if not self._matchMasterlist(self._dataframe):
            raise TypeError("Pucks submitted do not match master list. Blacklisted pucks in red and pucks not in whitelist are yellow")

        if not self._checkSampleNames(self._dataframe):
            raise TypeError(
                """Invalid Sample names found. Only numbers, letters, dash ("-"), 
                and underscore ("_") are allowed. Total length is sample name cannot exceed 25"""
            )

        if not self._checkDuplicateSamples(self._dataframe):
            raise TypeError("Duplicate sample names found.")

        if not self._checkProposalNumbers(self._dataframe):
            raise TypeError(
                "Invalid proposal numbers"
            )
        
        if not self._checkDuplicatePuckPos(self._dataframe):
            raise TypeError('Duplicate Puck name and position combinations found')
        self.validData = True

    def preprocessData(self) -> None:
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

    def _checkProposalNumbers(self, data: pd.DataFrame) -> bool:
        proposalNumCol = 'proposalNum'
        # Remove all letters from proposal numbers
        data[proposalNumCol] = data[proposalNumCol].astype('str')
        data[proposalNumCol] = data[proposalNumCol].str.replace(r'\D', '')

        # Check if proposal numbers have 6 digits
        indices = data[proposalNumCol][~data[proposalNumCol].map(len).eq(6)].index
        col_index = data.columns.get_loc(proposalNumCol)
        if len(indices) > 0:
            self._changeCellColors(col_index, indices)
            return False

        if len(data[proposalNumCol].unique()) > 1:
            return False
        
        return True

    def _changeCellColors(self, column_index: int, row_indices, color=QColor(Qt.red)) -> None:
        for idx in row_indices:
            self.changeColor(idx, column_index, color)

    def _checkDuplicateSamples(self, data: pd.DataFrame) -> bool:
        duplicate_rows = data[data["sampleName"].duplicated(keep=False)]
        if len(duplicate_rows):
            column_index = data.columns.get_loc("sampleName")
            self._changeCellColors(column_index, duplicate_rows.index)
            return False
        return True
    
    def _checkDuplicatePuckPos(self, data: pd.DataFrame) -> bool:
        duplicate_rows = data[data.duplicated(subset=['puckName', 'position'], keep=False)]
        if len(duplicate_rows):
            column_index = data.columns.get_loc('puckName')
            self._changeCellColors(column_index, duplicate_rows.index)
            column_index = data.columns.get_loc('position')
            self._changeCellColors(column_index, duplicate_rows.index)
            return False
        return True

    def _checkSampleNames(self, data: pd.DataFrame) -> bool:
        sampleNameRegex = "[0-9a-zA-Z-_]{0,25}"
        non_matching_rows = data[~data["sampleName"].str.fullmatch(sampleNameRegex)]
        if len(non_matching_rows):
            column_index = data.columns.get_loc("sampleName")
            self._changeCellColors(column_index, non_matching_rows.index)
            return False
        return True

    def _matchMasterlist(self, data: pd.DataFrame) -> bool:
        with open("masterlist.json", "r") as f:
            masterList = json.load(f)
        enteredPucks = set(data["puckName"])
        missingPucks = enteredPucks - set(masterList["whitelist"])
        column_index = data.columns.get_loc("puckName")
        indices = []
        for puck in missingPucks:
            indices.extend(data.index[data["puckName"] == puck].tolist())
        self._changeCellColors(column_index, indices, color= QColor(Qt.yellow))
        
        disallowedPucks = enteredPucks.intersection(set(masterList['blacklist']))
        indices = []
        for puck in disallowedPucks:
            indices.extend(data.index[data["puckName"] == puck].tolist())
        self._changeCellColors(column_index, indices)
        
        if missingPucks or disallowedPucks:
            return False
        return True
