#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from collections import OrderedDict
from model import QueryResultListModel
import settings
import elasticsearch
from functools import partial
import json


class FontFixer(object):

    font = QFont()
    font.setStyleHint(QFont.Monospace)
    font.setFamily("Menlo, 'Bitstream Vera Sans Mono'")

    @classmethod
    def set_monospace_font(self, widget):
        widget.setFont(self.font)


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
        self.setAlternatingRowColors(1)
        self.setUniformRowHeights(1)
        self.setSortingEnabled(True)
        FontFixer.set_monospace_font(self)

        model = QueryResultListModel("http://localhost:9200")
        self.setModel(model)
        header = self.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)
        model.modelReset.connect(self.restore_colums)
        model.modelReset.connect(self.init_header_menu)

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
        self._header_menu = QMenu(self)
        header = self.header()
        model = header.model()
        for i in range(model.columnCount()):
            field = model.headerData(i, Qt.Horizontal)
            field_visible = not header.isSectionHidden(i)
            action = QAction(field, self._header_menu)
            action.setCheckable(True)
            action.setChecked(field_visible)
            action.toggled.connect(self.toggle_column(i, field))
            self._header_menu.addAction(action)

    def show_header_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        self._header_menu.exec_(global_pos)


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
        FontFixer.set_monospace_font(self)


class ResultDetailWidget(QPlainTextEdit):

    def __init__(self):
        super(ResultDetailWidget, self).__init__()
        self.setReadOnly(True)
        FontFixer.set_monospace_font(self)

    def update(self, model, current, previous):
        data = model.data(current, Qt.EditRole)
        self.setPlainText(data)


class ResultFieldWidget(QPlainTextEdit):

    def __init__(self):
        super(ResultFieldWidget, self).__init__()
        self.setReadOnly(True)
        FontFixer.set_monospace_font(self)
        self.field = "message"

    def update(self, model, current, previous):
        data = json.loads(model.data(current, Qt.EditRole))
        self.setPlainText(data.get(self.field))


def run_query_handler(query_editor, model):
    def handler():
        query_text = unicode(query_editor.toPlainText())
        query = elasticsearch.Query(query_text)
        model.set_query(query)
    return handler


if __name__ == '__main__':
    app = QApplication(sys.argv)

    with open("./app.css") as fp:
        app.setStyleSheet(fp.read())

    window = MainWindow()
    query_results = ResultsWidget()
    results_list = query_results.list_view
    window.setCentralWidget(query_results)

    query_editor = QueryEditor()
    dock_widget = QDockWidget("Query", window)
    dock_widget.setObjectName("query_editor")
    dock_widget.setWidget(query_editor)
    dock_widget.setAllowedAreas(
        Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        | Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
    window.addDockWidget(Qt.TopDockWidgetArea, dock_widget)

    result_detail_view = ResultDetailWidget()
    dock_widget = QDockWidget("Details", window)
    dock_widget.setObjectName("details_dock")
    dock_widget.setWidget(result_detail_view)
    dock_widget.setAllowedAreas(
        Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        | Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
    window.addDockWidget(Qt.BottomDockWidgetArea, dock_widget)

    result_field_view = ResultFieldWidget()
    dock_widget = QDockWidget("Field", window)
    dock_widget.setObjectName("field_dock")
    dock_widget.setWidget(result_field_view)
    dock_widget.setAllowedAreas(
        Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        | Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
    window.addDockWidget(Qt.BottomDockWidgetArea, dock_widget)


    results_list.selectionModel().currentChanged.connect(
        partial(result_detail_view.update, results_list.model())
    )
    results_list.selectionModel().currentChanged.connect(
        partial(result_field_view.update, results_list.model())
    )

    window.run_query_shortcut.activated.connect(
        run_query_handler(query_editor, results_list.model())
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
