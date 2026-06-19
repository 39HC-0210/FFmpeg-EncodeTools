from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMessageBox, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel, CardWidget, FluentIcon, InfoBar, InfoBarPosition,
    PrimaryPushButton, ProgressBar, PushButton, SpinBox, StrongBodyLabel,
    TitleLabel, TransparentToolButton,
)

from core.work import Job, JobQ, JobState, load_q
from ui.theme import polish_theme_widgets


class TaskCard(CardWidget):
    """队列中的单个任务卡片，展示进度、状态和控制按钮"""

    rm = Signal(str)
    up = Signal(str)
    down = Signal(str)

    def __init__(self, job: Job, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.jid = job.id
        self.setMinimumHeight(78)
        self._build(job)

    def _build(self, job):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        row = QHBoxLayout()
        kind = BodyLabel(f"[{Job.type_name(job.jtype)}]")
        kind.setStyleSheet("color: #6A9955; font-weight: bold;")
        row.addWidget(kind)

        name = StrongBodyLabel(job.name or job.jtype)
        name.setWordWrap(True)
        row.addWidget(name, stretch=1)

        self.st_lbl = BodyLabel(job.state.text)
        self.st_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.st_lbl.setMinimumWidth(80)
        row.addWidget(self.st_lbl)
        lay.addLayout(row)

        summary = self._summary(job)
        if summary:
            detail_row = QHBoxLayout()
            detail = BodyLabel(summary)
            detail.setStyleSheet("color: #858585; font-size: 11px;")
            detail_row.addWidget(detail)
            detail_row.addStretch()
            lay.addLayout(detail_row)

        self.bar = ProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setFixedHeight(6)
        self.bar.setVisible(job.state == JobState.RUN)
        self.bar.setValue(job.pct)
        lay.addWidget(self.bar)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_up = TransparentToolButton(FluentIcon.UP, self)
        self.btn_up.setFixedSize(28, 28)
        self.btn_up.setToolTip("上移")
        self.btn_up.clicked.connect(lambda: self.up.emit(self.jid))
        btn_row.addWidget(self.btn_up)

        self.btn_down = TransparentToolButton(FluentIcon.DOWN, self)
        self.btn_down.setFixedSize(28, 28)
        self.btn_down.setToolTip("下移")
        self.btn_down.clicked.connect(lambda: self.down.emit(self.jid))
        btn_row.addWidget(self.btn_down)

        btn_row.addStretch()
        rm = PushButton(FluentIcon.DELETE, "移除")
        rm.clicked.connect(lambda: self.rm.emit(self.jid))
        btn_row.addWidget(rm)
        lay.addLayout(btn_row)
        self.refresh(job.state, job.pct)

    def _summary(self, job):
        params = job.params
        parts = []
        if job.jtype in ("encode", "vs"):
            enc = params.get("enc_name", params.get("encoder", params.get("enc", "")))
            crf = params.get("crf")
            if enc:
                parts.append(f"编码器: {enc}")
            if crf not in (None, ""):
                parts.append(f"CRF: {crf}")
        elif job.jtype == "mux":
            parts.append(f"模式: {params.get('mode', 'ffmpeg')}")
        elif job.jtype == "clean":
            parts.append(f"模式: {params.get('mode', 'clean')}")
        elif job.jtype == "chapter":
            parts.append(f"章节: {len(params.get('times_ms', []))} 个")
        return "  |  ".join(parts)

    def refresh(self, state, pct=0):
        self.st_lbl.setText(state.text)
        colors = {
            JobState.WAIT: "#858585",
            JobState.RUN: "#DCDCAA",
            JobState.PAUSE: "#DCDCAA",
            JobState.DONE: "#4EC9B0",
            JobState.FAIL: "#F44747",
            JobState.STOP: "#F44747",
        }
        self.st_lbl.setStyleSheet(f"color: {colors.get(state, '#858585')};")
        self.bar.setVisible(state == JobState.RUN)
        self.bar.setValue(pct)
        moving = state == JobState.WAIT
        self.btn_up.setVisible(moving)
        self.btn_down.setVisible(moving)


class QueuePage(QWidget):
    """任务队列页面：展示所有排队/运行中/已完成的任务卡片，支持并发控制和排序"""

    def __init__(self, q: JobQ | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tab_queue")
        self.q = q or JobQ()
        self._cards = {}
        self._ui()
        self._bind()
        self._load()

    def _ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(35, 14, 35, 20)
        lay.setSpacing(12)

        title = TitleLabel("任务队列")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        lay.addWidget(title)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_start = PrimaryPushButton(FluentIcon.PLAY, "启动队列")
        self.btn_start.clicked.connect(self.q.start_queue)
        bar.addWidget(self.btn_start)
        bar.addSpacing(12)

        bar.addWidget(BodyLabel("并发数:"))
        self.sp_n = SpinBox()
        self.sp_n.setRange(1, 8)
        self.sp_n.setValue(1)
        self.sp_n.valueChanged.connect(lambda v: self.q.set_max(v))
        bar.addWidget(self.sp_n)

        bar.addSpacing(16)
        self.btn_p = PushButton(FluentIcon.PAUSE, "全部暂停")
        self.btn_p.clicked.connect(self.q.pause_all)
        bar.addWidget(self.btn_p)

        self.btn_r = PushButton(FluentIcon.PLAY, "全部恢复")
        self.btn_r.clicked.connect(self.q.goon_all)
        bar.addWidget(self.btn_r)

        bar.addStretch()
        self.btn_c = PushButton(FluentIcon.DELETE, "清除已完成")
        self.btn_c.clicked.connect(self.q.clear_done)
        bar.addWidget(self.btn_c)
        lay.addLayout(bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.cw = QWidget()
        self.cl = QVBoxLayout(self.cw)
        self.cl.setSpacing(8)
        self.empty = BodyLabel("队列为空。在其他页面配置好参数后，点击添加到队列。")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cl.addWidget(self.empty)
        self.cl.addStretch()
        scroll.setWidget(self.cw)
        lay.addWidget(scroll, stretch=1)

    def _bind(self):
        self.q.sig.added.connect(self._added)
        self.q.sig.started.connect(self._started)
        self.q.sig.prog.connect(self._prog)
        self.q.sig.ended.connect(self._ended)
        self.q.sig.changed.connect(self._refresh)
        self.q.sig.fail.connect(self._failed)

    def _added(self, jid):
        job = self.q.get(jid)
        if not job:
            return
        card = TaskCard(job)
        card.rm.connect(self.q.remove)
        card.up.connect(lambda tid: self.q.move(tid, -1))
        card.down.connect(lambda tid: self.q.move(tid, 1))
        self._cards[jid] = card
        self.cl.insertWidget(max(0, self.cl.count() - 1), card)
        polish_theme_widgets(card)
        self.empty.setVisible(False)

    def _started(self, jid):
        card = self._cards.get(jid)
        if card:
            card.refresh(JobState.RUN)

    def _prog(self, jid, pct):
        card = self._cards.get(jid)
        if card:
            card.refresh(JobState.RUN, pct)

    def _ended(self, jid, ok):
        card = self._cards.get(jid)
        if card:
            job = self.q.get(jid)
            if job:
                card.refresh(job.state, job.pct)
            else:
                card.refresh(JobState.DONE if ok else JobState.FAIL)

    def _failed(self, text):
        QMessageBox.warning(self.window(), "任务队列未完成", text)

    def _refresh(self):
        jobs = self.q.all()
        job_ids = {job.id for job in jobs}
        
        for jid in list(self._cards.keys()):
            if jid not in job_ids:
                card = self._cards.pop(jid)
                self.cl.removeWidget(card)
                card.deleteLater()

        for job in jobs:
            card = self._cards.get(job.id)
            if card:
                card.refresh(job.state, job.pct)
        active = [j for j in jobs if j.state in (JobState.WAIT, JobState.RUN, JobState.PAUSE)]
        self.empty.setVisible(len(active) == 0)

    def _load(self):
        saved = load_q()
        for job in saved:
            self.q.add(job)
        if saved:
            InfoBar.info(
                "任务恢复",
                f"已恢复 {len(saved)} 个未完成任务，点击“启动队列”后开始执行。",
                position=InfoBarPosition.TOP,
                parent=self.window(), duration=5000,
            )
