# -*- coding: utf-8 -*-
import json
import shlex


class Query(object):

    def __init__(self, raw=""):
        query_dict = json.loads("\n".join(
            line.split("#", 1)[0]
            for line in raw.split("\n")
        ))
        self.data = dict(
            sort=dict(),
            size=100,
        )
        self.data.update(query_dict)

    def size(self, size):
        self.data["size"] = size
        return self

    def from_(self, from_):
        self.data["from"] = from_
        return self

    def sort(self, field, dir_):
        self.data["sort"] = {field: dir_}
        # field_exists = {"exists": {"field": field}}
        # filters = self.data["query"]["filtered"]["filter"]
        # if field_exists not in filters:
        #     filters.append(field_exists)
        return self

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


class Result(object):

    def __init__(self, data):
        if data:
            self.data = json.loads(data.decode("UTF-8"))
        else:
            self.data = {}

        self.fields = self.get_all_fields(self.data)

    @property
    def total(self):
        try:
            return self.data["hits"]["total"]
        except (AttributeError, KeyError):
            return 0

    def get_all_fields(self, data):
        try:
            fields = set([])
            for hit in data["hits"]["hits"]:
                fields.update(hit["_source"].keys())
            return sorted(fields)
        except KeyError:
            return []

    def __len__(self):
        try:
            return len(self.data["hits"]["hits"])
        except KeyError:
            return 0

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

