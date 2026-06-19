from pathlib import Path
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    CardWidget, SubtitleLabel, RadioButton, PushButton, FluentIcon, BodyLabel
)

from core.tools.chapters import read_chap
from ui.main_ui import BasePage, ChapDialog
from ui.other.path import DropEdit, PathPick, to_one, to_paths


class ChapPage(BasePage):
    """章节封装页面：导入章节 TXT 文件或手动编辑，注入到视频"""

    def __init__(self) -> None:
        super().__init__("章节封装", "tab_chapter")
        self._chaps = []

        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        lay.addWidget(SubtitleLabel("选择并封装章节文件"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.v_in = DropEdit(replace=True)
        self.v_in.done.connect(self._auto_out)
        self.out_pick = PathPick(self.v_in)
        self.rb_file = RadioButton("导入 TXT")
        self.rb_file.setChecked(True)
        self.chap_in = DropEdit(replace=True)
        self.rb_man = RadioButton("手动编辑")
        self.btn_edit = PushButton(FluentIcon.EDIT, "编辑")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._open)
        self.lbl_cnt = BodyLabel("0 行")
        self.rb_man.toggled.connect(self._mode)

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.rb_man)
        manual_row.addWidget(self.btn_edit)
        manual_row.addWidget(self.lbl_cnt)
        manual_row.addStretch()

        grid.addWidget(BodyLabel("视频文件"), 0, 0)
        grid.addWidget(self.v_in, 0, 1)
        grid.addWidget(BodyLabel("输出位置"), 1, 0)
        grid.addWidget(self.out_pick, 1, 1)
        grid.addWidget(self.rb_file, 2, 0)
        grid.addWidget(self.chap_in, 2, 1)
        grid.addLayout(manual_row, 3, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        self.cards.addWidget(card)

    def _auto_out(self, text):
        paths = to_paths(text)
        if paths and not self.out_pick.edit.text().strip():
            self.out_pick.edit.setText(str(paths[0].with_name(f"{paths[0].stem}_chapter.mp4")))

    def _mode(self):
        manual = self.rb_man.isChecked()
        self.chap_in.setEnabled(not manual)
        self.btn_edit.setEnabled(manual)

    def _open(self):
        dialog = ChapDialog(self, self._chaps)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._chaps = dialog.get()
            self.lbl_cnt.setText(f"{len(self._chaps)} 行")

    def get_job(self) -> tuple:
        """收集章节注入任务参数

        Returns:
            (任务类型, 参数字典) 或 (None, 错误信息字符串)
        """
        video = to_one(self.v_in.text())
        if not video:
            return None, "请选择视频文件。"

        times, names = [], []
        if self.rb_file.isChecked():
            chap = to_one(self.chap_in.text())
            if chap:
                chap_path = Path(chap)
                if chap_path.exists():
                    times, names = read_chap(str(chap_path))
        else:
            for item in self._chaps:
                text = item.get("time", "")
                if not text:
                    continue
                try:
                    parts = text.replace(".", ":").split(":")
                    ms = int(parts[0]) * 3600000 + int(parts[1]) * 60000 + int(parts[2]) * 1000 + int(parts[3] if len(parts) > 3 else 0)
                    times.append(ms)
                    names.append(item.get("name", ""))
                except (IndexError, ValueError):
                    pass

        return "chapter", {
            "v_path": video,
            "times_ms": times,
            "names": names,
            "out_path": to_one(self.out_pick.text()),
        }
