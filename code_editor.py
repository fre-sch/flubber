# -*- coding: UTF-8 -*-
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class LineNumberArea(QWidget):

    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.setObjectName("LineNumberArea")
        self.fontMetrics = self.editor.fontMetrics()
        self.font_width =  self.fontMetrics.width("9")
        self.font_height = self.fontMetrics.height()
        self.editor.blockCountChanged.connect(
            self.update_editor_margins)
        self.editor.updateRequest.connect(self.on_editor_update)
        self.update_editor_margins()

    @property
    def editor(self):
        return self.parentWidget()

    def sizeHint(self):
        return QSize(self.calcWidth(), 0)

    def calcWidth(self):
        digits = 1
        max_blocks = max(1, self.editor.blockCount())
        while max_blocks >= 10:
            max_blocks /= 10
            digits += 1

        space = 3 + self.font_width * digits
        return space

    def update_editor_margins(self):
        self.editor.setViewportMargins(self.calcWidth(), 0, 0, 0)

    def on_editor_update(self, rect, dy):
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

        if rect.contains(self.editor.viewport().rect()):
            self.update_editor_margins()

    def on_editor_resize(self):
        cr = self.editor.contentsRect()
        self.setGeometry(
            QRect(cr.left(), cr.top(), self.calcWidth(), cr.height())
        )

    def paintEvent(self, event):
        style_opts = QStyleOption()
        style_opts.initFrom(self)
        event_rect = event.rect()
        palette = self.style().standardPalette()
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PE_Widget, style_opts, painter, self)

        block = self.editor.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()
        while block.isValid() and top <= event_rect.bottom():
            if block.isVisible() and bottom >= event_rect.top():
                number = str(blockNumber + 1)
                self.style().drawItemText(painter,
                    QRect(0, top, self.width(), self.font_height),
                    Qt.AlignRight, palette, True,
                    number
                )
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            blockNumber += 1


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super(CodeEditor, self).__init__(parent)
        self.line_number_area = LineNumberArea(self)

    def resizeEvent(self, event):
        super(CodeEditor, self).resizeEvent(event)
        self.line_number_area.on_editor_resize()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = QMainWindow()
    editor = CodeEditor()
    window.setCentralWidget(editor)
    window.show()
    sys.exit(app.exec_())
