#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from collections import OrderedDict
from model import EsQuery, EsQueryResult, QueryResultListModel
import settings


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
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        self.setCentralWidget(splitter)
        self.run_query_shortcut = QShortcut(
            QKeySequence.fromString("Ctrl+R"), self)
        self.add_query_item_shortcut = QShortcut(
            QKeySequence.fromString("Ctrl++"), self)

    def closeEvent(self, event):
        self.closeSignal.emit()


class QueryResultListWidget(OSXItemActivationFix, QTreeView):

    default_columns_visible = [
        "asctime",
        "levelname",
        "message",
    ]

    def __init__(self):
        super(QueryResultListWidget, self).__init__()
        self.field_config = dict()
        model = QueryResultListModel()
        self.setModel(model)
        self.setAlternatingRowColors(1)
        FontFixer.set_monospace_font(self)
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

    def toggle_column(self, i):
        def handler(toggled):
            self.header().setSectionHidden(i, not toggled)
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
            action.toggled.connect(self.toggle_column(i))
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
    item = list_widget.currentItem()
    item = QListWidgetItem("new query item", list_widget)
    item.setFlags(
        item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
    item.setCheckState(Qt.Checked)
    list_widget.editItem(item)


def run_query_handler(query_editor, query_results_view):
    def handler():
        model = query_results_view.model()
        model.beginResetModel()
        if not model.query_result:
            model.query_result = EsQueryResult()
        model.query_result.fetch()
        model.reset()
        model.endResetModel()
    return handler


def show_result_in_editor(rv, te):
    def handler(current, previous):
        data = rv.model().data(current, Qt.EditRole)
        te.setText(data)
    return handler


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    query_terms_view = QueryTermsWidget()
    query_results_view = QueryResultListWidget()
    query_result_view = QueryResultWidget()
    sp = window.centralWidget()

    query_results_view.selectionModel().currentChanged.connect(
        show_result_in_editor(query_results_view, query_result_view))
    window.run_query_shortcut.activated.connect(
        run_query_handler(query_terms_view, query_results_view))
    window.add_query_item_shortcut.activated.connect(
        lambda: add_query_item(query_terms_view))

    window.closeSignal.connect(
        lambda: settings.save_main_window(window))
    window.closeSignal.connect(
        lambda: settings.save_splitter(sp))
    window.closeSignal.connect(
        lambda: settings.save_query_results_view(query_results_view))

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

    settings.restore_main_window(window)
    settings.restore_splitter(sp)
    settings.restore_query_results_view(query_results_view)
    window.show()
    sys.exit(app.exec_())
