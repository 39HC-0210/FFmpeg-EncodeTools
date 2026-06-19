import re
from PySide6.QtCore import QObject, Qt, QRect, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit, QWidget
from ui.theme import DARK_BORDER, DARK_FIELD, DARK_PANEL, DARK_SELECTION, DARK_TEXT, DARK_MUTED


class LineBar(QWidget):
    """代码编辑器左侧行号栏"""

    def __init__(self, editor: "CodeBox"):
        super().__init__(editor)
        self.ed = editor

    def sizeHint(self) -> QSize:
        return QSize(self.ed.line_bar_w(), 0)

    def paintEvent(self, event) -> None:
        self.ed.line_bar_draw(event)


class PyHL(QSyntaxHighlighter):
    """Python 语法高亮器"""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)  # pyright: ignore[reportArgumentType, reportCallIssue]
        self.rules = []

        kw = QTextCharFormat()
        kw.setForeground(QColor("#569CD6"))
        kw.setFontWeight(QFont.Weight.Bold)
        for w in ["import","from","as","def","class","return",
                  "if","else","elif","for","while","try","except",
                  "finally","with","pass","True","False","None",
                  "and","or","not","in","is","lambda","yield"]:
            self.rules.append((rf"\b{w}\b", kw))

        s = QTextCharFormat()
        s.setForeground(QColor("#CE9178"))
        self.rules.append((r'"[^"]*"', s))
        self.rules.append((r"'[^']*'", s))

        c = QTextCharFormat()
        c.setForeground(QColor("#6A9955"))
        self.rules.append((r"#.*$", c))

        n = QTextCharFormat()
        n.setForeground(QColor("#B5CEA8"))
        self.rules.append((r"\b\d+\.?\d*\b", n))

        f = QTextCharFormat()
        f.setForeground(QColor("#DCDCAA"))
        self.rules.append((r"\b\w+(?=\()", f))

        vs = QTextCharFormat()
        vs.setForeground(QColor("#4EC9B0"))
        self.rules.append((r"\bvapoursynth\b", vs))

    def highlightBlock(self, text: str) -> None:
        for pat, fmt in self.rules:
            for m in re.finditer(pat, text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class CmdHL(QSyntaxHighlighter):
    """命令行参数语法高亮器

    高亮 ``--flag`` 选项、数字和字符串
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)  # pyright: ignore[reportArgumentType, reportCallIssue]
        self.rules = []

        opt = QTextCharFormat()
        opt.setForeground(QColor("#569CD6"))
        opt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((r"-[a-zA-Z0-9_-]+|--[a-zA-Z0-9_-]+", opt))

        num = QTextCharFormat()
        num.setForeground(QColor("#B5CEA8"))
        self.rules.append((r"\b\d+\.?\d*\b", num))

        string = QTextCharFormat()
        string.setForeground(QColor("#CE9178"))
        self.rules.append((r'"[^"]*"', string))
        self.rules.append((r"'[^']*'", string))

    def highlightBlock(self, text: str) -> None:
        for pat, fmt in self.rules:
            for m in re.finditer(pat, text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class CodeBox(QPlainTextEdit):
    """带行号栏和 Python 语法高亮的代码编辑器"""

    changed = Signal()

    STYLE = """
        QPlainTextEdit {
            background-color: %s; color: %s;
            border: 1px solid %s; border-radius: 6px;
            selection-background-color: %s;
            padding: 6px;
        }
    """ % (DARK_FIELD, DARK_TEXT, DARK_BORDER, DARK_SELECTION)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.bar = LineBar(self)
        self.setFont(QFont("Consolas", 11))
        self.setTabStopDistance(32)
        self.hl = PyHL(self.document())
        self.blockCountChanged.connect(self._up_w)
        self.updateRequest.connect(self._up_area)
        self.textChanged.connect(self.changed.emit)
        self.setStyleSheet(self.STYLE)

    def line_bar_w(self) -> int:
        """根据当前行数计算行号栏所需宽度"""
        n = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * (n + 1)

    def _up_w(self) -> None:
        self.setViewportMargins(self.line_bar_w(), 0, 0, 0)

    def _up_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.bar.scroll(0, dy)
        else:
            self.bar.update(0, rect.y(), self.bar.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._up_w()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.bar.setGeometry(QRect(cr.left(), cr.top(), self.line_bar_w(), cr.height()))

    def line_bar_draw(self, event) -> None:
        """绘制行号栏内容（行号数字）"""
        p = QPainter(self.bar)
        p.fillRect(event.rect(), QColor(DARK_PANEL))

        blk = self.firstVisibleBlock()
        num = blk.blockNumber()
        top = int(self.blockBoundingGeometry(blk).translated(self.contentOffset()).top())
        bot = top + int(self.blockBoundingRect(blk).height())

        while blk.isValid() and top <= event.rect().bottom():
            if blk.isVisible() and bot >= event.rect().top():
                p.setPen(QColor(DARK_MUTED))
                p.drawText(0, top, self.bar.width() - 5,
                           self.fontMetrics().height(),
                           Qt.AlignmentFlag.AlignRight, str(num + 1))
            blk = blk.next()
            top = bot
            bot = top + int(self.blockBoundingRect(blk).height()) if blk.isValid() else top
            num += 1
