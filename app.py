#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from collections import OrderedDict
from model import QueryResultListModel
import settings
import elasticsearch
from functools import partial
import json


class OSXItemActivationFix(object):

    def keyPressEvent(self, event):
        """despite the docs stating otherwise, "activated" is not emitted on
        keyboard events an OSX user would expect"""
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and int(event.modifiers()) == 0
                and self.currentIndex().isValid()
                and self.state() != QAbstractItemView.EditingState):
            self.activated.emit(self.currentIndex())
            return
        super(OSXItemActivationFix, self).keyPressEvent(event)


class MainWindow(QMainWindow):

    closeSignal = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setContentsMargins(4, 4, 4, 4)
        self.run_query_shortcut = QShortcut(
            QKeySequence.fromString("Ctrl+R"), self)

    def closeEvent(self, event):
        self.closeSignal.emit()


class ResultListView(OSXItemActivationFix, QTreeView):

    default_columns_visible = [
        "asctime",
        "levelname",
        "message",
    ]

    def __init__(self):
        super(ResultListView, self).__init__()
        self.field_config = dict()
        self.header_menu = QMenu(self)
        self.item_menu = QMenu(self)

        self.setAlternatingRowColors(1)
        self.setUniformRowHeights(1)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_item_menu)

        model = QueryResultListModel("http://localhost:9200")
        self.setModel(model)

        header = self.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)
        model.modelReset.connect(self.restore_colums)
        model.modelReset.connect(self.init_header_menu)
        model.modelReset.connect(self.init_item_menu)

    def restore_colums(self):
        header = self.header()
        model = header.model()
        for i in range(model.columnCount()):
            field = model.headerData(i, Qt.Horizontal)
            default = (100, field not in self.default_columns_visible)
            size, hidden = self.field_config.get(field, default)
            header.setSectionHidden(i, hidden)
            header.resizeSection(i, size)

    def toggle_column(self, i, field):
        def handler(toggled):
            self.header().setSectionHidden(i, not toggled)
            size = int(max(50, self.header().sectionSize(i)))
            self.field_config[field] = (size, not toggled)
        return handler

    def init_header_menu(self):
        self.header_menu.clear()
        header = self.header()
        model = header.model()
        for i in range(model.columnCount()):
            field = model.headerData(i, Qt.Horizontal)
            field_visible = not header.isSectionHidden(i)
            action = QAction(field, self.header_menu)
            action.setCheckable(True)
            action.setChecked(field_visible)
            action.toggled.connect(self.toggle_column(i, field))
            self.header_menu.addAction(action)

    def show_header_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        self.header_menu.exec_(global_pos)

    def init_item_menu(self):
        self.item_menu.clear()
        action = QAction("Show details", self.item_menu)
        action.setData(None)
        self.item_menu.addAction(action)

        header = self.header()
        model = header.model()
        for i in range(model.columnCount()):
            field = model.headerData(i, Qt.Horizontal)
            action = QAction("Show '{}'".format(field), self.item_menu)
            action.setData(field)
            self.item_menu.addAction(action)

    def show_item_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        self.item_menu.exec_(global_pos)


class ResultsWidget(QWidget):

    def __init__(self):
        super(ResultsWidget, self).__init__()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.list_view = ResultListView()
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        layout.addWidget(self.list_view)
        layout.addWidget(self.status_bar)
        model = self.list_view.model()
        model.modelReset.connect(self.update_status_bar)

    def update_status_bar(self):
        model = self.list_view.model()
        self.status_bar.showMessage(
            "total: {}".format(model.result.total)
        )


class QueryEditor(QPlainTextEdit):

    def __init__(self):
        super(QueryEditor, self).__init__()
        self.setObjectName("query_editor")


class ResultDetailWidget(QPlainTextEdit):

    def __init__(self, field=None):
        super(ResultDetailWidget, self).__init__()
        self.field = field
        self.setReadOnly(True)

    def update(self, model, current, previous):
        data = model.data(current, Qt.EditRole)
        if self.field is None:
            self.setPlainText(data)
        else:
            data = json.loads(data)
            self.setPlainText(data.get(self.field, ""))


def run_query_handler(query_editor, model, status_bar):
    def handler():
        status_bar.showMessage("running query...")
        query_text = query_editor.toPlainText()
        query = elasticsearch.Query(query_text)
        model.set_query(query)
    return handler


def show_details(window, list_view):
    model = list_view.model()
    selection = list_view.selectionModel()

    def handler(action):
        field = action.data()
        if field:
            title = "Field '{}'".format(field)
            name = "details_dock_{}".format(field)
        else:
            title = "Details"
            name = "details_dock"

        view = ResultDetailWidget(field)
        view.update(model, list_view.currentIndex(), None)
        selection.currentChanged.connect(partial(view.update, model))

        dock_widget = QDockWidget(title, window)
        dock_widget.setObjectName(name)
        dock_widget.setWidget(view)
        dock_widget.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
            | Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        window.addDockWidget(Qt.BottomDockWidgetArea, dock_widget)

    return handler


if __name__ == '__main__':
    app = QApplication(sys.argv)

    with open("./app.css") as fp:
        app.setStyleSheet(fp.read())

    window = MainWindow()
    query_results = ResultsWidget()
    results_list = query_results.list_view
    window.setCentralWidget(query_results)

    results_list.item_menu.triggered.connect(
        show_details(window, results_list)
    )

    query_editor = QueryEditor()
    dock_widget = QDockWidget("Query", window)
    dock_widget.setObjectName("query_editor")
    dock_widget.setWidget(query_editor)
    dock_widget.setAllowedAreas(
        Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        | Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
    window.addDockWidget(Qt.TopDockWidgetArea, dock_widget)

    window.run_query_shortcut.activated.connect(
        run_query_handler(query_editor, results_list.model(), query_results.status_bar)
    )

    window.closeSignal.connect(lambda:(
        settings.save_main_window(window),
        settings.save_query_results_view(results_list),
        settings.save_last_query(query_editor),
    ))

    settings.restore_main_window(window)
    settings.restore_query_results_view(results_list)
    settings.restore_last_query(query_editor)

    window.show()
    sys.exit(app.exec_())
