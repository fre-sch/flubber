# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class QueryResultListModel(QAbstractItemModel):

    def __init__(self, result=None):
        super(QueryResultListModel, self).__init__()
        self.result = result

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        if self.result:
            return len(self.result)
        return 0

    def index(self, row, column, parent):
        return self.createIndex(row, column, None)

    def parent(self, index):
        return QModelIndex()

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        if self.result:
            return len(self.result.fields)
        return 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if not self.result:
            return None

        if role == Qt.DisplayRole:
            data = self.result.get(index.row(), index.column())
            try:
                return data.split("\n")[0]
            except AttributeError:
                return None

        elif role == Qt.EditRole:
            return self.result.get_text(index.row())

        return None

    def headerData(self, column, orientation, role=Qt.DisplayRole):
        if not self.result:
            return None
        if role == Qt.DisplayRole:
            return self.result.fields[column]
        return None

    def update_result(self, result):
        self.beginResetModel()
        self.result = result
        self.reset()
        self.endResetModel()

