from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtGui import QColor
import pandas as pd
import typing
import json
import re
from typing import Dict, Tuple


class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe"""

    def __init__(self, dataframe: pd.DataFrame, parent=None) -> None:
        QAbstractTableModel.__init__(self, parent)
        self.validData = False
        self._dataframe = dataframe.dropna(how="all")
        self.colors: Dict[Tuple[int, int], QColor] = {}

    def setPuckLists(self, pucklist):
        self.puckList = pucklist

    def rowCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

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

    def data(self, index: QModelIndex, role=Qt.ItemDataRole) -> "str | QColor | None":
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
            self.dataChanged.emit(index, index)
            return True
        return False

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ) -> "str | None":
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

    def validateData(self, config) -> None:
        self.resetColors()
        if not self._matchMasterlist(self._dataframe, config):
            raise TypeError(
                "Pucks submitted do not match master list. Blacklisted pucks in red and pucks not in whitelist are yellow"
            )

        if not self._checkSampleNames(self._dataframe):
            raise TypeError(
                'Invalid Sample names found. Only numbers, letters, dash ("-"),'
                ' and underscore ("_") are allowed. Total length of sample name cannot exceed 25'
            )

        if not self._checkEmptySamples(self._dataframe):
            raise TypeError("Empty sample names found")

        if not self._checkDuplicateSamples(self._dataframe):
            raise TypeError("Duplicate sample names found.")

        if not self._checkProposalNumbers(self._dataframe):
            raise TypeError("Invalid proposal numbers")

        if not self._checkDuplicatePuckPos(self._dataframe):
            raise TypeError("Duplicate Puck name and position combinations found")
        self.validData = True

    def preprocessData(self) -> None:
        # Note all column names are lowercase, good for comparison
        required_columns_list = [
                    "puckname",
                    "position",
                    "samplename",
                    "model",
                    "sequence",
                    "proposalnum",
                ]
        required_columns = set(required_columns_list)
        self._dataframe.columns = self._dataframe.columns.str.lower()
        columns_absent = None
        
        # Change current dataframe to only have required columns
        if not required_columns.issubset(self._dataframe.columns):
            columns_present = required_columns.intersection(self._dataframe.columns)
            columns_absent = required_columns - set(self._dataframe.columns)
            self._dataframe = self._dataframe[columns_present]
            for col in columns_absent:
                self._dataframe.loc[:,col] = ''

        # Set data types for various columns. By this point all required columns should be present
        self._dataframe.loc[:,'position'] = pd.to_numeric(self._dataframe['position'], errors='coerce').astype('Int64')
        self._dataframe.loc[:,'proposalnum'] = pd.to_numeric(self._dataframe['proposalnum'], errors='coerce').astype('Int64')

        self._dataframe = self._dataframe.astype({'sequence': 'str', 'model': 'str'})
        self._dataframe = self._dataframe[required_columns_list]


        # Remove all whitespaces from string columns
        for col in required_columns:
            self._dataframe[col] = self._dataframe[col].astype("string")
            if col != "samplename":
                self._dataframe[col].str.replace(r"\s+", "", regex=True)
            else:
                self._dataframe[col].str.replace(r"(\.|\s)+", "", regex=True)

        
        if columns_absent:
            raise TypeError(
                f"Missing column headers in excel file: {columns_absent}."
                " If data is present in the excel file, make sure column names are correct and import the file again."
                " Otherwise enter values into the empty column generated by the puck importer."
            )


    def _checkProposalNumbers(self, data: pd.DataFrame) -> bool:
        proposalNumCol = "proposalnum"
        # Remove all letters from proposal numbers
        data[proposalNumCol] = data[proposalNumCol].astype("str")
        data[proposalNumCol] = data[proposalNumCol].str.replace(r"\D", "", regex=True)

        # Check if proposal numbers have 6 digits
        indices = data[proposalNumCol][~data[proposalNumCol].map(len).eq(6)].index
        col_index = data.columns.get_loc(proposalNumCol)
        if len(indices) > 0:
            self._changeCellColors(col_index, indices)
            return False

        if len(data[proposalNumCol].unique()) > 1:
            return False

        return True

    def _changeCellColors(
        self, column_index: int, row_indices, color=QColor(Qt.red)
    ) -> None:
        for idx in row_indices:
            self.changeColor(idx, column_index, color)

    def _checkDuplicateSamples(self, data: pd.DataFrame) -> bool:
        duplicate_rows = data[data["samplename"].duplicated(keep=False)]
        if len(duplicate_rows):
            column_index = data.columns.get_loc("samplename")
            self._changeCellColors(column_index, duplicate_rows.index)
            return False
        return True

    def _checkEmptySamples(self, data: pd.DataFrame) -> bool:
        empty_rows = data[pd.isna(data["samplename"])]
        if len(empty_rows):
            column_index = data.columns.get_loc("samplename")
            self._changeCellColors(column_index, empty_rows.index)
            return False
        return True

    def _checkDuplicatePuckPos(self, data: pd.DataFrame) -> bool:
        duplicate_rows = data[
            data.duplicated(subset=["puckname", "position"], keep=False)
        ]
        if len(duplicate_rows):
            column_index = data.columns.get_loc("puckname")
            self._changeCellColors(column_index, duplicate_rows.index)
            column_index = data.columns.get_loc("position")
            self._changeCellColors(column_index, duplicate_rows.index)
            return False
        return True

    def _checkSampleNames(self, data: pd.DataFrame) -> bool:
        sampleNameRegex = "[0-9a-zA-Z-_]{0,25}"
        non_matching_rows = data[~data["samplename"].str.fullmatch(sampleNameRegex)]
        if len(non_matching_rows):
            column_index = data.columns.get_loc("samplename")
            self._changeCellColors(column_index, non_matching_rows.index)
            return False
        return True

    def _matchMasterlist(self, data: pd.DataFrame, config) -> bool:
        masterList = self.puckList
        enteredPucks = set(data["puckname"])
        column_index = data.columns.get_loc("puckname")

        missingPucks = set()
        if not config.get("disable_whitelist", False):
            missingPucks = enteredPucks - set(masterList["whitelist"])

            # data["puckname"].fillna('MISSING', inplace=True)
            indices = []
            for puck in missingPucks:
                if not pd.isnull(puck):
                    indices.extend(data.index[data["puckname"] == puck].tolist())
            self._changeCellColors(column_index, indices, color=QColor(Qt.yellow))

        disallowedPucks = set()
        if not config.get("disable_blacklist", False):
            disallowedPucks = enteredPucks.intersection(set(masterList["blacklist"]))
            indices = []
            for puck in disallowedPucks:
                indices.extend(data.index[data["puckname"] == puck].tolist())
            self._changeCellColors(column_index, indices)

        if missingPucks or disallowedPucks:
            return False
        return True
