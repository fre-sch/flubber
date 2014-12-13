# -*- coding: utf-8 -*-
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
import elasticsearch
from functools import partial
import json


class QueryResultListModel(QAbstractItemModel):
    sort_dir = {
        Qt.AscendingOrder: "asc",
        Qt.DescendingOrder: "desc",
    }

    def __init__(self, service_url):
        super(QueryResultListModel, self).__init__()
        self.service_url = QUrl(service_url + "/_search")
        self.qnetwork = QNetworkAccessManager(self)
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

        request = QNetworkRequest(self.service_url)
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        reply = self.qnetwork.post(request, self.query_to_bytearray())
        reply.finished.connect(partial(self._update_result, reply))

    def _update_result(self, reply):
        n = reply.bytesAvailable()
        data = reply.read(n)
        self.beginResetModel()
        self.result = elasticsearch.Result(data)
        #self.reset()
        self.endResetModel()

    def query_to_bytearray(self):
        json_data = json.dumps(self.query.data)
        print(json_data)
        return QByteArray(json_data)
