import os
import shlex
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QWidget
from qfluentwidgets import LineEdit, PushButton


def to_paths(text: str) -> list[Path]:
    """将空格分隔/引号包裹的路径字符串解析为 Path 列表

    Args:
        text: 可能包含多个路径的字符串（空格或引号分隔）

    Returns:
        存在的 Path 对象列表
    """
    try:
        ps = []
        for t in shlex.split(text.strip(), posix=(os.name != 'nt')):
            p = Path(t.strip(' "'))
            if p.exists():
                ps.append(p)
        return ps
    except Exception:
        return []


def to_one(text: str) -> str | None:
    """提取单一路径字符串，去除首尾引号与空格"""
    raw = text.strip(' "')
    return raw if raw else None


class DropEdit(LineEdit):
    """支持拖放文件的单行输入框

    拖入文件时自动填入路径（含空格则自动加引号）
    """

    done = Signal(str)

    def __init__(self, replace: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._rep = replace
        self.textChanged.connect(self._on_change)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e: QDropEvent) -> None:
        """拖放文件时填入路径，含空格自动加引号"""
        urls = e.mimeData().urls()
        if urls:
            p = urls[0].toLocalFile()
            txt = f'"{p}"' if " " in p else p
            self.setText(txt)
        e.acceptProposedAction()

    def _on_change(self, text: str) -> None:
        self.done.emit(text)


class PathPick(QWidget):
    """输出路径选择组件

    组合了输入框、浏览按钮和"同输入源"同步按钮
    """

    def __init__(self, src_input: DropEdit | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.src = src_input
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(8)

        self.edit = DropEdit(replace=True)
        self.edit.setPlaceholderText("留空则使用输入路径")

        self.btn_b = PushButton("选择位置")
        self.btn_b.clicked.connect(self._browse)
        self.btn_s = PushButton("同输入源")
        self.btn_s.clicked.connect(self._sync)

        self.lay.addWidget(self.edit)
        self.lay.addWidget(self.btn_b)
        self.lay.addWidget(self.btn_s)

    def _browse(self) -> None:
        """弹出文件保存对话框选择输出位置"""
        dp = ""
        if self.src:
            ps = to_paths(self.src.text())
            if ps:
                dp = str(ps[0])
        p, _ = QFileDialog.getSaveFileName(self, "选择输出位置", dp, "所有文件 (*)")
        if p:
            self.edit.setText(p)

    def _sync(self) -> None:
        """将输出路径同步为输入源的父目录"""
        if self.src:
            ps = to_paths(self.src.text())
            if ps:
                self.edit.setText(str(ps[0].parent))

    def text(self) -> str:
        """返回当前输出路径文本"""
        return self.edit.text()


class FilePick(QWidget):
    """文件/目录选择组件，组合了输入框和选择按钮

    Attributes:
        edit: 内部的 DropEdit 实例，可监听其 ``done`` 信号
    """

    def __init__(
        self,
        title: str,
        filter_str: str = "所有文件 (*.*)",
        is_dir: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.filter = filter_str
        self.is_dir = is_dir
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(8)

        self.edit = DropEdit(replace=True)
        self.btn = PushButton(title)
        self.btn.clicked.connect(self._pick)

        self.lay.addWidget(self.edit)
        self.lay.addWidget(self.btn)

    def _pick(self) -> None:
        """弹出文件或目录选择对话框"""
        if self.is_dir:
            path = QFileDialog.getExistingDirectory(self, self.btn.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, self.btn.text(), "", self.filter)
        if path:
            txt = f'"{path}"'
            self.edit.setText(txt)

    def text(self) -> str:
        """返回当前输入文本"""
        return self.edit.text()

    def setText(self, text: str) -> None:
        """设置输入文本"""
        self.edit.setText(text)
