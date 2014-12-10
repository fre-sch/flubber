# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class QueryResultListModel(QAbstractItemModel):
    sort_dir = {
        Qt.AscendingOrder: "asc",
        Qt.DescendingOrder: "desc",
    }

    def __init__(self, service):
        super(QueryResultListModel, self).__init__()
        self.service = service
        self.query = None
        self.result = None
        self._sort = None

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

    def sort(self, column, order=Qt.AscendingOrder):
        print "sort", column, order
        sort = {
            Qt.AscendingOrder: "asc",
            Qt.DescendingOrder: "desc",
        }
        self._sort = (column, order)
        self.fetch_result()

    def set_query(self, query):
        self.query = query
        self.fetch_result()

    def fetch_result(self):
        if not self.query:
            return

        if self.result:
            sort_column, sort_dir = self._sort
            sort_field = str(self.headerData(sort_column, Qt.Horizontal))
            sort_dir = self.sort_dir[sort_dir]
            self.query.sort(sort_field, sort_dir)

        self.beginResetModel()
        self.result = self.service.fetch(self.query)
        self.reset()
        self.endResetModel()

