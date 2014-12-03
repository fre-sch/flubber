#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from model import EsQuery, EsQueryResult, QueryResultListModel
from collections import OrderedDict


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

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setMinimumSize(600, 400)
        self.run_query_shortcut = QShortcut(
            QKeySequence.fromString("Ctrl+R"), self)
        self.add_query_item_shortcut = QShortcut(
            QKeySequence.fromString("Ctrl++"), self)


class QueryResultListWidget(OSXItemActivationFix, QTreeView):

    default_columns_visible = [
        "asctime",
        "levelname",
        "message",
    ]

    def __init__(self):
        super(QueryResultListWidget, self).__init__()
        results = EsQueryResult.fetch()
        model = QueryResultListModel(results)
        self.setAlternatingRowColors(1)
        self.setModel(model)
        header = self.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)
        FontFixer.set_monospace_font(self)
        self.init_columns_visible(results.fields)
        self.create_header_menu(results.fields)

    def init_columns_visible(self, fields):
        for i, field in enumerate(fields):
            field_visible = field in self.default_columns_visible
            self.setColumnHidden(i, not field_visible)

    def toggle_column(self, i, field):
        def handler(toggled):
            self.setColumnHidden(i, not toggled)
        return handler

    def create_header_menu(self, fields):
        self._header_menu = QMenu(self)
        for i, field in enumerate(fields):
            field_visible = field in self.default_columns_visible
            action = QAction(field, self._header_menu)
            action.setCheckable(True)
            action.setChecked(field_visible)
            action.toggled.connect(self.toggle_column(i, field))
            self._header_menu.addAction(action)

    def show_header_menu(self, pos):
        global_pos = self.mapToGlobal(pos)
        self._header_menu.exec_(global_pos)


class QueryTermsWidget(OSXItemActivationFix, QListWidget):

    def __init__(self):
        super(QueryTermsWidget, self).__init__()
        self.setResizeMode(QListView.Adjust)
        FontFixer.set_monospace_font(self)

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key_Backspace, Qt.Key_Delete)
                and self.currentIndex().isValid()
                and self.state() != QAbstractItemView.EditingState):
            index = self.currentIndex()
            item = self.takeItem(index.row())
            del item
            return
        super(QueryTermsWidget, self).keyPressEvent(event)

    def __iter__(self):
        return (
            self.item(i) for i in range(len(self))
        )


class QueryResultWidget(QTextEdit):
    def __init__(self):
        super(QueryResultWidget, self).__init__()
        self.setReadOnly(True)
        FontFixer.set_monospace_font(self)


def add_query_item(list_widget):
    def handler():
        item = list_widget.currentItem()
        item = QListWidgetItem("new query item", list_widget)
        item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        list_widget.editItem(item)
    return handler


def run_query_handler(list_widget):
    def handler():
        items = [item for item in list_widget
                 if item.checkState() == Qt.Checked]

        for item in items:
            query_item = EsQuery.parse(str(item.text()))
            print query_item

    return handler


def show_result_in_editor(rv, te):
    def handler(current, previous):
        data = rv.model().data(current, Qt.EditRole)
        te.setText(data)
    return handler


if __name__ == '__main__':
    app = QApplication(sys.argv)

    query_terms_view = QueryTermsWidget()
    query_results_view = QueryResultListWidget()
    query_result_view = QueryResultWidget()

    query_results_view.selectionModel()\
        .currentChanged\
        .connect(show_result_in_editor(query_results_view, query_result_view))

    window = MainWindow()
    window.run_query_shortcut\
        .activated.connect(run_query_handler(query_terms_view))
    window.add_query_item_shortcut\
        .activated.connect(add_query_item(query_terms_view))

    sp = QSplitter()
    sp.setOrientation(Qt.Vertical)
    sp.addWidget(query_terms_view)
    sp.addWidget(query_results_view)
    sp.addWidget(query_result_view)
    sp.setCollapsible(0, False)
    sp.setCollapsible(1, False)
    sp.setCollapsible(2, False)
    sp.setStretchFactor(0, 0)
    sp.setStretchFactor(1, 10)
    sp.setStretchFactor(2, 2)
    sp.setSizes([50, 300, 100])

    window.setCentralWidget(sp)
    window.show()
    sys.exit(app.exec_())
