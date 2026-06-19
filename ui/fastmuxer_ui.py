from pathlib import Path
from PySide6.QtWidgets import QGridLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel, CardWidget, ComboBox, SubtitleLabel
)

from ui.main_ui import BasePage
from ui.other.path import FilePick, PathPick, to_one, to_paths


class FastMuxPage(BasePage):
    """MP4 快速封装页面：视频+音频+章节快速混流为 MP4"""

    def __init__(self) -> None:
        super().__init__("MP4快速封装", "tab_fast_mux")
        self._ui()

    def _ui(self):
        in_card = CardWidget()
        in_lay = QVBoxLayout(in_card)
        in_lay.setContentsMargins(16, 16, 16, 16)
        in_lay.setSpacing(12)
        in_lay.addWidget(SubtitleLabel("输入设置"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        
        self.vid_pick = FilePick("选择视频", "视频文件 (*.mp4 *.mkv *.avi *.ts);;所有文件 (*.*)")
        self.vid_pick.edit.setPlaceholderText("输入作为主轨道的视频文件")
        
        self.aud_pick = FilePick("选择音频", "音频文件 (*.m4a *.aac *.mp3 *.wav);;所有文件 (*.*)")
        self.aud_pick.edit.setPlaceholderText("混入此音频并忽略原视频音频")

        self.chap_pick = FilePick("选择章节", "文本文件 (*.txt);;所有文件 (*.*)")
        self.chap_pick.edit.setPlaceholderText("混入章节数据一起封装")
        
        grid.addWidget(BodyLabel("视频文件"), 0, 0)
        grid.addWidget(self.vid_pick, 0, 1)
        grid.addWidget(BodyLabel("音频文件"), 1, 0)
        grid.addWidget(self.aud_pick, 1, 1)
        grid.addWidget(BodyLabel("章节文件"), 2, 0)
        grid.addWidget(self.chap_pick, 2, 1)
        grid.setColumnStretch(1, 1)
        
        in_lay.addLayout(grid)
        self.cards.addWidget(in_card)

        out_card = CardWidget()
        out_lay = QVBoxLayout(out_card)
        out_lay.setContentsMargins(16, 16, 16, 16)
        out_lay.setSpacing(12)
        out_lay.addWidget(SubtitleLabel("输出设置"))
        
        out_grid = QGridLayout()
        out_grid.setHorizontalSpacing(12)
        out_grid.setVerticalSpacing(10)
        
        self.engine_combo = ComboBox()
        self.engine_combo.addItems(["mp4box", "ffmpeg"])
        self.engine_combo.setCurrentIndex(0)
        
        self.out_pick = PathPick(self.vid_pick.edit)
        self.vid_pick.edit.done.connect(self._auto_out)
        
        out_grid.addWidget(BodyLabel("混流工具"), 0, 0)
        out_grid.addWidget(self.engine_combo, 0, 1)
        out_grid.addWidget(BodyLabel("输出位置"), 1, 0)
        out_grid.addWidget(self.out_pick, 1, 1)
        out_grid.setColumnStretch(1, 1)

        out_lay.addLayout(out_grid)
        self.cards.addWidget(out_card)

    def _auto_out(self, text):
        paths = to_paths(text)
        if not paths or self.out_pick.edit.text().strip():
            return
        if len(paths) >= 1:
            self.out_pick.edit.setText(str(paths[0].with_name(f"{paths[0].stem}.mp4")))

    def get_job(self) -> tuple:
        """收集快速封装任务参数

        Returns:
            (任务类型, 参数字典) 或 (None, 错误信息字符串)
        """
        videos = to_paths(self.vid_pick.text())
        if not videos:
            return None, "请先提供有效的视频文件路径！"
        vp = str(videos[0])
            
        audios = to_paths(self.aud_pick.text())
        ap = str(audios[0]) if audios else None
        
        chaps = to_paths(self.chap_pick.text())
        cp = str(chaps[0]) if chaps else None
        
        out = to_one(self.out_pick.text())
        
        times, names = None, None
        if cp and Path(cp).exists():
            from core.tools.chapters import read_chap
            times, names = read_chap(cp)
        
        params = {
            "v_path": vp,
            "a_path": ap,
            "out_path": out if out else None,
            "mode": self.engine_combo.currentText(),
            "times_ms": times,
            "names": names
        }
        
        return "fast_mux", params
