#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from collections import OrderedDict
from model import QueryResultListModel
from code_editor import CodeEditor
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

    default_column_size = 50
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
        self.customContextMenuRequested.connect(
            partial(self.show_menu, self.item_menu))

        model = QueryResultListModel("http://localhost:9200")
        self.setModel(model)

        header = self.header()
        header.setMinimumSectionSize(self.default_column_size)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(
            partial(self.show_menu, self.header_menu))
        model.modelReset.connect(self.restore_colums)
        model.modelReset.connect(self.init_header_menu)
        model.modelReset.connect(self.init_item_menu)

    def restore_colums(self):
        header = self.header()
        model = header.model()
        for i in range(model.columnCount()):
            field = model.headerData(i, Qt.Horizontal)
            default = (self.default_column_size,
                       field not in self.default_columns_visible)
            size, hidden = self.field_config.get(field, default)
            size = max(self.default_column_size, size)
            header.setSectionHidden(i, hidden)
            header.resizeSection(i, size)

    def toggle_column(self, i, field):
        def handler(toggled):
            self.header().setSectionHidden(i, not toggled)
            size = max(self.default_column_size,
                       self.header().sectionSize(i))
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

    def show_menu(self, menu, pos):
        global_pos = self.mapToGlobal(pos)
        menu.exec_(global_pos)

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


class QueryEditor(CodeEditor):

    dock_title = "Query"
    dock_name = "query_editor"

    def __init__(self):
        super(QueryEditor, self).__init__()
        self.setObjectName("query_editor")


class ResultDetailWidget(CodeEditor):

    def __init__(self, field=None):
        super(ResultDetailWidget, self).__init__()
        self.field = field
        self.setReadOnly(True)

    def update(self, model, current, previous):
        data = model.data(current, Qt.EditRole)
        if self.field is None:
            self.setPlainText(data)
        else:
            try:
                data = json.loads(data)
            except Exception:
                data = ""
            else:
                data = str(data.get(self.field, ""))
            self.setPlainText(data)

    @property
    def dock_title(self):
        if self.field:
            return "Field '{}'".format(self.field)
        else:
            return "Details"

    @property
    def dock_name(self):
        if self.field:
            return "details_dock_{}".format(self.field)
        else:
            return "details_dock"


def run_query_handler(query_editor, model, status_bar):
    def handler():
        status_bar.showMessage("running query...")
        query_text = query_editor.toPlainText()
        try:
            query = elasticsearch.Query(query_text)
        except Exception as e:
            status_bar.showMessage("query error: {}".format(str(e)))
        else:
            model.set_query(query)
    return handler


class DockManager(object):
    def __init__(self, window):
        self.window = window
        self.docks = dict()

    def add(self, widget,
            allowed_areas=Qt.AllDockWidgetAreas,
            dock_area=Qt.BottomDockWidgetArea):
        if widget.dock_name in self.docks:
            self.docks[widget.dock_name].setVisible(True)
            return

        dock_widget = QDockWidget(widget.dock_title, self.window)
        dock_widget.setObjectName(widget.dock_name)
        dock_widget.setWidget(widget)
        dock_widget.setAllowedAreas(allowed_areas)
        self.docks[widget.dock_name] = dock_widget

        if not self.window.restoreDockWidget(dock_widget):
            self.window.addDockWidget(dock_area, dock_widget)
        else:
            dock_widget.setVisible(True)


def _show_details(dock_manager, list_view, active_detail_docks, field):
    model = list_view.model()
    selection = list_view.selectionModel()
    view = ResultDetailWidget(field)
    view.update(model, list_view.currentIndex(), None)
    selection.currentChanged.connect(partial(view.update, model))
    dock_manager.add(view)
    active_detail_docks.append(field)


def show_details(dock_manager, list_view, active_detail_docks, action):
    _show_details(dock_manager, list_view, active_detail_docks, action.data())


def copy_item_value(clipboard, model, index):
    data = model.data(index)
    clipboard.setText(str(data) if data is not None else "")


def show_query_error(status_bar, error):
    status_bar.showMessage("query error: {}".format(error))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    with open("./app.css") as fp:
        app.setStyleSheet(fp.read())

    window = MainWindow()
    dock_manager = DockManager(window)
    active_detail_docks = []
    query_results = ResultsWidget()
    results_list = query_results.list_view
    window.setCentralWidget(query_results)

    results_list.model().query_error.connect(
        partial(show_query_error, query_results.status_bar)
    )
    results_list.item_menu.triggered.connect(
        partial(show_details, dock_manager, results_list, active_detail_docks)
    )
    results_list.doubleClicked.connect(
        partial(copy_item_value, app.clipboard(), results_list.model()))

    query_editor = QueryEditor()
    dock_manager.add(query_editor, dock_area=Qt.TopDockWidgetArea)

    window.run_query_shortcut.activated.connect(
        run_query_handler(query_editor,
                          results_list.model(),
                          query_results.status_bar)
    )

    window.closeSignal.connect(lambda:(
        settings.save_main_window(window),
        settings.save_query_results_view(results_list),
        settings.save_last_query(query_editor),
        settings.save_detail_docks(active_detail_docks),
    ))

    settings.restore_main_window(window)
    settings.restore_query_results_view(results_list)
    settings.restore_last_query(query_editor)
    settings.restore_detail_docks(
        partial(_show_details, dock_manager, results_list, active_detail_docks))

    window.show()
    sys.exit(app.exec_())
