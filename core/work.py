import os
import json
import ctypes
import subprocess
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from threading import Lock
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal, QObject
from config import CFG_DIR

QUEUE_FILE = CFG_DIR / "task_queue.json"


class JobState(Enum):
    """任务状态枚举"""
    WAIT = "pending"
    RUN = "running"
    PAUSE = "paused"
    DONE = "done"
    FAIL = "failed"
    STOP = "cancelled"

    @property
    def icon(self) -> str:
        return ""

    @property
    def text(self) -> str:
        """返回状态的中文显示文本"""
        m = {"pending": "等待中", "running": "进行中", "paused": "已暂停", "done": "已完成", "failed": "失败", "cancelled": "已取消"}
        return m.get(self.value, self.value)


@dataclass
class Job:
    """任务数据类，支持 JSON 序列化/反序列化"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    jtype: str = ""
    name: str = ""
    params: dict = field(default_factory=dict)
    state: JobState = JobState.WAIT
    pct: int = 0
    log: list = field(default_factory=list)
    err: str = ""
    made_at: str = field(default_factory=lambda: datetime.now().isoformat())
    done_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于 JSON 持久化）"""
        return {"id": self.id, "task_type": self.jtype, "display_name": self.name,
                "params": self.params, "status": self.state.value, "created_at": self.made_at}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Job":
        """从字典反序列化为 Job 实例"""
        try:
            st = JobState(d.get("status", "pending"))
        except ValueError:
            st = JobState.WAIT
        return cls(id=d.get("id", ""), jtype=d.get("task_type", ""),
                   name=d.get("display_name", ""), params=d.get("params", {}),
                   state=st, made_at=d.get("created_at", ""))

    @staticmethod
    def type_name(jtype: str) -> str:
        """返回任务类型的中文显示名"""
        m = {"encode": "视频压制", "mux": "混流封装", "mux_ff": "混流封装", "fast_mux": "MP4快速封装",
             "clean": "字幕清洗", "chapter": "章节封装", "vs": "VapourSynth压制"}
        return m.get(jtype, jtype)


def suspend_process(pid: int) -> None:
    """通过 Windows API 挂起进程（仅 Windows）"""
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x0800, False, pid)
        if handle:
            ctypes.windll.ntdll.NtSuspendProcess(handle)
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


def resume_process(pid: int) -> None:
    """通过 Windows API 恢复挂起的进程（仅 Windows）"""
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x0800, False, pid)
        if handle:
            ctypes.windll.ntdll.NtResumeProcess(handle)
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


class RunnerSig(QObject):
    """Runner 的信号集合"""
    log = Signal(str)
    done = Signal()
    err = Signal(str)
    prog = Signal(int, str)


class Runner(QThread):
    """任务执行线程

    根据 jtype 分发到不同的编码/混流/清洗/章节/VS 函数
    支持暂停、恢复、取消操作
    """

    def __init__(self, jtype: str, params: dict[str, Any]):
        super().__init__()
        self.jtype: str = jtype
        self.params: dict[str, Any] = params
        self.sig: RunnerSig = RunnerSig()
        self.paused: bool = False
        self.cancelled: bool = False
        self.processes: list[subprocess.Popen] = []

    @property
    def process(self) -> subprocess.Popen | None:
        """当前关联的子进程（取第一个）"""
        return self.processes[0] if self.processes else None

    @process.setter
    def process(self, proc: subprocess.Popen | None) -> None:
        if proc is None:
            self.processes.clear()
        else:
            self.processes = [proc]

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled

    def pause(self) -> None:
        """暂停任务（挂起关联的子进程）"""
        self.paused = True
        if os.name == "nt":
            for p in self.processes:
                suspend_process(p.pid)

    def goon(self) -> None:
        """恢复暂停的任务"""
        self.paused = False
        if os.name == "nt":
            for p in self.processes:
                resume_process(p.pid)

    def stop(self) -> None:
        """取消任务并终止关联子进程"""
        self.cancelled = True
        self.paused = False
        if os.name == "nt":
            for p in self.processes:
                resume_process(p.pid)
        for p in self.processes:
            try:
                p.terminate()
            except Exception:
                pass

    def log(self, line: str, pct: int, status_desc: str | None = None) -> None:
        """发出日志和进度信号"""
        if pct >= 0:
            desc = status_desc if status_desc else line
            self.sig.prog.emit(pct, desc)
        self.sig.log.emit(line)

    def run(self) -> None:
        """线程运行入口：按 jtype 分发到对应的工具函数"""
        if self.jtype in ["encode", "mux", "mux_ff", "fast_mux", "chapter", "vs"]:
            self.params['worker'] = self

        try:
            if self.jtype == "encode":
                from core.tools.encode_videos import encode
                encode(**self.params)
            elif self.jtype == "clean":
                from core.tools.subs_clean import clean_subs
                single = len(self.params['vid_list']) == 1
                total = len(self.params['vid_list'])
                for idx, p in enumerate(self.params['vid_list']):
                    if self.cancelled:
                        break
                    pct = int((idx / total) * 100)
                    self.log(f"正在清洗字幕 ({idx+1}/{total}): {p.name}", pct)
                    clean_subs(p, self.params['mode'], self.params['split_n'],
                               self.params['out_dir'], single)
                self.log("所有字幕清洗完成", 100)
            elif self.jtype == "mux":
                from core.tools.muxer import mux
                mux(**self.params)
            elif self.jtype == "fast_mux":
                from core.tools.muxer import mux
                mux(**self.params)
            elif self.jtype == "mux_ff":
                from core.tools.muxer import mux_ff
                mux_ff(**self.params)
            elif self.jtype == "chapter":
                from core.tools.chaper_into import inject_chap
                inject_chap(**self.params)
            elif self.jtype == "vs":
                from core.vapoursynth.vs_pipe import run_vs_cli, run_vs_ff
                scr = self.params["scr"]
                out = self.params["out"]
                enc = self.params["enc"]
                enc_p = self.params["enc_p"]
                mode = self.params["_mode"]
                if mode == "ffmpeg":
                    ok = run_vs_ff(scr, out, enc, enc_p, self)
                else:
                    ok = run_vs_cli(scr, out, enc, enc_p, self)
                if not ok:
                    raise Exception("VapourSynth压制管道执行失败")

            self.sig.log.emit("\n>>> 任务完成 <<<")
        except Exception as e:
            self.sig.err.emit(str(e))
        finally:
            self.sig.done.emit()


class QSig(QObject):
    """JobQ 的信号集合"""
    added = Signal(str)
    started = Signal(str)
    prog = Signal(str, int)
    log = Signal(str, str)
    ended = Signal(str, bool)
    changed = Signal()
    all_done = Signal()


class JobQ:
    """线程安全的任务队列，支持持久化、并发控制、暂停/恢复"""

    def __init__(self, max_run: int = 1):
        self._q: list[Job] = []
        self._lk = Lock()
        self.max_run: int = max_run
        self._running: dict[str, Runner] = {}
        self._enabled: bool = False
        self.sig: QSig = QSig()

    def add(self, job: Job) -> None:
        """添加任务到队列"""
        with self._lk:
            self._q.append(job)
        self.sig.added.emit(job.id)
        self.sig.changed.emit()
        self._save()

    def remove(self, jid: str) -> bool:
        """从队列中移除指定任务正在运行的任务会被取消"""
        stop_w = None
        changed = False
        with self._lk:
            for t in self._q:
                if t.id == jid and t.state == JobState.RUN:
                    stop_w = self._running.get(jid)
                    break
            
            before = len(self._q)
            self._q = [t for t in self._q if t.id != jid]
            if len(self._q) < before:
                changed = True
        
        if stop_w:
            stop_w.stop()
            
        if changed:
            self.sig.changed.emit()
            self._save()
            return True
            
        return False

    def move(self, jid: str, d: int) -> None:
        """在队列中上移/下移任务

        Args:
            jid: 任务 ID
            d: 偏移量，负值上移，正值下移
        """
        with self._lk:
            for i, t in enumerate(self._q):
                if t.id == jid:
                    ni = i + d
                    if 0 <= ni < len(self._q):
                        self._q[i], self._q[ni] = self._q[ni], self._q[i]
                    break
        self.sig.changed.emit()

    def clear_done(self) -> None:
        """清除所有已完成/失败/取消的任务"""
        with self._lk:
            self._q = [t for t in self._q
                       if t.state in (JobState.WAIT, JobState.RUN, JobState.PAUSE)]
        self.sig.changed.emit()
        self._save()

    def all(self) -> list[Job]:
        """返回队列中所有任务的副本"""
        with self._lk:
            return list(self._q)

    def get(self, jid: str) -> Job | None:
        """按 ID 获取任务"""
        for t in self._q:
            if t.id == jid:
                return t
        return None

    def _next(self) -> None:
        """取出下一个等待任务并启动"""
        job = None
        with self._lk:
            if not self._enabled:
                return
            if len(self._running) >= self.max_run:
                return
            for t in self._q:
                if t.state == JobState.WAIT:
                    t.state = JobState.RUN
                    job = t
                    break
        if job:
            self._go(job)
            self._save()

    def _go(self, job: Job) -> None:
        """启动一个任务的 Runner 线程并连接信号"""
        r = Runner(job.jtype, dict(job.params))
        self._running[job.id] = r

        def on_log(msg, jid=job.id):
            job.log.append(msg)
            self.sig.log.emit(jid, msg)

        def on_prog(pct, _msg, jid=job.id):
            job.pct = pct if pct >= 0 else job.pct
            self.sig.prog.emit(jid, job.pct)

        def on_done(jid=job.id):
            w = self._running.pop(jid, None)
            ok = bool(w and not getattr(w, "cancelled", False) and not getattr(w, "_err", False))
            self._finish(jid, ok)

        def on_err(err, jid=job.id):
            w = self._running.get(jid)
            if w:
                setattr(w, "_err", True)
            job.err = err
            self.sig.log.emit(jid, f"[错误] {err}")

        r.sig.log.connect(on_log)
        r.sig.prog.connect(on_prog)
        r.sig.done.connect(on_done)
        r.sig.err.connect(on_err)

        r.start()
        self.sig.started.emit(job.id)
        self.sig.changed.emit()

    def _finish(self, jid: str, ok: bool) -> None:
        """标记任务完成并触发下一个"""
        with self._lk:
            for t in self._q:
                if t.id == jid:
                    t.state = JobState.DONE if ok else JobState.FAIL
                    t.done_at = datetime.now().isoformat()
                    break
        self.sig.ended.emit(jid, ok)
        self.sig.changed.emit()
        self._save()
        self._next()

        with self._lk:
            is_all_finished = len(self._running) == 0 and not any(t.state == JobState.WAIT for t in self._q)
        if is_all_finished and self._enabled:
            self._enabled = False
            self.sig.all_done.emit()

    def start_queue(self) -> None:
        """启动队列调度"""
        self._enabled = True
        self._next()

    def pause_all(self) -> None:
        """暂停所有正在运行的任务"""
        with self._lk:
            for jid, r in list(self._running.items()):
                r.pause()
                for t in self._q:
                    if t.id == jid:
                        t.state = JobState.PAUSE
        self.sig.changed.emit()

    def goon_all(self) -> None:
        """恢复所有暂停的任务并重新启动调度"""
        self._enabled = True
        with self._lk:
            for jid, r in list(self._running.items()):
                r.goon()
                for t in self._q:
                    if t.id == jid:
                        t.state = JobState.RUN
        self.sig.changed.emit()
        self._next()



    def set_max(self, n: int) -> None:
        """设置最大并发数（1-8）"""
        self.max_run = max(1, min(n, 8))
        if self._enabled:
            self._next()



    def _save(self) -> None:
        """将未完成任务持久化到 JSON 文件"""
        try:
            items = [t.to_dict() for t in self._q
                     if t.state in (JobState.WAIT, JobState.PAUSE)]
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def load_q() -> list[Job]:
    """从持久化文件恢复未完成的任务列表"""
    if not QUEUE_FILE.exists():
        return []
    try:
        data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        return [Job.from_dict(d) for d in data]
    except Exception:
        return []



