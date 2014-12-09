# -*- coding: utf-8 -*-
import json
import shlex
import requests


class Service(object):

    def __init__(self, url):
        self.url = url

    def query(self, query):
        response = requests.post(self.url + "/_search",
                                 json=query.to_json())
        return Result(response.json())


class Query(object):

    def __init__(self, raw=""):
        self.raw = "\n".join(
            line.split("#", 1)[0]
            for line in raw.split("\n")
        )

    def to_json(self):
        return json.loads(self.raw)

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
        self.data = data
        self.fields = self.get_all_fields(data)

    def get_all_fields(self, data):
        fields = set([])
        for hit in data["hits"]["hits"]:
            fields.update(hit["_source"].keys())
        return sorted(fields)

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
