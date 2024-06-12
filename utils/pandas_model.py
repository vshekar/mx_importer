import json
import re
import typing
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QTableView


class BasePandasModel(QAbstractTableModel):
    """Base model interface Qt view"""

    def __init__(self, dataframe: pd.DataFrame, parent=None) -> None:
        QAbstractTableModel.__init__(self, parent)
        self.validData = False
        self._dataframe = dataframe
        self.colors: Dict[Tuple[int, int], QColor] = {}

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

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            data = self._dataframe.iloc[index.row(), index.column()]
            return str(data) if not pd.isna(data) else ""
        if role == Qt.ItemDataRole.BackgroundRole:
            color = self.colors.get((index.row(), index.column()))
            if color is not None:
                return color

        return None

    def rows(self):
        for i, row in self._dataframe.iterrows():
            yield row

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
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
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Orientation.Vertical:
                return str(self._dataframe.index[section])

        return None

    def changeColor(self, row: int, column: int, color: QColor) -> None:
        ix = self.index(row, column)
        self.colors[(row, column)] = color
        self.dataChanged.emit(ix, ix, (Qt.ItemDataRole.BackgroundRole,))

    def resetColors(self) -> None:
        cells = list(self.colors.keys())
        self.colors = {}
        for row, col in cells:
            ix = self.index(row, col)
            self.dataChanged.emit(ix, ix, (Qt.ItemDataRole.BackgroundRole,))

    def _changeCellColors(
        self, column_index: int, row_indices, color=QColor(Qt.GlobalColor.red)
    ) -> None:
        for idx in row_indices:
            self.changeColor(idx, column_index, color)


class PuckPandasModel(BasePandasModel):
    """A model to interface a Qt view with pandas dataframe"""

    def __init__(self, dataframe: pd.DataFrame, parent=None) -> None:
        super().__init__(dataframe, parent)
        self._dataframe = self._dataframe.dropna(how="all").reset_index(drop=True)

    def setPuckLists(self, pucklist):
        self.puckList = pucklist

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

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
                " Automatically changed invalid characters to underscore and highlighted in yellow"
            )

        if not self._checkEmptySamples(self._dataframe):
            raise TypeError("Empty sample names found")

        if not self._checkDuplicateSamples(self._dataframe):
            raise TypeError(
                "Duplicate sample names found. Added postfix and highlighted in yellow"
            )

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
            self._dataframe = self._dataframe[list(columns_present)]
            for col in columns_absent:
                self._dataframe.loc[:, col] = ""

        # Set data types for various columns. By this point all required columns should be present
        self._dataframe.loc[:, "position"] = pd.to_numeric(
            self._dataframe["position"], errors="coerce"
        ).astype("Int64")
        self._dataframe.loc[:, "proposalnum"] = pd.to_numeric(
            self._dataframe["proposalnum"], errors="coerce"
        ).astype("Int64")

        self._dataframe = self._dataframe.astype({"sequence": "str", "model": "str"})
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

    def _checkDuplicateSamples(self, data: pd.DataFrame) -> bool:
        column = "samplename"
        duplicate_rows = data[data[column].duplicated(keep=False)]
        duplicates = data[data.duplicated(column)]
        counter = (duplicates.groupby(column).cumcount() + 1).astype(str).str.zfill(3)
        data.loc[counter.index, column] += "_" + counter

        if len(duplicate_rows):
            column_index = data.columns.get_loc("samplename")
            self._changeCellColors(
                column_index, duplicate_rows.index, color=QColor(Qt.GlobalColor.yellow)
            )
            return False
        return True

    def _checkEmptySamples(self, data: pd.DataFrame) -> bool:
        column = "samplename"
        empty_rows = data[pd.isna(data[column])]
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
        # replacing non-matching characters
        data["samplename"] = data["samplename"].apply(
            lambda x: re.sub(r"[^0-9a-zA-Z-_]", "_", x)
        )

        # truncate strings to the first 25 characters
        data["samplename"] = data["samplename"].apply(lambda x: x[:25])

        if len(non_matching_rows):
            column_index = data.columns.get_loc("samplename")
            self._changeCellColors(
                column_index,
                non_matching_rows.index,
                color=QColor(Qt.GlobalColor.yellow),
            )
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
            self._changeCellColors(
                column_index, indices, color=QColor(Qt.GlobalColor.yellow)
            )

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


class DewarPandasModel(BasePandasModel):
    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            if str(value).startswith("DEWAR"):
                self.addDewar(index, value)
            else:
                self.addDataToNextRow(index, value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def addDewar(self, index: QModelIndex, value):
        tableView: QTableView = self.parent().tableView
        # If dewar column exists in the dataframe, jump to the first empty
        if value in self._dataframe.columns:
            first_empty_row = (
                self._dataframe[value].eq("").idxmax()
                if self._dataframe[value].eq("").any()
                else None
            )
            # if first_empty is none create a new row and go there
            if first_empty_row is None:
                self.addDataToNextRow(index, value)
            else:
                desired_index = tableView.model().index(
                    first_empty_row, self._dataframe.columns.get_loc(value)
                )
                tableView.setCurrentIndex(desired_index)
        else:
            self.addDataToNextColumn(index, value)

    def addDataToNextRow(self, index, value):
        tableView: QTableView = self.parent().tableView
        if len(self._dataframe.index) == index.row() + 1:
            self.beginInsertRows(QModelIndex(), index.row() + 1, index.row() + 1)
            self._dataframe = pd.concat(
                [
                    self._dataframe,
                    pd.Series(
                        ["" for i in range(len(self._dataframe.columns))],
                        index=self._dataframe.columns,
                    )
                    .to_frame()
                    .T,
                ],
                ignore_index=True,
            )
            self.endInsertRows()
        if (
            not self._dataframe[self._dataframe.columns[index.column()]]
            .isin([value])
            .any()
        ):
            self._dataframe.iloc[index.row(), index.column()] = value
            next_index = self.index(index.row() + 1, index.column())
            tableView.setCurrentIndex(next_index)

    def addDataToNextColumn(self, index, value):
        if index.row() == 0 and index.column() == 0:
            if None in self._dataframe.columns:
                self._dataframe.rename(columns={None: value}, inplace=True)
                self.layoutChanged.emit()
            else:
                self.addDewarColumn(index, value)
        else:
            self.addDewarColumn(index, value)

    def addDewarColumn(self, index, value):
        tableView: QTableView = self.parent().tableView
        # Add a column if we are running out of columns
        self.beginInsertColumns(QModelIndex(), index.column() + 1, index.column() + 1)
        self._dataframe[value] = ["" for i in range(len(self._dataframe.index))]
        self.endInsertColumns()
        desired_index = tableView.model().index(
            0, self._dataframe.columns.get_loc(value)
        )
        tableView.setCurrentIndex(desired_index)
