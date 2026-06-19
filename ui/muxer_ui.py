import os
import subprocess
import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPixmap, QPainter, QIcon, QPen, QPainterPath, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView,
    QListWidget, QListWidgetItem, QLabel
)
from qfluentwidgets import (
    BodyLabel, CardWidget, ComboBox, FluentIcon, InfoBar, InfoBarPosition,
    PushButton, RadioButton, SubtitleLabel,
    TableWidget, CaptionLabel, LineEdit,
    ListWidget
)

from core.tools.chapters import read_chap
from ui.main_ui import BasePage, ChapDialog
from ui.other.path import DropEdit, PathPick, FilePick, to_one, to_paths
from utils import find_exe

FONT_EXTS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".flv", ".mov", ".wmv", ".webm", ".ts", ".m2ts", ".mpg", ".mpeg", ".hevc", ".avc", ".h264", ".h265", ".264", ".265", ".ivf"}
AUDIO_EXTS = {".aac", ".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".ac3", ".eac3", ".dts", ".mka", ".wma", ".ape", ".tak"}
SUB_EXTS = {".ass", ".srt", ".ssa", ".sup", ".sub", ".idx", ".vtt", ".lrc"}

LANG_LIST = [
    ("und", "未指定"),
    ("chi", "中文"),
    ("jpn", "日语"),
    ("eng", "英语"),
]

LANG_CODES = [c for c, _ in LANG_LIST]
LANG_LABELS = [f"{label} ({code})" for code, label in LANG_LIST]

SRC_COLORS = [
    "#F44336",
    "#2196F3",
    "#4CAF50",
    "#FF9800",
    "#9C27B0",
    "#009688",
    "#E91E63",
    "#3F51B5",
    "#8BC34A",
    "#795548"
]


def _guess_type(path_str):
    ext = Path(path_str).suffix.lower()
    if ext in VIDEO_EXTS: return "video"
    if ext in AUDIO_EXTS: return "audio"
    if ext in SUB_EXTS: return "subtitle"
    return "video"


def _is_font(path_str):
    return Path(path_str).suffix.lower() in FONT_EXTS


def _type_label(t):
    return {"video": "视频", "audio": "音频", "subtitle": "字幕"}.get(t, t)


def _probe_streams(path_str):
    fp = find_exe("ffprobe")
    if not fp:
        return []
    try:
        c_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(
            [fp, "-v", "error", "-show_entries",
             "stream=index,codec_type,codec_name:stream_tags=language,title",
             "-of", "json", str(path_str)],
            capture_output=True, text=True, creationflags=c_flag, timeout=5,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            return data.get("streams", [])
        return []
    except Exception:
        return []


class SourceDropArea(ListWidget):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e: QDropEvent):
        if e.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class AttachDropArea(QWidget):
    fonts_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e: QDropEvent):
        if e.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile() and _is_font(u.toLocalFile())]
            if paths:
                self.fonts_dropped.emit(paths)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class DragListWidget(QListWidget):
    row_moved = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSpacing(2)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; padding: 0px; margin: 0px; }
            QListWidget::item { background: transparent; border: none; outline: none; padding: 0px; margin: 0px; }
            QListWidget::item:hover { background: transparent; border: none; }
            QListWidget::item:selected { background: transparent; border: none; }
            QListWidget::item:selected:active { background: transparent; border: none; }
        """)
        self.itemSelectionChanged.connect(self._update_all_cards)

    def _update_all_cards(self):
        for i in range(self.count()):
            item = self.item(i)
            if item:
                w = self.itemWidget(item)
                if w:
                    w.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # 实时计算拖拽后的位置
        selected_items = self.selectedItems()
        if not selected_items:
            event.ignore()
            return
        src_row = self.row(selected_items[0])

        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item:
            dest_row = self.row(item)
        else:
            dest_row = self.count() - 1

        if src_row != dest_row:
            self.row_moved.emit(src_row, dest_row)
            event.setDropAction(Qt.DropAction.IgnoreAction)
            event.accept()
        else:
            event.ignore()


class TrackHeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 12)
        lay.setSpacing(12)
        
        from qfluentwidgets import isDarkTheme
        c = "#888888" if isDarkTheme() else "#999999"
        style = f"color: {c}; font-weight: 600; font-size: 12px;"
        
        self.lbl_type = QLabel("类型")
        self.lbl_type.setStyleSheet(style)
        self.lbl_type.setFixedWidth(80)
        
        self.lbl_codec = QLabel("编码")
        self.lbl_codec.setStyleSheet(style)
        self.lbl_codec.setFixedWidth(100)
        
        self.lbl_lang = QLabel("语言")
        self.lbl_lang.setStyleSheet(style)
        self.lbl_lang.setFixedWidth(120)
        
        self.lbl_name = QLabel("名称")
        self.lbl_name.setStyleSheet(style)
        
        self.lbl_ops = QLabel("操作")
        self.lbl_ops.setStyleSheet(style)
        self.lbl_ops.setFixedWidth(50)
        self.lbl_ops.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lay.addWidget(self.lbl_type)
        lay.addWidget(self.lbl_codec)
        lay.addWidget(self.lbl_lang)
        lay.addWidget(self.lbl_name, stretch=1)
        lay.addWidget(self.lbl_ops)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        c = QColor(255, 255, 255, 20) if is_dark else QColor(0, 0, 0, 15)
        p.setPen(QPen(c, 1))
        p.drawLine(12, self.height() - 1, self.width() - 12, self.height() - 1)
        
        y1, y2 = 6, self.height() - 6
        x1 = self.lbl_codec.geometry().left() - 6
        x2 = self.lbl_lang.geometry().left() - 6
        x3 = self.lbl_name.geometry().left() - 6
        x4 = self.lbl_ops.geometry().left() - 6
        
        p.drawLine(x1, y1, x1, y2)
        p.drawLine(x2, y1, x2, y2)
        p.drawLine(x3, y1, x3, y2)
        p.drawLine(x4, y1, x4, y2)


class TrackCardWidget(QWidget):
    remove_clicked = Signal(int)

    def __init__(self, idx, trk, color_hex, color_icon, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.setFixedHeight(36)
        self.is_hovered = False
        self.setMouseTracking(True)
        
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        if is_dark:
            self.bg_color = QColor(255, 255, 255, 8)
            self.border_color = QColor(255, 255, 255, 20)
        else:
            self.bg_color = QColor(0, 0, 0, 5)
            self.border_color = QColor(0, 0, 0, 15)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)
        
        lbl_type_icon = QLabel()
        lbl_type_icon.setPixmap(color_icon.pixmap(16, 16))
        lbl_type_icon.setFixedSize(16, 16)
        
        t_str = _type_label(trk.get("type", ""))
        lbl_type_text = QLabel(t_str)
        
        type_lay = QHBoxLayout()
        type_lay.setContentsMargins(0, 0, 0, 0)
        type_lay.setSpacing(6)
        type_lay.addWidget(lbl_type_icon)
        type_lay.addWidget(lbl_type_text)
        
        self.type_widget = QWidget()
        self.type_widget.setLayout(type_lay)
        self.type_widget.setFixedWidth(80)
        
        self.lbl_codec = QLabel(trk.get("codec", ""))
        self.lbl_codec.setFixedWidth(100)
        
        lang_code = trk.get("lang", "und")
        lang_display = lang_code
        for code, label in LANG_LIST:
            if code == lang_code:
                lang_display = label
                break
        self.lbl_lang = QLabel(lang_display)
        self.lbl_lang.setFixedWidth(120)
        
        self.lbl_name = QLabel(trk.get("name", ""))
        self.lbl_name.setStyleSheet("color: #E8E8E8;" if is_dark else "color: #333333;")
        self.lbl_name.setToolTip(trk.get("name", ""))
        
        self.btn_rm = PushButton("删除", self)
        self.btn_rm.setFixedSize(50, 22)
        self.btn_rm.setStyleSheet("""
            PushButton {
                background: transparent;
                border: none;
                color: #FF4D4F;
                font-weight: 500;
                font-size: 12px;
                padding: 0px;
                margin: 0px;
            }
            PushButton:hover {
                background: rgba(255, 77, 79, 0.1);
                border-radius: 4px;
            }
            PushButton:pressed {
                background: rgba(255, 77, 79, 0.2);
            }
        """)
        self.btn_rm.clicked.connect(lambda: self.remove_clicked.emit(self.idx))
        
        lay.addWidget(self.type_widget)
        lay.addWidget(self.lbl_codec)
        lay.addWidget(self.lbl_lang)
        lay.addWidget(self.lbl_name, stretch=1)
        lay.addWidget(self.btn_rm)
        
    def sizeHint(self):
        return QSize(100, 36)

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from qfluentwidgets import isDarkTheme
        is_dark = isDarkTheme()
        
        is_selected = False
        viewport = self.parent()
        if viewport:
            list_widget = viewport.parent()
            if isinstance(list_widget, QListWidget):
                item = list_widget.item(self.idx)
                if item and item.isSelected():
                    is_selected = True
                    
        if is_selected:
            bg = QColor(255, 255, 255, 18) if is_dark else QColor(0, 0, 0, 12)
            border = QColor(255, 255, 255, 45) if is_dark else QColor(0, 0, 0, 30)
        elif self.is_hovered:
            bg = QColor(255, 255, 255, 12) if is_dark else QColor(0, 0, 0, 8)
            border = QColor(255, 255, 255, 30) if is_dark else QColor(0, 0, 0, 20)
        else:
            bg = self.bg_color
            border = self.border_color
            
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        
        p.fillPath(path, bg)
        p.setPen(QPen(border, 1))
        p.drawPath(path)
        
        div_color = QColor(255, 255, 255, 15) if is_dark else QColor(0, 0, 0, 10)
        p.setPen(QPen(div_color, 1))
        y1, y2 = 6, self.height() - 6
        
        x1 = self.lbl_codec.geometry().left() - 6
        x2 = self.lbl_lang.geometry().left() - 6
        x3 = self.lbl_name.geometry().left() - 6
        x4 = self.btn_rm.geometry().left() - 6
        
        p.drawLine(x1, y1, x1, y2)
        p.drawLine(x2, y1, x2, y2)
        p.drawLine(x3, y1, x3, y2)
        p.drawLine(x4, y1, x4, y2)


class MuxPage(BasePage):
    """高级混流封装页面：多源文件、轨道选择、语言/名称元数据、MKV 字体附件"""

    def __init__(self) -> None:
        super().__init__("混流封装", "tab_mux", add_stretch=False)
        self._sources = []
        self._tracks = []
        self._attachments = []
        self._selected_row = -1

        self._ui()

    def _ui(self):
        top_widget = QWidget()
        top_lay = QHBoxLayout(top_widget)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(12)
        
        src_card = CardWidget()
        src_lay = QVBoxLayout(src_card)
        src_lay.setContentsMargins(14, 14, 14, 14)
        src_lay.setSpacing(10)
        
        src_hdr = QHBoxLayout()
        src_hdr.addWidget(SubtitleLabel("源文件"))
        src_hdr.addStretch()
        self.btn_add_src = PushButton(FluentIcon.ADD, "添加文件")
        self.btn_add_src.clicked.connect(self._add_files_dialog)
        self.btn_rm_src = PushButton(FluentIcon.DELETE, "移除文件")
        self.btn_rm_src.clicked.connect(self._remove_selected_source)
        src_hdr.addWidget(self.btn_add_src)
        src_hdr.addWidget(self.btn_rm_src)
        src_lay.addLayout(src_hdr)

        self.list_src = SourceDropArea()
        self.list_src.files_dropped.connect(self._on_files_dropped)
        src_lay.addWidget(self.list_src, stretch=1)
        
        top_lay.addWidget(src_card, stretch=6)

        prop_card = CardWidget()
        prop_lay = QVBoxLayout(prop_card)
        prop_lay.setContentsMargins(14, 14, 14, 14)
        prop_lay.setSpacing(10)
        prop_lay.addWidget(SubtitleLabel("轨道属性"))
        
        self.prop_hint = CaptionLabel("请在左侧选择一个轨道")
        prop_lay.addWidget(self.prop_hint)
        
        self.prop_body = QWidget()
        pb_lay = QGridLayout(self.prop_body)
        pb_lay.setContentsMargins(0, 0, 0, 0)
        pb_lay.setHorizontalSpacing(10)
        pb_lay.addWidget(BodyLabel("轨道名称"), 0, 0)
        self.prop_name = LineEdit()
        self.prop_name.textChanged.connect(self._on_prop_name_changed)
        pb_lay.addWidget(self.prop_name, 0, 1)
        pb_lay.addWidget(BodyLabel("轨道语言"), 1, 0)
        self.prop_lang = ComboBox()
        self.prop_lang.addItems(LANG_LABELS)
        self.prop_lang.currentIndexChanged.connect(self._on_prop_lang_changed)
        pb_lay.addWidget(self.prop_lang, 1, 1)
        pb_lay.setColumnStretch(1, 1)
        self.prop_body.hide()
        
        prop_lay.addWidget(self.prop_body)
        prop_lay.addStretch()
        
        top_lay.addWidget(prop_card, stretch=4)
        
        self.cards.addWidget(top_widget, stretch=1)

        bottom_widget = QWidget()
        bottom_lay = QHBoxLayout(bottom_widget)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(12)

        trk_card = CardWidget()
        trk_lay = QVBoxLayout(trk_card)
        trk_lay.setContentsMargins(14, 14, 14, 14)
        trk_lay.setSpacing(10)
        
        trk_lay.addWidget(SubtitleLabel("轨道"))

        self.hdr_trk = TrackHeaderWidget()
        trk_lay.addWidget(self.hdr_trk)

        self.list_trk = DragListWidget()
        self.list_trk.itemSelectionChanged.connect(self._on_track_selected)
        self.list_trk.row_moved.connect(self._on_row_moved)

        trk_lay.addWidget(self.list_trk, stretch=1)
        bottom_lay.addWidget(trk_card, stretch=6)

        right_bottom_widget = QWidget()
        right_bottom_lay = QVBoxLayout(right_bottom_widget)
        right_bottom_lay.setContentsMargins(0, 0, 0, 0)
        right_bottom_lay.setSpacing(12)

        chap_card = CardWidget()
        chap_lay = QVBoxLayout(chap_card)
        chap_lay.setContentsMargins(14, 14, 14, 14)
        chap_lay.setSpacing(10)
        chap_lay.addWidget(SubtitleLabel("导入章节文件"))
        self.chap_pick = FilePick("选择文件", "章节 (*.txt);;所有 (*.*)")
        chap_lay.addWidget(self.chap_pick)
        right_bottom_lay.addWidget(chap_card, stretch=0)

        attach_card = CardWidget()
        attach_lay = QVBoxLayout(attach_card)
        attach_lay.setContentsMargins(14, 14, 14, 14)
        attach_lay.setSpacing(10)
        
        att_hdr = QHBoxLayout()
        self.attach_count_lbl = CaptionLabel("拖入字体文件（.ttf/.otf/.ttc）")
        self.btn_clear_attach = PushButton(FluentIcon.DELETE, "清空附件")
        self.btn_clear_attach.clicked.connect(self._clear_attachments)
        att_hdr.addWidget(self.attach_count_lbl)
        att_hdr.addStretch()
        att_hdr.addWidget(self.btn_clear_attach)
        attach_lay.addLayout(att_hdr)
        
        self.attach_area = AttachDropArea()
        att_area_lay = QVBoxLayout(self.attach_area)
        att_area_lay.setContentsMargins(0, 0, 0, 0)
        self.attach_tbl = TableWidget()
        self.attach_tbl.setColumnCount(2)
        self.attach_tbl.setHorizontalHeaderLabels(["文件名", "格式"])
        self.attach_tbl.verticalHeader().setVisible(False)
        self.attach_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        att_area_lay.addWidget(self.attach_tbl)
        self.attach_area.fonts_dropped.connect(self._on_fonts_dropped)
        
        attach_lay.addWidget(self.attach_area, stretch=1)
        right_bottom_lay.addWidget(attach_card, stretch=1)

        bottom_lay.addWidget(right_bottom_widget, stretch=4)
        
        self.cards.addWidget(bottom_widget, stretch=2)

        out_card = CardWidget()
        out_lay = QHBoxLayout(out_card)
        out_lay.setContentsMargins(14, 10, 14, 10)
        out_lay.setSpacing(12)
        
        out_lay.addWidget(SubtitleLabel("输出"))

        self.rb_mkv = RadioButton("MKV")
        self.rb_mp4 = RadioButton("MP4")
        self.rb_mkv.setChecked(True)
        self.rb_mkv.toggled.connect(self._on_fmt_changed)
        self.rb_mp4.toggled.connect(self._on_fmt_changed)
        out_lay.addWidget(self.rb_mkv)
        out_lay.addWidget(self.rb_mp4)

        self.out_edit = DropEdit(replace=True)
        self.out_edit.setPlaceholderText("留空跟随首个视频的路径")
        out_lay.addWidget(self.out_edit, stretch=1)

        self.btn_out_browse = PushButton("选择位置")
        self.btn_out_browse.clicked.connect(self._browse_out)
        self.btn_out_sync = PushButton("同首个输入源")
        self.btn_out_sync.clicked.connect(self._sync_out)
        out_lay.addWidget(self.btn_out_browse)
        out_lay.addWidget(self.btn_out_sync)

        self.cards.addWidget(out_card, stretch=0)

    def _add_files_dialog(self):
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "添加源文件", "",
            "媒体文件 (*.mp4 *.mkv *.avi *.flv *.mov *.ts *.aac *.mp3 *.flac "
            "*.wav *.ogg *.opus *.m4a *.ac3 *.dts *.mka "
            "*.ass *.srt *.ssa *.sup *.vtt "
            "*.hevc *.avc *.h264 *.h265 "
            "*.ttf *.otf *.ttc *.woff);;所有文件 (*.*)"
        )
        if paths:
            self._on_files_dropped(paths)

    def _create_color_icon(self, color_hex, size=14):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(color_hex))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, size, size, 4, 4)
        p.end()
        return QIcon(pm)

    def _refresh_sources_list(self):
        self.list_src.clear()
        for idx, p in enumerate(self._sources):
            item = QListWidgetItem(Path(p).name)
            item.setIcon(self._create_color_icon(SRC_COLORS[idx % len(SRC_COLORS)]))
            self.list_src.addItem(item)

    def _on_files_dropped(self, paths):
        font_paths = [p for p in paths if _is_font(p)]
        track_paths = [p for p in paths if not _is_font(p)]

        if font_paths:
            self._on_fonts_dropped(font_paths)

        has_new = False
        for p in track_paths:
            if p not in self._sources:
                src_idx = len(self._sources)
                self._sources.append(p)
                has_new = True
                
                streams = _probe_streams(p)
                if not streams:
                    t = _guess_type(p)
                    self._tracks.append({
                        "src_idx": src_idx,
                        "st_idx": 0,
                        "type": t,
                        "name": "",
                        "lang": "und",
                        "codec": ""
                    })
                else:
                    for st in streams:
                        t = st.get("codec_type")
                        if t not in ("video", "audio", "subtitle"):
                            continue
                        tags = st.get("tags", {})
                        lang = tags.get("language", "und")
                        name = tags.get("title", "")
                        self._tracks.append({
                            "src_idx": src_idx,
                            "st_idx": st.get("index", 0),
                            "type": t,
                            "name": name,
                            "lang": lang,
                            "codec": st.get("codec_name", "")
                        })
        if has_new:
            self._refresh_sources_list()
            self._refresh_table()

    def _remove_selected_source(self):
        row = self.list_src.currentRow()
        if row < 0 or row >= len(self._sources):
            return
        
        self._tracks = [t for t in self._tracks if t["src_idx"] != row]
        for t in self._tracks:
            if t["src_idx"] > row:
                t["src_idx"] -= 1

        self._sources.pop(row)
        self._selected_row = -1
        self._show_prop(False)
        self._refresh_sources_list()
        self._refresh_table()

    def _on_row_moved(self, src_row, dest_row):
        if 0 <= src_row < len(self._tracks) and 0 <= dest_row < len(self._tracks):
            item = self._tracks.pop(src_row)
            self._tracks.insert(dest_row, item)
            self._refresh_table()
            self.list_trk.setCurrentRow(dest_row)

    def _refresh_table(self):
        self.list_trk.clear()

        for i, trk in enumerate(self._tracks):
            color_hex = SRC_COLORS[trk["src_idx"] % len(SRC_COLORS)]
            color_icon = self._create_color_icon(color_hex)

            item = QListWidgetItem()
            card = TrackCardWidget(i, trk, color_hex, color_icon)
            card.remove_clicked.connect(self._remove_track)
            
            item.setSizeHint(card.sizeHint())
            self.list_trk.addItem(item)
            self.list_trk.setItemWidget(item, card)

        if self._sources and not self.out_edit.text().strip():
            first_video_idx = next((t["src_idx"] for t in self._tracks if t["type"] == "video"), None)
            if first_video_idx is not None:
                suffix = ".mkv" if self.rb_mkv.isChecked() else ".mp4"
                out = Path(self._sources[first_video_idx]).with_suffix(suffix)
                self.out_edit.setText(str(out))

    def _remove_track(self, idx):
        if 0 <= idx < len(self._tracks):
            self._tracks.pop(idx)
            self._selected_row = -1
            self._refresh_table()
            self._show_prop(False)

    def _on_track_selected(self):
        items = self.list_trk.selectedItems()
        if not items:
            self._selected_row = -1
            self._show_prop(False)
            return
        idx = self.list_trk.row(items[0])
        if idx < 0 or idx >= len(self._tracks):
            self._show_prop(False)
            return
        self._selected_row = idx
        trk = self._tracks[idx]

        self.prop_name.blockSignals(True)
        self.prop_name.setText(trk.get("name", ""))
        self.prop_name.blockSignals(False)

        self.prop_lang.blockSignals(True)
        lang = trk.get("lang", "und")
        lang_idx = LANG_CODES.index(lang) if lang in LANG_CODES else 0
        self.prop_lang.setCurrentIndex(lang_idx)
        self.prop_lang.blockSignals(False)

        self._show_prop(True)

    def _show_prop(self, show):
        self.prop_body.setVisible(show)
        self.prop_hint.setVisible(not show)

    def _on_prop_name_changed(self, text):
        if self._selected_row < 0 or self._selected_row >= len(self._tracks): return
        self._tracks[self._selected_row]["name"] = text
        item = self.list_trk.item(self._selected_row)
        if item:
            w = self.list_trk.itemWidget(item)
            if w: w.lbl_name.setText(text)  # pyright: ignore[reportAttributeAccessIssue]

    def _on_prop_lang_changed(self, idx):
        if self._selected_row < 0 or self._selected_row >= len(self._tracks): return
        code = LANG_CODES[idx] if 0 <= idx < len(LANG_CODES) else "und"
        self._tracks[self._selected_row]["lang"] = code
        label = ""
        for c, l in LANG_LIST:
            if c == code:
                label = l
                break
        item = self.list_trk.item(self._selected_row)
        if item:
            w = self.list_trk.itemWidget(item)
            if w: w.lbl_lang.setText(label)  # pyright: ignore[reportAttributeAccessIssue]

    def _on_fonts_dropped(self, paths):
        for p in paths:
            if p not in self._attachments:
                self._attachments.append(p)
        self._refresh_attachments()

    def _clear_attachments(self):
        self._attachments.clear()
        self._refresh_attachments()

    def _refresh_attachments(self):
        self.attach_tbl.setRowCount(len(self._attachments))
        for i, p in enumerate(self._attachments):
            self.attach_tbl.setItem(i, 0, QTableWidgetItem(Path(p).name))
            self.attach_tbl.setItem(i, 1, QTableWidgetItem(Path(p).suffix.upper().lstrip(".")))
        cnt = len(self._attachments)
        self.attach_count_lbl.setText(f"共 {cnt} 个字体文件" if cnt > 0 else "拖入字体文件（.ttf/.otf/.ttc）")

    def _browse_out(self):
        from PySide6.QtWidgets import QFileDialog
        dp = ""
        if self._sources:
            dp = str(Path(self._sources[0]))
        p, _ = QFileDialog.getSaveFileName(self, "选择输出位置", dp, "所有文件 (*)")
        if p:
            self.out_edit.setText(p)

    def _sync_out(self):
        if self._sources:
            self.out_edit.setText(str(Path(self._sources[0]).parent))

    def _on_fmt_changed(self):
        suffix = ".mkv" if self.rb_mkv.isChecked() else ".mp4"
        raw = self.out_edit.text().strip()
        if raw:
            self.out_edit.setText(str(Path(raw).with_suffix(suffix)))

    def get_job(self) -> tuple:
        """收集混流任务参数

        Returns:
            (任务类型, 参数字典) 或 (None, 错误信息字符串)
        """
        if not self._tracks:
            return None, "请添加至少一个包含轨道的源文件。"

        fmt = "mkv" if self.rb_mkv.isChecked() else "mp4"
        if fmt == "mp4" and self._attachments:
            return None, "MP4 格式不支持封入字体附件，请切换为 MKV 或清空附件。"

        out = to_one(self.out_edit.text())
        if not out:
            return None, "请指定输出文件路径。"

        out_p = Path(out)
        if out_p.suffix.lower() != f".{fmt}":
            out = str(out_p.with_suffix(f".{fmt}"))

        chap = to_one(self.chap_pick.text())

        tracks_data = []
        for trk in self._tracks:
            tracks_data.append({
                "src_idx": trk["src_idx"],
                "st_idx": trk["st_idx"],
                "type": trk["type"],
                "name": trk.get("name", ""),
                "lang": trk.get("lang", "und"),
            })

        return "mux_ff", {
            "sources": list(self._sources),
            "tracks": tracks_data,
            "attachments": list(self._attachments),
            "chap_path": chap,
            "out_path": out,
            "fmt": fmt,
        }
