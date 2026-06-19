import os
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QGridLayout,
    QHeaderView, QHBoxLayout, QLabel, QMessageBox,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CardWidget, ComboBox, FluentIcon, InfoBar,
    InfoBarPosition, PrimaryPushButton, ProgressBar, PushButton,
    SubtitleLabel, TableWidget, TextEdit, TitleLabel, qconfig,
    CaptionLabel
)

from ui.other.path import DropEdit
from ui.theme import dialog_card_style, dialog_style, polish_theme_widgets, valid_text_color
from utils import load_cfg, save_cfg

# 版本号
CURRENT_VERSION = "v0.9.2-pre"


class DashCard(CardWidget):
    """主页功能仪表板卡片，点击时发出 clicked 信号"""

    clicked = Signal()

    def __init__(self, title: str, desc: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(150)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        title_label = TitleLabel(title, self)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        desc_label = CaptionLabel(desc, self)
        desc_label.setWordWrap(True)

        lay.addWidget(title_label)
        lay.addSpacing(6)
        lay.addWidget(desc_label)
        lay.addStretch()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.clicked.emit()
        super().mousePressEvent(e)


class BasePage(QWidget):
    """所有功能页面的基类，提供标题和卡片布局容器"""

    def __init__(self, title: str, obj_name: str, parent: QWidget | None = None, add_stretch: bool = True):
        super().__init__(parent)
        self.setObjectName(obj_name)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(35, 14, 35, 28)
        self.lay.setSpacing(18)

        title_label = TitleLabel(title, self)
        title_label.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        self.lay.addWidget(title_label)

        self.cards = QVBoxLayout()
        self.cards.setSpacing(16)
        self.lay.addLayout(self.cards)
        if add_stretch:
            self.lay.addStretch()


class HomePage(QWidget):
    """主页，展示功能导航卡片和版本信息"""

    go = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("tab_home")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(50, 40, 50, 40)
        lay.setSpacing(24)

        top_lay = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.setAlignment(Qt.AlignmentFlag.AlignBottom)
        title = TitleLabel("FFmpeg EncodeTools GUI", self)
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        ver_label = CaptionLabel(CURRENT_VERSION, self)
        ver_label.setStyleSheet("color: #858585; margin-bottom: 6px;")
        ver_label.setFont(QFont("Segoe UI", 14))
        title_row.addWidget(title)
        title_row.addWidget(ver_label)
        title_row.addStretch()
        
        title_box.addLayout(title_row)
        title_box.addWidget(BodyLabel("基于FFmpeg的，更适配字幕组工作流程的压制工具箱", self))
        top_lay.addLayout(title_box)
        top_lay.addStretch()
        
        btn_box = QVBoxLayout()
        btn_box.setSpacing(8)
        btn_dir = PushButton(FluentIcon.FOLDER, "打开软件所在目录", self)
        btn_dir.clicked.connect(lambda: os.startfile(os.getcwd()))
        
        row2_lay = QHBoxLayout()
        row2_lay.setSpacing(8)
        self.btn_about = PushButton(FluentIcon.INFO, "关于", self)
        self.btn_about.clicked.connect(self._show_about)
        self.btn_update = PushButton(FluentIcon.GITHUB, "检查版本更新", self)
        self.btn_update.clicked.connect(lambda: webbrowser.open("https://github.com/39HC-0210/FFmpeg-EncodeTools/releases"))
        row2_lay.addWidget(self.btn_about)
        row2_lay.addWidget(self.btn_update)
        
        btn_box.addWidget(btn_dir)
        btn_box.addLayout(row2_lay)
        top_lay.addLayout(btn_box)
        lay.addLayout(top_lay)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        
        card_encode = DashCard("视频压制", "使用 FFmpeg 中的编码器对文件中的视频、音频进行压制")
        card_encode.clicked.connect(lambda: self.go.emit("tab_encode"))
        grid.addWidget(card_encode, 0, 0)
        
        card_mux = DashCard("混流封装", "导入文件，选取已有轨道进行无损混流")
        card_mux.clicked.connect(lambda: self.go.emit("tab_mux"))
        grid.addWidget(card_mux, 0, 1)
        
        card_fast_mux = DashCard("MP4快速封装", "以 MP4BOX 为基础，针对字幕组压制中的常见需求特化出的快速封装界面")
        card_fast_mux.clicked.connect(lambda: self.go.emit("tab_fast_mux"))
        grid.addWidget(card_fast_mux, 1, 0)
        
        card_chapter = DashCard("章节封装", "导入或编写章节文件，并将其封入视频文件中")
        card_chapter.clicked.connect(lambda: self.go.emit("tab_chapter"))
        grid.addWidget(card_chapter, 1, 1)
        
        card_clean = DashCard("字幕清洗", "利用既有的清洗规则，针对ASS/SRT字幕中的无效文本进行清洗并等分，得到更适合字幕组翻译使用的干净文本")
        card_clean.clicked.connect(lambda: self.go.emit("tab_clean"))
        grid.addWidget(card_clean, 2, 0)
        
        card_vs = DashCard("VapourSynth压制", "编写vpy脚本、调用视频编码器，针对目标视频源进行预处理并压制")
        card_vs.clicked.connect(lambda: self.go.emit("tab_vs_encode"))
        grid.addWidget(card_vs, 2, 1)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch()

    def _show_about(self) -> None:
        dlg = AboutDialog(self.window())
        dlg.exec()


class SettingsPage(QWidget):
    """系统设置页：配置工具路径和任务完成后的预设动作"""

    def __init__(self):
        super().__init__()
        self.setObjectName("tab_settings")
        self.cfg = load_cfg()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(35, 14, 35, 28)
        lay.setSpacing(18)

        title = TitleLabel("系统设置", self)
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        lay.addWidget(title)

        tool_card = CardWidget()
        tool_lay = QVBoxLayout(tool_card)
        tool_lay.setContentsMargins(16, 10, 16, 10)
        tool_lay.setSpacing(8)
        tool_lay.addWidget(SubtitleLabel("程序路径"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        self.ff_in = DropEdit(replace=True)
        self.ff_in.setText(self.cfg.get("ffmpeg_path", ""))
        self.ff_btn = PushButton("选择")
        self.ff_btn.clicked.connect(lambda: self._choose_exe(self.ff_in))

        self.fp_in = DropEdit(replace=True)
        self.fp_in.setText(self.cfg.get("ffprobe_path", ""))
        self.fp_btn = PushButton("选择")
        self.fp_btn.clicked.connect(lambda: self._choose_exe(self.fp_in))

        self.mp_in = DropEdit(replace=True)
        self.mp_in.setText(self.cfg.get("mp4box_path", ""))
        self.mp_btn = PushButton("选择")
        self.mp_btn.clicked.connect(lambda: self._choose_exe(self.mp_in))

        grid.addWidget(BodyLabel("FFmpeg"), 0, 0)
        grid.addWidget(self.ff_in, 0, 1)
        grid.addWidget(self.ff_btn, 0, 2)
        grid.addWidget(BodyLabel("FFprobe"), 1, 0)
        grid.addWidget(self.fp_in, 1, 1)
        grid.addWidget(self.fp_btn, 1, 2)
        grid.addWidget(BodyLabel("MP4Box"), 2, 0)
        grid.addWidget(self.mp_in, 2, 1)
        grid.addWidget(self.mp_btn, 2, 2)
        grid.setColumnStretch(1, 1)
        tool_lay.addLayout(grid)
        lay.addWidget(tool_card)

        vs_card = CardWidget()
        vs_lay = QVBoxLayout(vs_card)
        vs_lay.setContentsMargins(16, 10, 16, 10)
        vs_lay.setSpacing(8)
        vs_lay.addWidget(SubtitleLabel("VapourSynth 工具"))

        vs_grid = QGridLayout()
        vs_grid.setHorizontalSpacing(12)
        vs_grid.setVerticalSpacing(8)
        self.vs_in = DropEdit(replace=True)
        self.vs_in.setText(self.cfg.get("vspipe_path", ""))
        self.vs_btn = PushButton("选择")
        self.vs_btn.clicked.connect(lambda: self._choose_exe(self.vs_in))

        self.x5_in = DropEdit(replace=True)
        self.x5_in.setText(self.cfg.get("x265_path", ""))
        self.x5_btn = PushButton("选择")
        self.x5_btn.clicked.connect(lambda: self._choose_exe(self.x5_in))

        self.x4_in = DropEdit(replace=True)
        self.x4_in.setText(self.cfg.get("x264_path", ""))
        self.x4_btn = PushButton("选择")
        self.x4_btn.clicked.connect(lambda: self._choose_exe(self.x4_in))

        vs_grid.addWidget(BodyLabel("vspipe"), 0, 0)
        vs_grid.addWidget(self.vs_in, 0, 1)
        vs_grid.addWidget(self.vs_btn, 0, 2)
        vs_grid.addWidget(BodyLabel("x265"), 1, 0)
        vs_grid.addWidget(self.x5_in, 1, 1)
        vs_grid.addWidget(self.x5_btn, 1, 2)
        vs_grid.addWidget(BodyLabel("x264"), 2, 0)
        vs_grid.addWidget(self.x4_in, 2, 1)
        vs_grid.addWidget(self.x4_btn, 2, 2)
        vs_grid.setColumnStretch(1, 1)
        vs_lay.addLayout(vs_grid)
        lay.addWidget(vs_card)

        action_card = CardWidget()
        action_lay = QVBoxLayout(action_card)
        action_lay.setContentsMargins(16, 8, 16, 8)
        action_lay.setSpacing(6)
        action_lay.addWidget(SubtitleLabel("任务完成后的预设动作"))

        self.action_box = ComboBox()
        self.action_box.addItems(["无动作", "系统通知", "打开输出文件夹", "退出软件", "关机"])
        self.action_box.setCurrentText(self.cfg.get("post_task_action", "无动作"))

        self.action_desc = BodyLabel("说明：\n- 关机：请慎重选择！任务完成后会强制将窗口置顶显示并弹出倒计时确认窗。如果 1 分钟内无人响应，系统将执行自动关机。")
        self.action_desc.setStyleSheet("color: #858585; font-size: 11px;")

        action_lay.addWidget(self.action_box)
        action_lay.addWidget(self.action_desc)
        lay.addWidget(action_card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_check = PushButton("检测")
        btn_check.clicked.connect(self._check)
        
        btn_save = PrimaryPushButton("保存")
        btn_save.clicked.connect(self._save)
        
        btn_row.addWidget(btn_check)
        btn_row.addWidget(btn_save)
        
        lay.addLayout(btn_row)
        lay.addStretch()

    def _choose_exe(self, edit_widget: DropEdit) -> None:
        """弹出文件对话框选择可执行文件，支持相对路径"""
        path, _ = QFileDialog.getOpenFileName(self, "选择程序文件", "", "可执行文件 (*.exe);;所有文件 (*.*)")
        if path:
            try:
                rel_path = os.path.relpath(path, os.getcwd())
                if not rel_path.startswith(".."):
                    path = ".\\" + rel_path
                else:
                    path = os.path.normpath(path)
            except ValueError:
                path = os.path.normpath(path)
            edit_widget.setText(path)

    def _check(self) -> None:
        """检测各工具路径配置的有效性并弹出结果"""
        cfg = load_cfg()

        def get_status(name: str) -> str:
            path = cfg.get(f"{name}_path", "").strip()
            if not path:
                return "未配置"
            
            resolved_path = None
            if path.startswith(".\\") or path.startswith("./"):
                p = Path(os.getcwd()) / path
                if p.is_file():
                    resolved_path = p
            else:
                p = Path(path)
                if p.is_file():
                    resolved_path = p
            
            if not resolved_path:
                return "未生效"
                
            fname = resolved_path.name.lower()
            if name.lower() not in fname:
                return "未生效"
                
            return "正常"

        InfoBar.info(
            "环境检测",
            f"FFmpeg: {get_status('ffmpeg')}\n"
            f"FFprobe: {get_status('ffprobe')}\n"
            f"MP4Box: {get_status('mp4box')}\n"
            f"vspipe: {get_status('vspipe')}\n"
            f"x265: {get_status('x265')}\n"
            f"x264: {get_status('x264')}",
            position=InfoBarPosition.TOP,
            parent=self.window(),
            duration=5000,
        )

    def _save(self) -> None:
        """保存当前设置到配置文件"""
        self.cfg["ffmpeg_path"] = self.ff_in.text().strip()
        self.cfg["ffprobe_path"] = self.fp_in.text().strip()
        self.cfg["mp4box_path"] = self.mp_in.text().strip()
        self.cfg["vspipe_path"] = self.vs_in.text().strip()
        self.cfg["x265_path"] = self.x5_in.text().strip()
        self.cfg["x264_path"] = self.x4_in.text().strip()
        self.cfg["post_task_action"] = self.action_box.currentText()
        save_cfg(self.cfg)
        InfoBar.success("保存成功", "设置已保存。", position=InfoBarPosition.TOP, parent=self.window(), duration=5000)

    def get_job(self) -> tuple[None, None]:
        return None, None


class BaseDialog(QDialog):
    """弹窗基类，提供无边框半透明背景和主题跟随"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._pos: QPoint | None = None
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        qconfig.themeChanged.connect(self._theme)

    def _theme(self) -> None:
        self.setStyleSheet(dialog_style())
        polish_theme_widgets(self)


class AboutDialog(BaseDialog):
    """关于本软件弹窗"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.resize(500, 290)
        self._ui()
        self._theme()

    def _ui(self) -> None:
        """构建关于弹窗 UI 布局"""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.card = CardWidget()
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(24, 24, 24, 24)
        card_lay.setSpacing(12)

        title_lay = QHBoxLayout()
        title_lbl = SubtitleLabel("关于 FFmpeg EncodeTools GUI", self)
        title_lbl.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_lay.addWidget(title_lbl)
        title_lay.addStretch()
        card_lay.addLayout(title_lay)

        author_text = (
            "<b>项目作者：</b>H.Coo<br>"
            "<b>项目地址：</b><a href='https://github.com/39HC-0210/FFmpeg-EncodeTools' style='color: #39C5BB; text-decoration: underline;'>https://github.com/39HC-0210/FFmpeg-EncodeTools</a>"
        )
        self.author_lbl = BodyLabel(author_text, self)
        self.author_lbl.setOpenExternalLinks(True)
        card_lay.addWidget(self.author_lbl)
        card_lay.addSpacing(4)

        license_text = (
            "本软件使用了 FFmpeg 的可执行程序，FFmpeg 受 GPL/LGPL 许可证保护。其相关信息可访问 "
            "<a href='https://ffmpeg.org' style='color: #39C5BB; text-decoration: underline;'>FFmpeg 官方网站</a> 获取。<br>"
            "本软件支持调用 VapourSynth 进行压制，VapourSynth 受 LGPL 2.1 许可证保护。其相关信息可访问 "
            "<a href='https://www.vapoursynth.com/' style='color: #39C5BB; text-decoration: underline;'>VapourSynth 官方网站</a> 获取。"
        )
        self.license_lbl = BodyLabel(license_text, self)
        self.license_lbl.setStyleSheet("color: #858585; font-size: 11.5px; line-height: 140%;")
        self.license_lbl.setWordWrap(True)
        self.license_lbl.setOpenExternalLinks(True)
        card_lay.addWidget(self.license_lbl)
        card_lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_close = PrimaryPushButton("确定", self)
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)
        card_lay.addLayout(btn_row)

        lay.addWidget(self.card)

    def _theme(self) -> None:
        super()._theme()
        self.card.setStyleSheet(dialog_card_style())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._pos is not None:
            self.move(event.globalPosition().toPoint() - self._pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._pos = None
        super().mouseReleaseEvent(event)


class ShutdownCountdownDialog(BaseDialog):
    """关机倒计时弹窗，60 秒内可取消，超时执行 shutdown /s"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.resize(400, 200)
        self.seconds_left = 60
        self._ui()
        self._theme()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _ui(self) -> None:
        """构建关机倒计时弹窗 UI 布局"""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.card = CardWidget()
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(22, 22, 22, 22)
        card_lay.setSpacing(16)

        self.title_lbl = SubtitleLabel("系统自动关机提示", self)
        self.desc_lbl = BodyLabel("所有任务已完成，系统将在 60 秒后关机。\n若要继续使用，请点击下方按钮取消关机。", self)
        self.desc_lbl.setWordWrap(True)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = PrimaryPushButton("取消关机", self)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)

        card_lay.addWidget(self.title_lbl)
        card_lay.addWidget(self.desc_lbl)
        card_lay.addLayout(btn_row)
        lay.addWidget(self.card)

    def _theme(self) -> None:
        super()._theme()
        self.card.setStyleSheet(dialog_card_style())

    def _tick(self) -> None:
        """倒计时每秒回调，归零后执行关机"""
        self.seconds_left -= 1
        self.desc_lbl.setText(f"所有任务已完成，系统将在 {self.seconds_left} 秒后关机。\n若要继续使用，请点击下方按钮取消关机。")
        if self.seconds_left <= 0:
            self.timer.stop()
            self.accept()
            os.system("shutdown /s /t 0")

    def _cancel(self) -> None:
        """取消关机倒计时"""
        self.timer.stop()
        self.reject()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._pos is not None:
            self.move(event.globalPosition().toPoint() - self._pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._pos = None
        super().mouseReleaseEvent(event)


class TaskDialog(BaseDialog):
    """任务执行弹窗，展示实时日志、进度条与暂停/保存日志操作"""

    def __init__(self, parent: QWidget, runner):  # Runner imported locally below
        from core.work import Runner
        super().__init__(parent)
        self.runner = runner
        self._err = False
        self.resize(600, 380)
        self._ui()
        self._bind()
        self._theme()

    def _ui(self) -> None:
        """构建任务弹窗 UI 布局"""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.card = CardWidget()
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(12)
        card_lay.addWidget(SubtitleLabel("任务执行中..."))

        self.log_box = TextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        card_lay.addWidget(self.log_box)

        self.status_lbl = BodyLabel("准备中...")
        card_lay.addWidget(self.status_lbl)

        self.bar = ProgressBar()
        self.bar.setRange(0, 100)
        card_lay.addWidget(self.bar)

        btn_row = QHBoxLayout()
        self.btn_pause = PushButton("暂停")
        self.btn_pause.clicked.connect(self._pause)

        self.btn_save_log = PushButton("保存日志")
        self.btn_save_log.clicked.connect(self._save_log)

        self.btn_close = PrimaryPushButton("关闭")
        self.btn_close.clicked.connect(self._close_dlg)
        self.btn_close.setEnabled(False)

        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_save_log)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_close)
        card_lay.addLayout(btn_row)
        lay.addWidget(self.card)

    def _bind(self):
        self.runner.sig.prog.connect(self._on_prog)
        self.runner.sig.log.connect(self.log_box.append)
        self.runner.sig.done.connect(self._done)
        self.runner.sig.err.connect(lambda e: self.log_box.append(f"\n[错误] {e}"))

    def _on_prog(self, val, desc):
        self.bar.setValue(val)
        if desc:
            self.status_lbl.setText(desc)

    def _theme(self):
        super()._theme()
        self.card.setStyleSheet(dialog_card_style())

    def _pause(self):
        if self.runner.paused:
            self.runner.goon()
            self.btn_pause.setText("暂停")
            self.btn_close.setEnabled(False)
        else:
            self.runner.pause()
            self.btn_pause.setText("继续")
            self.btn_close.setEnabled(True)

    def _save_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if path:
            try:
                Path(path).write_text(self.log_box.toPlainText(), encoding="utf-8")
                InfoBar.success("保存成功", f"日志已成功保存至 {Path(path).name}", position=InfoBarPosition.TOP, parent=self, duration=5000)
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"保存失败: {e}")

    def _close_dlg(self):
        if not self.runner.isFinished():
            self.runner.stop()
        super().accept()

    def reject(self):
        if not self.runner.isFinished() and not self.runner.paused:
            QMessageBox.warning(self, "提示", "请先暂停任务后再关闭窗口。")
            return
        if not self.runner.isFinished():
            self.runner.stop()
        super().reject()

    def _done(self):
        if not self.runner.cancelled and not self._err:
            self.bar.setValue(100)
        self.btn_pause.setEnabled(False)
        self.btn_close.setEnabled(True)


class ChapDialog(BaseDialog):
    """章节编辑弹窗，提供增删改排序的章节时间/名称表格"""

    def __init__(self, parent: QWidget | None = None, data: list[dict[str, str]] | None = None):
        super().__init__(parent)
        self.resize(600, 480)
        self._ui(data or [])
        self._theme()

    def _ui(self, data):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.card = CardWidget()
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(12)
        card_lay.addWidget(SubtitleLabel("章节列表"))

        self.tbl = TableWidget()
        self.tbl.setColumnCount(2)
        self.tbl.setHorizontalHeaderLabels(["时间", "名称"])
        self.tbl.setBorderVisible(True)
        self.tbl.setBorderRadius(6)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnWidth(0, 220)
        self.tbl.setMinimumHeight(250)
        card_lay.addWidget(self.tbl)

        btn_row = QHBoxLayout()
        btn_add = PushButton(FluentIcon.ADD, "添加")
        btn_del = PushButton(FluentIcon.DELETE, "删除")
        btn_sort = PushButton(FluentIcon.SCROLL, "按时间排序")
        btn_save = PrimaryPushButton(FluentIcon.SAVE, "保存")
        btn_cancel = PushButton(FluentIcon.CLOSE, "取消")
        btn_add.clicked.connect(lambda: self._add("", ""))
        btn_del.clicked.connect(self._del)
        btn_sort.clicked.connect(self._sort)
        btn_save.clicked.connect(self._ok)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_sort)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        card_lay.addLayout(btn_row)
        lay.addWidget(self.card)

        self.tbl.blockSignals(True)
        if data:
            for item in data:
                self._add(item.get("time", ""), item.get("name", ""))
        else:
            self._add("00:00:00.000", "")
        self.tbl.blockSignals(False)
        self.tbl.cellChanged.connect(self._on_edit)

    def _theme(self):
        super()._theme()
        self.card.setStyleSheet(dialog_card_style())

    def _valid(self, text):
        try:
            parts = text.replace(".", ":").split(":")
            if len(parts) < 3:
                return False
            int(parts[0])
            int(parts[1])
            int(parts[2])
            if len(parts) > 3:
                int(parts[3])
            return True
        except (TypeError, ValueError):
            return False

    def _on_edit(self, row, col):
        # 校验章节时间格式
        item = self.tbl.item(row, col)
        if col == 0 and item:
            item.setForeground(QColor(valid_text_color() if self._valid(item.text().strip()) else "#F44747"))

    def _ok(self):
        has_error = False
        for row in range(self.tbl.rowCount()):
            item = self.tbl.item(row, 0)
            text = item.text().strip() if item else ""
            if text and not self._valid(text):
                has_error = True
                if item:
                    item.setForeground(QColor("#F44747"))
        if has_error:
            QMessageBox.warning(self, "时间格式错误", "请检查章节时间。")
            return
        self.accept()

    def _add(self, time_text, name_text):
        row = self.tbl.rowCount()
        self.tbl.insertRow(row)
        self.tbl.setItem(row, 0, QTableWidgetItem(time_text))
        self.tbl.setItem(row, 1, QTableWidgetItem(name_text))

    def _del(self):
        row = self.tbl.currentRow()
        if row >= 0:
            self.tbl.removeRow(row)

    def _sort(self):
        # 按章节时间进行重新排序
        data = self.get()

        def to_ms(text):
            try:
                parts = text.replace(".", ":").split(":")
                h, m, s = parts[:3]
                ms = parts[3] if len(parts) > 3 else "0"
                return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
            except Exception:
                return float("inf")

        data.sort(key=lambda item: to_ms(item["time"]))
        self.tbl.blockSignals(True)
        self.tbl.setRowCount(0)
        for item in data:
            self._add(item["time"], item["name"])
        self.tbl.blockSignals(False)

    def get(self):
        result = []
        for row in range(self.tbl.rowCount()):
            time_item = self.tbl.item(row, 0)
            name_item = self.tbl.item(row, 1)
            time_text = time_item.text().strip() if time_item else ""
            name_text = name_item.text().strip() if name_item else ""
            if time_text or name_text:
                result.append({"time": time_text, "name": name_text})
        return result
