#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from collections import OrderedDict
from model import QueryResultListModel
import settings
import elasticsearch


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
        FontFixer.set_monospace_font(self)

        model = QueryResultListModel()
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


class QueryEditor(QPlainTextEdit):

    def __init__(self):
        super(QueryEditor, self).__init__()
        FontFixer.set_monospace_font(self)


class ResultDetailWidget(QPlainTextEdit):

    def __init__(self):
        super(ResultDetailWidget, self).__init__()
        self.setReadOnly(True)
        FontFixer.set_monospace_font(self)


def run_query_handler(query_editor, model, es_service):
    def handler():
        query_text = unicode(query_editor.toPlainText())
        query = elasticsearch.Query(query_text)
        model.update_result(es_service.query(query))
    return handler


def update_result_details(results_model, detail_widget):
    def handler(current, previous):
        data = results_model.data(current, Qt.EditRole)
        detail_widget.setPlainText(data)
    return handler


if __name__ == '__main__':
    app = QApplication(sys.argv)

    es_service = elasticsearch.Service("http://localhost:9200/")

    window = MainWindow()
    query_editor = QueryEditor()
    query_results = ResultsWidget()
    results_list = query_results.list_view
    result_detail_view = ResultDetailWidget()
    sp = window.centralWidget()

    results_list.selectionModel().currentChanged.connect(
        update_result_details(
            results_list.model(), result_detail_view
        )
    )

    window.run_query_shortcut.activated.connect(
        run_query_handler(query_editor, results_list.model(), es_service)
    )

    window.closeSignal.connect(lambda:(
        settings.save_main_window(window),
        settings.save_splitter(sp),
        settings.save_query_results_view(results_list),
        settings.save_last_query(query_editor),
    ))

    sp.addWidget(query_editor)
    sp.addWidget(query_results)
    sp.addWidget(result_detail_view)
    sp.setCollapsible(0, False)
    sp.setCollapsible(1, False)
    sp.setCollapsible(2, False)
    sp.setStretchFactor(0, 0)
    sp.setStretchFactor(1, 10)
    sp.setStretchFactor(2, 2)
    sp.setSizes([50, 300, 100])

    settings.restore_main_window(window)
    settings.restore_splitter(sp)
    settings.restore_query_results_view(results_list)
    settings.restore_last_query(query_editor)

    window.show()
    sys.exit(app.exec_())
