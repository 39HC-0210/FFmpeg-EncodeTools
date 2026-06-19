import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QInputDialog, QMessageBox, QSplitter,
    QVBoxLayout, QWidget, QGridLayout,
)
from qfluentwidgets import (
    BodyLabel, CardWidget, ComboBox, DoubleSpinBox, FluentIcon,
    PrimaryPushButton, PushButton, SubtitleLabel, TextEdit,
    TitleLabel, InfoBar, InfoBarPosition,
)

from config import CFG_DIR
from core.vapoursynth.vs_script import check_vs
from ui.other.Python_code import CodeBox, CmdHL
from ui.other.path import DropEdit, PathPick, FilePick, to_one, to_paths
from utils import load_cfg, save_cfg


class VSPage(QWidget):
    """VapourSynth 压制页面：脚本编辑、语法检查、编码器配置、预设管理"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tab_vs_encode")
        self.source_path = ""
        self.preset_dir = CFG_DIR / "vs_presets"
        self.script_dir = CFG_DIR / "vs_scripts"
        self._ui()
        self._load_settings()
        self._load_default_script()


    def _ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(35, 14, 35, 28)
        lay.setSpacing(18)

        header = QHBoxLayout()
        title = TitleLabel("VapourSynth压制", self)
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._left())
        split.addWidget(self._right())
        split.setSizes([620, 300])
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, stretch=1)

    def _left(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        io_card = CardWidget()
        io_lay = QVBoxLayout(io_card)
        io_lay.setContentsMargins(16, 16, 16, 16)
        io_lay.setSpacing(12)
        io_lay.addWidget(SubtitleLabel("输入与输出"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        
        self.vid_pick = FilePick("选择视频", "视频文件 (*.mp4 *.mkv *.avi *.flv);;所有文件 (*.*)")
        self.vid_pick.edit.done.connect(self._auto_out)
        self.sub_pick = FilePick("选择字幕", "字幕文件 (*.ass *.srt *.ssa);;所有文件 (*.*)")
        self.font_pick = FilePick("选择字体文件夹", is_dir=True)
        self.out_pick = PathPick(self.vid_pick.edit)

        self.vid_pick.edit.textChanged.connect(lambda t: self._update_script_variable("src", t))
        self.sub_pick.edit.textChanged.connect(lambda t: self._update_script_variable("ass", t))
        self.font_pick.edit.textChanged.connect(lambda t: self._update_script_variable("font", t))

        grid.addWidget(BodyLabel("视频文件"), 0, 0)
        grid.addWidget(self.vid_pick, 0, 1)
        grid.addWidget(BodyLabel("字幕文件"), 1, 0)
        grid.addWidget(self.sub_pick, 1, 1)
        grid.addWidget(BodyLabel("字体文件"), 2, 0)
        grid.addWidget(self.font_pick, 2, 1)
        grid.addWidget(BodyLabel("输出位置"), 3, 0)
        grid.addWidget(self.out_pick, 3, 1)
        grid.setColumnStretch(1, 1)
        io_lay.addLayout(grid)
        lay.addWidget(io_card)

        vs_card = CardWidget()
        vs_lay = QVBoxLayout(vs_card)
        vs_lay.setContentsMargins(16, 16, 16, 16)
        vs_lay.setSpacing(10)

        vs_hdr_row = QHBoxLayout()
        vs_hdr_row.addWidget(SubtitleLabel("VS 脚本"))
        vs_hdr_row.addStretch()
        vs_lay.addLayout(vs_hdr_row)

        self.ed = CodeBox()
        self.ed.setMinimumHeight(220)
        vs_lay.addWidget(self.ed, stretch=1)



        script_ops_row = QHBoxLayout()
        script_ops_row.setSpacing(8)
        btn_save_scr = PushButton(FluentIcon.SAVE, "保存脚本")
        btn_save_scr.clicked.connect(self._save_script_to_file)
        btn_load_scr = PushButton(FluentIcon.FOLDER, "加载脚本")
        btn_load_scr.clicked.connect(self._load_script_from_file)
        btn_save_def = PrimaryPushButton(FluentIcon.SETTING, "保存为默认脚本")
        btn_save_def.clicked.connect(self._save_default_script)
        btn_save_def.setToolTip("将当前编辑的脚本保存为软件初始启动时的默认模板")
        btn_check = PushButton(FluentIcon.CODE, "语法检查")
        btn_check.clicked.connect(self._chk)

        script_ops_row.addWidget(btn_save_scr)
        script_ops_row.addWidget(btn_load_scr)
        script_ops_row.addWidget(btn_save_def)
        script_ops_row.addStretch()
        script_ops_row.addWidget(btn_check)
        vs_lay.addLayout(script_ops_row)

        lay.addWidget(vs_card, stretch=1)
        return panel

    def _right(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(6, 0, 0, 0)
        lay.setSpacing(8)

        card = CardWidget()
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(10)
        card_lay.addWidget(SubtitleLabel("编码器设置"))

        self.mode_box = ComboBox()
        self.mode_box.addItems(["x264 CLI", "x265 CLI", "FFmpeg libx264", "FFmpeg libx265"])
        self.mode_box.currentTextChanged.connect(self._sync_output_suffix)
        card_lay.addWidget(BodyLabel("编码模式"))
        card_lay.addWidget(self.mode_box)

        self.pre_box = ComboBox()
        self.pre_box.addItems([
            "ultrafast", "superfast", "veryfast", "faster", "fast",
            "medium", "slow", "slower", "veryslow", "placebo",
        ])
        self.pre_box.setCurrentText("slow")
        card_lay.addWidget(BodyLabel("Preset"))
        card_lay.addWidget(self.pre_box)

        self.crf_box = DoubleSpinBox()
        self.crf_box.setRange(0, 51)
        self.crf_box.setSingleStep(0.5)
        self.crf_box.setValue(18)
        card_lay.addWidget(BodyLabel("CRF"))
        card_lay.addWidget(self.crf_box)

        card_lay.addWidget(BodyLabel("详细编码器设置"))
        self.extra_box = TextEdit()
        self.extra_box.setPlaceholderText("例如：--aq-mode 2 --psy-rd 2.0 --keyint 240")
        self.extra_box.setFont(QFont("Consolas", 10))
        self.extra_hl = CmdHL(self.extra_box.document())
        card_lay.addWidget(self.extra_box, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_save_preset = PushButton(FluentIcon.SAVE, "保存预设")
        self.btn_save_preset.clicked.connect(self._save_preset)
        self.btn_load_preset = PushButton(FluentIcon.FOLDER, "读取预设")
        self.btn_load_preset.clicked.connect(self._load_preset)
        self.btn_save_settings = PrimaryPushButton(FluentIcon.SAVE, "保存为默认参数")
        self.btn_save_settings.clicked.connect(self._save_settings)
        btn_row.addWidget(self.btn_save_preset)
        btn_row.addWidget(self.btn_load_preset)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save_settings)
        card_lay.addLayout(btn_row)

        lay.addWidget(card, stretch=1)
        return panel

    def _auto_out(self, text):
        paths = to_paths(text)
        if paths and not self.out_pick.text().strip():
            self.out_pick.edit.setText(str(paths[0].with_suffix(self._target_suffix())))

    def _insert_script_line(self, text):
        cursor = self.ed.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        current = self.ed.toPlainText()
        prefix = "" if not current or current.endswith("\n") else "\n"
        cursor.insertText(prefix + text + "\n")
        self.ed.setTextCursor(cursor)

    def _target_suffix(self):
        text = self.mode_box.currentText()
        if "FFmpeg" in text:
            return ".mp4"
        if "x264" in text:
            return ".avc"
        return ".hevc"

    def _sync_output_suffix(self):
        suffix = self._target_suffix()
        raw = self.out_pick.text().strip()
        if raw:
            self.out_pick.edit.setText(str(Path(raw).with_suffix(suffix)))
        elif self.vid_pick.text().strip():
            self.out_pick.edit.setText(str(Path(self.vid_pick.text().strip()).with_suffix(suffix)))

    def _preset_data(self):
        return {
            "mode": self.mode_box.currentText(),
            "preset": self.pre_box.currentText(),
            "crf": self.crf_box.value(),
            "extra_args": self.extra_box.toPlainText().strip(),
        }

    def _apply_preset_data(self, data):
        if data.get("mode"):
            idx = self.mode_box.findText(str(data["mode"]))
            if idx >= 0:
                self.mode_box.setCurrentIndex(idx)
        if data.get("preset"):
            self.pre_box.setCurrentText(str(data["preset"]))
        if "crf" in data:
            self.crf_box.setValue(float(data["crf"]))
        self.extra_box.setPlainText(str(data.get("extra_args", "")))
        self._sync_output_suffix()

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "保存预设", "预设名称:")
        if not ok or not name.strip():
            return
        safe = re.sub(r'[\\/:*?"<>|]+', "_", name.strip())
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        path = self.preset_dir / f"{safe}.json"
        path.write_text(json.dumps(self._preset_data(), indent=2, ensure_ascii=False), encoding="utf-8")
        InfoBar.success("保存成功", f"预设已保存：{path.name}", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)

    def _load_preset(self):
        self.preset_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "读取预设", str(self.preset_dir), "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self._apply_preset_data(data)
            InfoBar.success("读取成功", Path(path).name, position=InfoBarPosition.TOP, parent=self.window(), duration=5000)
        except Exception as exc:
            QMessageBox.warning(self, "读取失败", str(exc))

    def _save_settings(self):
        cfg = load_cfg()
        cfg["vs_mode"] = self.mode_box.currentText()
        cfg["vs_preset"] = self.pre_box.currentText()
        cfg["vs_crf"] = self.crf_box.value()
        cfg["vs_extra_args"] = self.extra_box.toPlainText().strip()
        cfg["vs_output"] = self.out_pick.text().strip()
        save_cfg(cfg)
        InfoBar.success("保存成功", "默认参数已保存。", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)

    def _load_settings(self):
        cfg = load_cfg()
        mode = cfg.get("vs_mode")
        if mode:
            if "x264 CLI" in mode or ("x264" in mode and "CLI" in mode):
                mode = "x264 CLI"
            elif "x265 CLI" in mode or ("x265" in mode and "CLI" in mode):
                mode = "x265 CLI"
            elif "libx264" in mode:
                mode = "FFmpeg libx264"
            elif "libx265" in mode:
                mode = "FFmpeg libx265"
            idx = self.mode_box.findText(str(mode))
            if idx >= 0:
                self.mode_box.setCurrentIndex(idx)
        if cfg.get("vs_preset"):
            self.pre_box.setCurrentText(str(cfg["vs_preset"]))
        if "vs_crf" in cfg:
            self.crf_box.setValue(float(cfg["vs_crf"]))
        self.extra_box.setPlainText(str(cfg.get("vs_extra_args", "")))
        self.out_pick.edit.setText(str(cfg.get("vs_output", "")))
        self._sync_output_suffix()





    def _chk(self):
        code = self.ed.toPlainText()
        ok, err, full_output = check_vs(code)
        if ok:
            InfoBar.success("语法检查", "脚本语法正确", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)
        else:
            log_path = self._export_chk_log(code, err, full_output)
            if log_path:
                InfoBar.warning("语法检查", f"检测到错误，日志已保存: {log_path}", position=InfoBarPosition.TOP, parent=self.window(), duration=8000)
            else:
                InfoBar.warning("语法检查", f"检测到错误: {err}", position=InfoBarPosition.TOP, parent=self.window(), duration=8000)

    def _export_chk_log(self, code, short_err, full_output):
        if getattr(sys, 'frozen', False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path.cwd()
        log_path = app_dir / "log.txt"
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = (
            f"===== VS 语法检查错误日志 =====\n"
            f"时间: {ts}\n"
            f"错误摘要: {short_err}\n\n"
            f"--- 完整输出 ---\n{full_output}\n\n"
            f"--- 脚本内容 ---\n{code}\n"
        )
        try:
            log_path.write_text(content, encoding="utf-8")
            return str(log_path)
        except Exception:
            return None

    def get_job(self) -> tuple:
        """收集 VS 压制任务参数

        Returns:
            (任务类型, 参数字典) 或 (None, 错误信息字符串)
        """
        code = self.ed.toPlainText().strip()
        if not code:
            return None, "请输入 VS 脚本"
        out = to_one(self.out_pick.text())
        if not out:
            return None, "请指定输出文件路径"

        mode_text = self.mode_box.currentText()
        enc_params = {
            "preset": self.pre_box.currentText(),
            "crf": self.crf_box.value(),
            "extra_args": self.extra_box.toPlainText().strip(),
        }
        if mode_text == "x264 CLI":
            mode = "cli"
            enc = "x264"
        elif mode_text == "x265 CLI":
            mode = "cli"
            enc = "x265"
        elif mode_text == "FFmpeg libx264":
            mode = "ffmpeg"
            enc = "libx264"
        else:
            mode = "ffmpeg"
            enc = "libx265"

        try:
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".vpy", delete=False, encoding="utf-8")
            tmp.write(code)
            tmp.close()
        except Exception as exc:
            return None, f"无法写入临时脚本: {exc}"

        return "vs", {
            "_mode": mode,
            "scr": tmp.name,
            "out": str(Path(out).with_suffix(self._target_suffix())),
            "enc": enc,
            "enc_p": enc_params,
        }

    def _update_script_variable(self, var_name, value):
        # 原地正则查找并替换编辑器中指定变量（如 src、ass、font）的值，统一正斜杠路径
        text = self.ed.toPlainText()
        clean_value = str(value).strip(' "\'').replace('\\', '/')
        pattern = r'(' + var_name + r'\s*=\s*[rR]?(?P<q>"""|\'\'\'|["\']))([^\r\n]*)(?P=q)'
        replacement = rf'\g<1>{clean_value}\g<2>'
        new_text, count = re.subn(pattern, replacement, text)
        if count > 0:
            self.ed.setPlainText(new_text)
        else:
            self._insert_script_line(f'{var_name} = r"{clean_value}"')

    def _load_default_script(self):
        path = CFG_DIR / "default_script.vpy"
        code = ""
        if path.exists():
            try:
                code = path.read_text(encoding="utf-8")
            except Exception:
                pass

        if not code:
            code = (
                "import vapoursynth as vs\n"
                "from vapoursynth import core\n"
                "# Input\n"
                "src = r\"\"\n"
                "clip = core.lsmas.LWLibavSource(src)\n"
                "# Subtitle\n"
                "ass = r\"\"\n"
                "font = r\"\"\n"
                "if ass:\n"
                "    clip = core.assrender.TextSub(clip, ass, fontdir=font) if font else core.assrender.TextSub(clip, ass)\n"
                "# Output\n"
                "clip.set_output(0)\n"
            )
        self.ed.setPlainText(code)
        
        if self.vid_pick.text().strip():
            self._update_script_variable("src", self.vid_pick.text().strip())
        if self.sub_pick.text().strip():
            self._update_script_variable("ass", self.sub_pick.text().strip())
        if self.font_pick.text().strip():
            self._update_script_variable("font", self.font_pick.text().strip())

    def _save_default_script(self):
        code = self.ed.toPlainText()
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        path = CFG_DIR / "default_script.vpy"
        try:
            path.write_text(code, encoding="utf-8")
            InfoBar.success("保存成功", "当前脚本已存为默认启动脚本。", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def _save_script_to_file(self):
        self.script_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "保存 VapourSynth 脚本", str(self.script_dir), "VapourSynth Script (*.vpy);;所有文件 (*.*)")
        if not path:
            return
        try:
            Path(path).write_text(self.ed.toPlainText(), encoding="utf-8")
            InfoBar.success("保存成功", f"脚本已写入：{Path(path).name}", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def _load_script_from_file(self):
        self.script_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "加载 VapourSynth 脚本", str(self.script_dir), "VapourSynth Script (*.vpy);;所有文件 (*.*)")
        if not path:
            return
        try:
            self.ed.setPlainText(Path(path).read_text(encoding="utf-8"))
            InfoBar.success("加载成功", f"脚本已载入：{Path(path).name}", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)
        except Exception as exc:
            QMessageBox.warning(self, "加载失败", str(exc))
