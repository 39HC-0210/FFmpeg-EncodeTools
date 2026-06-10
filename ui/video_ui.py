import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, CardWidget, CheckBox, ComboBox, DoubleSpinBox, FluentIcon,
    PushButton, SubtitleLabel,
)

from core.tools.encoder import EncBook
from ui.main_ui import BasePage
from ui.other.path import DropEdit, PathPick, to_one, to_paths, FilePick
from ui.other.ui_widgets import WidgetMaker
from ui.theme import polish_theme_widgets
from utils import bind_cfg, load_cfg, set_cfg, find_exe
from utils.keep import get_ffcap


class EncodePage(BasePage):
    """视频压制页面：编码器选择、CRF/Preset、像素格式、缩放、字幕烧入、音频重编码"""

    def __init__(self) -> None:
        super().__init__("视频压制", "tab_encode")
        self._w = {}
        self._crf_connected = False
        self._pre_connected = False
        self._io()
        self._video()
        self._audio()
        self._adv()
        self._load_enc_list()
        self._load_aud_enc_list()

    def _io(self):
        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        lay.addWidget(SubtitleLabel("输入与输出"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.vid_pick = FilePick("选择视频", "视频文件 (*.mp4 *.mkv);;所有文件 (*.*)")
        self.vid_pick.edit.done.connect(self._auto_out)
        self.sub_pick = FilePick("选择字幕", "字幕文件 (*.ass *.srt);;所有文件 (*.*)")
        self.font_pick = FilePick("选择字体文件夹", is_dir=True)
        self.out_pick = PathPick(self.vid_pick.edit)
        grid.addWidget(BodyLabel("视频文件"), 0, 0)
        grid.addWidget(self.vid_pick, 0, 1)
        grid.addWidget(BodyLabel("字幕文件"), 1, 0)
        grid.addWidget(self.sub_pick, 1, 1)
        grid.addWidget(BodyLabel("字体文件"), 2, 0)
        grid.addWidget(self.font_pick, 2, 1)
        grid.addWidget(BodyLabel("输出位置"), 3, 0)
        grid.addWidget(self.out_pick, 3, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        self.cards.addWidget(card)

    def _video(self):
        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        lay.addWidget(SubtitleLabel("视频参数"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.enc_box = ComboBox()
        self.enc_box.currentIndexChanged.connect(self._on_enc)

        self.crf_box = DoubleSpinBox()
        self.pre_box = ComboBox()

        self.pix_box = ComboBox()
        self.pix_box.addItem("YUV420P 8-bit", userData="yuv420p")
        self.pix_box.addItem("YUV420P10 10-bit", userData="yuv420p10le")
        self.pix_box.addItem("YUV444P 8-bit", userData="yuv444p")
        self.pix_box.addItem("YUV444P10 10-bit", userData="yuv444p10le")
        bind_cfg(self.pix_box, "v_pix", "YUV420P 8-bit")

        self.res_box = ComboBox()
        self.res_box.addItems(["保留原始分辨率", "缩放至 2160P (4K)", "缩放至 1440P (2K)", "缩放至 1080P", "缩放至 720P", "缩放至 540P"])
        bind_cfg(self.res_box, "v_res", "保留原始分辨率")

        self.crf_label = BodyLabel("CRF")
        self.pre_label = BodyLabel("Preset")
        grid.addWidget(BodyLabel("编码器"), 0, 0)
        grid.addWidget(self.enc_box, 0, 1)
        grid.addWidget(self.crf_label, 0, 2)
        grid.addWidget(self.crf_box, 0, 3)
        grid.addWidget(self.pre_label, 0, 4)
        grid.addWidget(self.pre_box, 0, 5)
        
        grid.addWidget(BodyLabel("像素格式"), 1, 0)
        grid.addWidget(self.pix_box, 1, 1)
        grid.addWidget(BodyLabel("分辨率"), 1, 2)
        grid.addWidget(self.res_box, 1, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(5, 1)
        lay.addLayout(grid)
        self.cards.addWidget(card)

    def _audio(self):
        card = CardWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(SubtitleLabel("音频参数"))

        row = QHBoxLayout()
        row.setSpacing(12)
        
        self.chk_a = CheckBox("重新编码音频")
        bind_cfg(self.chk_a, "a_ok", False)
        row.addWidget(self.chk_a)

        self.aud_body = QWidget()
        aud_lay = QHBoxLayout(self.aud_body)
        aud_lay.setContentsMargins(0, 0, 0, 0)
        aud_lay.setSpacing(8)

        self.a_enc = ComboBox()
        self.a_bit = ComboBox()
        self.a_bit.addItems([
            "32k", "40k", "48k", "56k", "64k", "80k", "96k", "112k", "128k", 
            "160k", "192k", "224k", "256k", "320k", "384k", "448k", "512k", 
            "576k", "640k", "无损"
        ])
        bind_cfg(self.a_bit, "a_bit", "192k")
        self.a_sr = ComboBox()
        self.a_sr.addItems([
            "保持原始采样率",
            "96000 Hz",
            "88200 Hz",
            "48000 Hz",
            "44100 Hz",
            "32000 Hz",
            "24000 Hz",
            "22050 Hz",
            "16000 Hz",
            "12000 Hz",
            "11025 Hz",
            "8000 Hz"
        ])
        bind_cfg(self.a_sr, "a_sr", "保持原始采样率")

        aud_lay.addWidget(BodyLabel("编码器"))
        aud_lay.addWidget(self.a_enc)
        aud_lay.addWidget(BodyLabel("比特率"))
        aud_lay.addWidget(self.a_bit)
        aud_lay.addWidget(BodyLabel("采样率"))
        aud_lay.addWidget(self.a_sr)

        row.addWidget(self.aud_body)
        row.addStretch()

        self.chk_a.toggled.connect(self.aud_body.setEnabled)
        self.aud_body.setEnabled(self.chk_a.isChecked())
        
        lay.addLayout(row)
        self.cards.addWidget(card)

    def _adv(self):
        self.a_card = CardWidget()
        lay = QVBoxLayout(self.a_card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.chk_adv = CheckBox("启用高级压制")
        bind_cfg(self.chk_adv, "adv_ok", False)
        header.addWidget(self.chk_adv)
        
        self.adv_btn = PushButton(FluentIcon.DOWN, "展开高级设置")
        self.adv_btn.clicked.connect(self._toggle_adv)
        header.addWidget(self.adv_btn)
        
        header.addStretch()
        self.btn_reset_adv = PushButton(FluentIcon.SYNC, "重置高级压制设置")
        self.btn_reset_adv.clicked.connect(self._reset_adv)
        header.addWidget(self.btn_reset_adv)
        lay.addLayout(header)

        self.adv_body = QWidget()
        self.adv_layout = QVBoxLayout(self.adv_body)
        self.adv_layout.setContentsMargins(0, 0, 0, 0)
        self.adv_layout.setSpacing(12)
        
        self.chk_adv.toggled.connect(self.adv_body.setEnabled)
        self.adv_body.setEnabled(self.chk_adv.isChecked())
        self.adv_body.hide()
        self.adv_open = False

        lay.addWidget(self.adv_body)
        self.cards.addWidget(self.a_card)

    def _toggle_adv(self):
        self.adv_open = not self.adv_open
        self.adv_body.setVisible(self.adv_open)
        self.adv_btn.setText("收起高级设置" if self.adv_open else "展开高级设置")
        self.adv_btn.setIcon(FluentIcon.UP if self.adv_open else FluentIcon.DOWN)
        if self.adv_open and not self._w:
            self._build_adv()

    def _reset_adv(self):
        for key, (widget, getter, param) in self._w.items():
            if param.w_type in ["float_spin", "int_spin"] and hasattr(widget, "setValue"):
                widget.setValue(param.default)
            elif param.w_type == "combo" and hasattr(widget, "setCurrentText"):
                widget.setCurrentText(str(param.default))
            elif param.w_type == "check" and hasattr(widget, "setChecked"):
                widget.setChecked(bool(param.default))
            elif param.w_type == "text" and hasattr(widget, "setText"):
                widget.setText(str(param.default))

    def _build_adv(self):
        for i in reversed(range(self.adv_layout.count())):
            item = self.adv_layout.itemAt(i)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
        self._w.clear()

        enc = self._enc_name()
        info = EncBook().get(enc)
        if not info or not info.groups:
            label = BodyLabel("该编码器没有高级可调参数。")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.adv_layout.addWidget(label)
            return

        for group in info.groups:
            params = [p for p in group.params if p.key not in {"crf", "preset"}]
            if not params:
                continue
            card = CardWidget()
            lay = QVBoxLayout(card)
            lay.setContentsMargins(14, 14, 14, 14)
            lay.setSpacing(10)
            lay.addWidget(SubtitleLabel(group.label))

            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(8)
            for row, param in enumerate(params):
                label, widget, getter = WidgetMaker.make_row(param)
                tip = param.tip or f"{param.label} ({param.key})"
                label.setToolTip(tip)
                widget.setToolTip(tip)
                self._w[param.key] = (widget, getter, param)
                grid.addWidget(label, row, 0, alignment=Qt.AlignmentFlag.AlignLeft)
                grid.addWidget(widget, row, 1)
            grid.setColumnStretch(1, 1)
            lay.addLayout(grid)
            self.adv_layout.addWidget(card)

        self.adv_layout.addStretch()
        polish_theme_widgets(self)

    def _enc_name(self):
        data = self.enc_box.currentData()
        if data:
            return data
        text = self.enc_box.currentText().strip()
        if text.startswith("──"):
            return "libx264"
        return text

    def _on_enc(self, _idx):
        self._update_video_params()
        if self.adv_open:
            self._build_adv()
        else:
            self._w.clear()

    def _update_video_params(self):
        enc = self._enc_name()
        info = EncBook().get(enc)
        if not info:
            return

        crf_param = None
        preset_param = None
        for group in info.groups:
            for p in group.params:
                if p.key == "crf" or p.key == "qscale":
                    crf_param = p
                elif p.key == "preset":
                    preset_param = p

        if self._crf_connected:
            self.crf_box.valueChanged.disconnect()
            self._crf_connected = False
        if self._pre_connected:
            self.pre_box.currentTextChanged.disconnect()
            self._pre_connected = False

        self.crf_box.blockSignals(True)
        self.pre_box.blockSignals(True)

        if crf_param:
            self.crf_label.setText(crf_param.label)
            self.crf_label.show()
            self.crf_box.show()
            
            if crf_param.w_type == "float_spin":
                self.crf_box.setDecimals(1)
            else:
                self.crf_box.setDecimals(0)
                
            if crf_param.rng:
                self.crf_box.setRange(crf_param.rng[0], crf_param.rng[1])
            self.crf_box.setSingleStep(crf_param.step)
            
            cfg = load_cfg()
            val = cfg.get(f"v_crf_{enc}")
            if val is None:
                if enc in ["libx264", "libx265"]:
                    val = cfg.get("v_crf", crf_param.default)
                else:
                    val = crf_param.default
            self.crf_box.setValue(float(val))
            
            self.crf_box.valueChanged.connect(lambda v: set_cfg(f"v_crf_{enc}", v))
            self._crf_connected = True
        else:
            self.crf_label.hide()
            self.crf_box.hide()

        if preset_param:
            self.pre_label.setText(preset_param.label)
            self.pre_label.show()
            self.pre_box.show()
            self.pre_box.clear()
            if preset_param.opts:
                self.pre_box.addItems(preset_param.opts)
            
            cfg = load_cfg()
            val = cfg.get(f"v_pre_{enc}")
            if val is None:
                if enc in ["libx264", "libx265"]:
                    val = cfg.get("v_pre", preset_param.default)
                else:
                    val = preset_param.default
            
            idx = self.pre_box.findText(str(val))
            if idx >= 0:
                self.pre_box.setCurrentIndex(idx)
            else:
                self.pre_box.setCurrentIndex(0)
                set_cfg(f"v_pre_{enc}", self.pre_box.currentText())
                
            self.pre_box.currentTextChanged.connect(lambda t: set_cfg(f"v_pre_{enc}", t))
            self._pre_connected = True
        else:
            self.pre_label.hide()
            self.pre_box.hide()

        self.crf_box.blockSignals(False)
        self.pre_box.blockSignals(False)

    def _load_enc_list(self):
        self.enc_box.blockSignals(True)
        self.enc_box.clear()
        cap = get_ffcap(find_exe("ffmpeg") or "ffmpeg")
        book = EncBook()
        saved = load_cfg().get("v_enc", "libx264")
        target = 0
        
        for name in ["libx264", "libx265", "libsvtav1"]:
            if cap.has(name) and (info := book.get(name)):
                self.enc_box.addItem(info.show_name, userData=name)
                if name == saved:
                    target = self.enc_box.count() - 1
                    
        if self.enc_box.count() == 0:
            x264 = book.get('libx264')
            x265 = book.get('libx265')
            av1 = book.get('libsvtav1')
            assert x264 and x265 and av1
            self.enc_box.addItem(x264.show_name, userData="libx264")
            self.enc_box.addItem(x265.show_name, userData="libx265")
            self.enc_box.addItem(av1.show_name, userData="libsvtav1")
            target = 0
            
        self.enc_box.blockSignals(False)
        self.enc_box.setCurrentIndex(target)
        self.enc_box.currentIndexChanged.connect(lambda: set_cfg("v_enc", self._enc_name()))
        self._update_video_params()

    def _load_aud_enc_list(self):
        self.a_enc.blockSignals(True)
        self.a_enc.clear()
        cap = get_ffcap(find_exe("ffmpeg") or "ffmpeg")
        cands = [
            ("aac", "aac"),
            ("libopus", "libopus"),
            ("libmp3lame", "libmp3lame"),
            ("ac3", "ac3"),
            ("eac3", "eac3"),
            ("flac", "flac"),
        ]
        avail = [name for name, _ in cands if cap.has(name)]
        if not avail:
            avail = ["aac", "flac"]
            
        for name in avail:
            self.a_enc.addItem(name, userData=name)
            
        saved = load_cfg().get("a_enc", "aac")
        target = self.a_enc.findText(saved)
        if target < 0:
            target = 0
        self.a_enc.setCurrentIndex(target)
        self.a_enc.blockSignals(False)
        self.a_enc.currentIndexChanged.connect(lambda: set_cfg("a_enc", self.a_enc.currentText()))
        self.a_enc.currentTextChanged.connect(self._on_aud_enc_changed)
        self._on_aud_enc_changed()

    def _on_aud_enc_changed(self):
        enc = self.a_enc.currentText()
        if enc == "flac":
            self.a_bit.setCurrentText("无损")
            self.a_bit.setEnabled(False)
        else:
            self.a_bit.setEnabled(True)
            if self.a_bit.currentText() == "无损":
                self.a_bit.setCurrentText("192k")

    def _auto_out(self, text):
        paths = to_paths(text)
        if not paths or self.out_pick.edit.text().strip():
            return
        if len(paths) == 1:
            self.out_pick.edit.setText(str(paths[0].with_name(f"{paths[0].stem}_output.mp4")))
        else:
            self.out_pick.edit.setText(str(paths[0].parent))

    def get_job(self) -> tuple:
        """收集当前页面的压制任务参数

        Returns:
            (任务类型, 参数字典) 或 (None, 错误信息字符串)
        """
        videos = to_paths(self.vid_pick.text())
        if not videos:
            return None, "请选择视频文件。"

        audio = {
            "ok": self.chk_a.isChecked(),
            "enc": self.a_enc.currentText(),
            "bitrate": self.a_bit.currentText(),
        }
        
        ar_text = self.a_sr.currentText()
        m = re.search(r"\d+", ar_text)
        if m:
            audio["ar"] = m.group(0)

        ext = {}
        if self.chk_adv.isChecked():
            for key, (widget, getter, param_def) in self._w.items():
                value = getter()
                if value != param_def.default:
                    ext[key] = value

        res_text = self.res_box.currentText()
        scale_param = None
        if "2160" in res_text:
            scale_param = "-2:2160"
        elif "1440" in res_text:
            scale_param = "-2:1440"
        elif "1080" in res_text:
            scale_param = "-2:1080"
        elif "720" in res_text:
            scale_param = "-2:720"
        elif "540" in res_text:
            scale_param = "-2:540"

        return "encode", {
            "vid_list": videos,
            "enc_name": self._enc_name(),
            "crf": self.crf_box.value(),
            "preset": self.pre_box.currentText(),
            "pix_fmt": self.pix_box.currentData() or "yuv420p",
            "scale": scale_param,
            "sub_path": to_paths(self.sub_pick.text())[0] if to_paths(self.sub_pick.text()) else None,
            "font_path": to_paths(self.font_pick.text())[0] if to_paths(self.font_pick.text()) else None,
            "aud_cfg": audio,
            "out_dir": to_one(self.out_pick.text()),
            "ext_params": ext,
        }
