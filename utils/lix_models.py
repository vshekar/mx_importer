import pandas as pd
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from utils.pandas_model import BasePandasModel


class LIXPlatePandasModel(BasePandasModel):
    def validateData(self, config):
        self.resetColors()
        self.checkValidTemplate(self._dataframe)
        self._dataframe = self._dataframe[
            ~self._dataframe["Sample"].isnull() & self._dataframe["Stock"].isnull()
        ][["Sample", "Buffer", "Well", "Volume (uL)"]]
        self.checkSampleDuplicates(self._dataframe)

    def checkValidTemplate(self, dataframe: pd.DataFrame):
        valid = True
        if len(dataframe) < 99:
            valid = False
        if dataframe["Notes"].iloc[-1] != "lix template":
            valid = False
            raise TypeError("This sample spreadsheet is not generated from a template")
        return valid

    def checkSampleDuplicates(self, dataframe: pd.DataFrame):
        duplicates = dataframe["Sample"].duplicated(keep=False)
        duplicate_indexes = dataframe.index[
            (dataframe["Sample"] != "") & duplicates
        ].tolist()
        column_index = dataframe.columns.get_loc("Sample")
        if duplicate_indexes:
            self._changeCellColors(
                column_index, duplicate_indexes, color=QColor(Qt.GlobalColor.red)
            )
            return False
        return True
