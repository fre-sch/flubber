# -*- coding: UTF-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from collections import OrderedDict
from contextlib import contextmanager


class Settings(QSettings):
    def __init__(self):
        super(Settings, self).__init__("Frederik Schumacher", "Flubber")

    @contextmanager
    def group_(self, name):
        self.beginGroup(name)
        yield
        self.endGroup()

    def child_groups(self, str_type=str):
        """
        Because childGroups returns a QStringList with QString. QString is
        almost a python str except when compared/hashed. Which sucks for use
        in lists, dicts and sets:
            "foo" in stringlist does not work as expected
        """
        return map(str_type, self.childGroups())


def restore_main_window(window):
    s = Settings()
    with s.group_("MainWindow"):
        window.resize(
            s.value("size", QSize(600, 400)).toSize()
        )


def save_main_window(window):
    s = Settings()
    with s.group_("MainWindow"):
        s.setValue("size", window.size())


def restore_splitter(splitter):
    s = Settings()
    with s.group_("splitter"):
        state = s.value("state", "").toByteArray()
        splitter.restoreState(state)


def save_splitter(splitter):
    s = Settings()
    with s.group_("splitter"):
        s.setValue("state", splitter.saveState())


def restore_query_results_view(view):
    s = Settings()
    with s.group_("query_results_view"):
        with s.group_("header"):
            for field in s.child_groups():
                with s.group_(field):
                    size = max(100, s.value("size", type=int))
                    hidden = s.value("hidden", type=bool)
                    view.field_config[field] = size, hidden



def save_query_results_view(view):
    s = Settings()
    header = view.header()
    model = view.model()
    with s.group_("query_results_view"):
        with s.group_("header"):
            current_fields = [model.headerData(i, Qt.Horizontal)
                              for i in range(header.count())]
            for i, field in enumerate(current_fields):
                with s.group_(field):
                    s.setValue("size", header.sectionSize(i))
                    s.setValue("hidden", header.isSectionHidden(i))


def restore_last_query(editor):
    s = Settings()
    with s.group_("last_query"):
        text = s.value("text").toString()
        editor.setPlainText(text)


def save_last_query(editor):
    s = Settings()
    with s.group_("last_query"):
        s.setValue("text", editor.toPlainText())
