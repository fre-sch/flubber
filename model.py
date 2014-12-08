from PyQt4.QtCore import *
from PyQt4.QtGui import *
import json
import shlex


class EsQuery(object):

    def __init__(self):
        pass

    @classmethod
    def parse(cls, value):
        parts = shlex.split(value)
        filter_type, field_name = parts[:2]
        filter_args = parts[2:]
        if filter_type == "query":
            # this is needlessly retarded because of elasticsearch :(
            query_string = {"query_string": {
                "fields": [field_name, ],
                "query": filter_args[0],
            }}
            return {"fquery": {
                "query": query_string,
                "_cached": True
            }}

        elif len(filter_args) > 1:
            return {filter_type: {field_name: filter_args}}

        else:
            return {filter_type: {field_name: filter_args[0]}}


class EsQueryResult(object):

    def __init__(self):
        self.fields = []

    def fetch(self):
        with open("tests/example_logs.json") as fp:
            content = json.load(fp)
            self.data = content
        fields = set([])
        for hit in self.data["hits"]["hits"]:
            fields.update(hit["_source"].keys())
        self.fields = sorted(fields)

    def __len__(self):
        return len(self.data["hits"]["hits"])

    def __getitem__(self, key):
        return self.data["hits"]["hits"][key]

    def get(self, row, column):
        field = self.fields[column]
        try:
            return self[row]["_source"][field]
        except (KeyError, IndexError):
            return None

    def get_text(self, row):
        return json.dumps(self[row]["_source"], indent=2)


class QueryResultListModel(QAbstractItemModel):

    def __init__(self, query_result=None):
        super(QueryResultListModel, self).__init__()
        self.query_result = query_result

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        if self.query_result:
            return len(self.query_result)
        return 0

    def index(self, row, column, parent):
        return self.createIndex(row, column, None)

    def parent(self, index):
        return QModelIndex()

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        if self.query_result:
            return len(self.query_result.fields)
        return 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if not self.query_result:
            return None

        if role == Qt.DisplayRole:
            data = self.query_result.get(index.row(), index.column())
            try:
                return data.split("\n")[0]
            except AttributeError:
                return None

        elif role == Qt.EditRole:
            return self.query_result.get_text(index.row())

        return None

    def headerData(self, column, orientation, role=Qt.DisplayRole):
        if not self.query_result:
            return None
        if role == Qt.DisplayRole:
            return self.query_result.fields[column]
        return None

