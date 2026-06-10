import ctypes, os, sys
from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QObject, QPoint,
    QParallelAnimationGroup, QPropertyAnimation, QRectF, Qt,
)
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QGraphicsOpacityEffect, QHBoxLayout,
    QMessageBox, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    FluentIcon, InfoBar, InfoBarPosition, NavigationInterface,
    NavigationItemPosition, PushButton, Theme, isDarkTheme, setTheme, setThemeColor,
)
from qframelesswindow import FramelessWindow

from core.work import JobQ, Job, JobState
from ui.main_ui import HomePage, SettingsPage
from ui.video_ui import EncodePage
from ui.muxer_ui import MuxPage
from ui.chapter_ui import ChapPage
from ui.fastmuxer_ui import FastMuxPage
from ui.subs_ui import SubsPage
from ui.vs_ui import VSPage
from ui.work_page import QueuePage
from ui.theme import apply_theme_styles
from utils.ffmpeg import find_exe, load_cfg


class Win(FramelessWindow):
    """主窗口，包含导航侧边栏、页面栈、底部操作栏和任务队列集成"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FFmpegEncodeTools")
        self.resize(1280, 900)
        self.setObjectName("MainWindow")
        self.setMinimumSize(1200, 850)
        if os.name == "nt":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HCoo.FFmpegEncodeTools")

        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
        icon_path = base_dir / "config" / "001.ico"
        if not icon_path.exists():
            icon_path = base_dir / "001.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.q = JobQ()
        self.q.sig.all_done.connect(self.on_all_done)

        root_lay = QHBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        side_lay = QVBoxLayout()
        side_lay.setContentsMargins(0, 36, 0, 0)
        side_lay.setSpacing(0)

        self.nav_pnl = QWidget()
        self.nav_pnl.setObjectName("NavPanel")
        nav_lay = QVBoxLayout(self.nav_pnl)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(0)

        self.nav = NavigationInterface(self.nav_pnl, showMenuButton=True, showReturnButton=False)
        self.nav.setStyleSheet("background: transparent;")
        nav_lay.addWidget(self.nav)
        side_lay.addWidget(self.nav_pnl)
        root_lay.addLayout(side_lay)
        self.nav.installEventFilter(self)
        self.last_w = 54
        self.cur_route = "tab_home"

        self.main_w = QWidget(self)
        self.main_w.setObjectName("MainBox")
        self.main_w.setMinimumWidth(800)
        main_lay = QVBoxLayout(self.main_w)
        main_lay.setContentsMargins(0, 36, 0, 0)
        main_lay.setSpacing(0)

        self.stack = QStackedWidget(self)
        main_lay.addWidget(self.stack, stretch=1)

        self.bot_bar = QWidget()
        self.bot_bar.setObjectName("BotBar")
        bot_lay = QVBoxLayout(self.bot_bar)
        bot_lay.setContentsMargins(35, 22, 35, 22)
        bot_lay.setSpacing(12)
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)
        self.run_btn = PushButton(FluentIcon.PLAY, "执行当前任务")
        self.run_btn.setObjectName("btnGo")
        self.run_btn.setFixedHeight(44)
        self.run_btn.clicked.connect(self.run_job)
        self.add_btn = PushButton(FluentIcon.ADD_TO, "添加到队列")
        self.add_btn.setObjectName("btnGo")
        self.add_btn.setFixedHeight(44)
        self.add_btn.clicked.connect(self.add_job)
        btn_lay.addWidget(self.run_btn, stretch=2)
        btn_lay.addWidget(self.add_btn, stretch=1)
        bot_lay.addLayout(btn_lay)
        main_lay.addWidget(self.bot_bar)
        root_lay.addWidget(self.main_w)

        self._setup()
        self.apply_theme()
        self.titleBar.raise_()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """导航侧边栏伸缩时自动调整窗口宽度"""
        if watched == self.nav and event.type() == QEvent.Type.Resize:
            nw = self.nav.width()
            dw = nw - self.last_w
            mw = nw + 1066

            old_w = self.width()
            self.setMinimumWidth(mw)

            if not self.isMaximized() and not self.isFullScreen() and dw != 0:
                EXPAND_THRESHOLD = 1150
                COLLAPSE_THRESHOLD = 1400
                TARGET_EXPANDED = 1380
                TARGET_COLLAPSED = 1120

                if dw > 0 and old_w < EXPAND_THRESHOLD:
                    self.resize(max(TARGET_EXPANDED, mw), self.height())
                elif dw < 0 and old_w <= COLLAPSE_THRESHOLD:
                    new_w = max(old_w + dw, TARGET_COLLAPSED, mw)
                    self.resize(new_w, self.height())

            self.last_w = nw
        return super().eventFilter(watched, event)

    def _setup(self) -> None:
        """初始化所有页面和导航项"""
        self.home_pg = HomePage()
        self.enc_pg = EncodePage()
        self.mux_pg = MuxPage()
        self.fmux_pg = FastMuxPage()
        self.clean_pg = SubsPage()
        self.chap_pg = ChapPage()
        self.vs_pg = VSPage()
        self.q_pg = QueuePage(self.q)
        self.cfg_pg = SettingsPage()

        self.pg_map = {}
        self.pg_widgets = {}

        # 子界面标题
        self.reg_pg(self.home_pg, FluentIcon.HOME, "主页")
        self.reg_pg(self.enc_pg, FluentIcon.VIDEO, "视频压制")
        self.reg_pg(self.mux_pg, FluentIcon.SYNC, "混流封装")
        self.reg_pg(self.fmux_pg, FluentIcon.SPEED_HIGH, "MP4快速封装")
        self.reg_pg(self.clean_pg, FluentIcon.DOCUMENT, "字幕清洗")
        self.reg_pg(self.chap_pg, FluentIcon.TAG, "章节封装")
        self.reg_pg(self.vs_pg, FluentIcon.CODE, "VapourSynth压制")
        self.nav.addSeparator()
        self.reg_pg(self.q_pg, FluentIcon.ALIGNMENT, "任务队列")
        self.nav.addSeparator(position=NavigationItemPosition.BOTTOM)
        self.nav.addItem(
            routeKey="theme",
            icon=self.get_theme_ico(),
            text="切换主题",
            position=NavigationItemPosition.BOTTOM,
            selectable=False,
            onClick=self.toggle_theme,
        )
        self.reg_pg(self.cfg_pg, FluentIcon.SETTING, "系统设置", NavigationItemPosition.BOTTOM)

        self.stack.setCurrentWidget(self.pg_map["tab_home"])
        self.nav.setCurrentItem("tab_home")
        self.bot_bar.setVisible(False)
        self.home_pg.go.connect(self.go_to)

    def reg_pg(self, w: QWidget, icon: FluentIcon, text: str, pos: NavigationItemPosition = NavigationItemPosition.TOP) -> None:
        """注册一个页面到侧边导航和页面栈中"""
        sc = QScrollArea(self)
        sc.setWidgetResizable(True)
        sc.setFrameShape(QScrollArea.Shape.NoFrame)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sc.setObjectName(f"{w.objectName()}_scroll")
        sc.setWidget(w)
        self.stack.addWidget(sc)
        self.pg_map[w.objectName()] = sc
        self.pg_widgets[w.objectName()] = w
        self.nav.addItem(
            routeKey=w.objectName(), icon=icon, text=text, position=pos,
            onClick=lambda: self.go_to(w.objectName()),
        )

    def go_to(self, route: str) -> None:
        """带滑动动画的页面切换"""
        if route not in self.pg_map:
            return

        nw = self.pg_map[route]
        ow = self.stack.currentWidget()
        if ow is nw:
            return
        oi = self.stack.indexOf(ow)
        ni = self.stack.indexOf(nw)
        d = 1 if ni > oi else -1

        self.bot_bar.setVisible(route not in ["tab_home", "tab_settings", "tab_queue"])
        self.nav.setCurrentItem(route)
        self.stack.setCurrentIndex(ni)
        self.cur_route = route

        self._anim = QParallelAnimationGroup(self)
        pa = QPropertyAnimation(nw, b"pos")
        pa.setDuration(400)
        pa.setEasingCurve(QEasingCurve.Type.OutQuart)
        pa.setStartValue(QPoint(0, 50 * d))
        pa.setEndValue(QPoint(0, 0))
        fx = QGraphicsOpacityEffect(nw)
        nw.setGraphicsEffect(fx)
        fa = QPropertyAnimation(fx, b"opacity")
        fa.setDuration(350)
        fa.setStartValue(0.0)
        fa.setEndValue(1.0)
        self._anim.addAnimation(pa)
        self._anim.addAnimation(fa)
        self._anim.finished.connect(lambda: nw.setGraphicsEffect(None))
        self._anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def apply_theme(self) -> None:
        """应用当前主题样式"""
        apply_theme_styles(self)

    def toggle_theme(self) -> None:
        """切换暗色/亮色主题"""
        route = self.cur_route
        if isDarkTheme():
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)
            setThemeColor("#39C5BB")
        self.apply_theme()
        self.up_theme_ico()
        if route in self.pg_map:
            self.nav.setCurrentItem(route)

    def get_theme_ico(self) -> QIcon:
        """绘制日/夜模式切换图标"""
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor("#F5F5F5") if isDarkTheme() else QColor("#1E1E1E")
        p.setPen(QPen(c, 2))
        if isDarkTheme():
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(8, 6, 16, 20))
            p.setBrush(QBrush(QColor("#252526")))
            p.drawEllipse(QRectF(14, 3, 16, 22))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(11, 11, 10, 10))
            for x1, y1, x2, y2 in [
                (16,3,16,7),(16,25,16,29),(3,16,7,16),(25,16,29,16),
                (7,7,10,10),(22,22,25,25),(25,7,22,10),(10,22,7,25),
            ]:
                p.drawLine(x1, y1, x2, y2)
        p.end()
        return QIcon(pm)

    def up_theme_ico(self) -> None:
        """刷新侧边栏主题切换按钮的图标"""
        wg = getattr(self.nav, "widget", None)
        if not callable(wg):
            return
        it = wg("theme")
        if it and hasattr(it, "setIcon"):
            it.setIcon(self.get_theme_ico())  # pyright: ignore[reportAttributeAccessIssue]

    def run_job(self) -> None:
        """执行当前页面的任务（弹窗模式）"""
        cur = self.stack.currentWidget()
        cur = self.pg_widgets.get(self.cur_route, cur)
        if not hasattr(cur, "get_job"):
            return
        jt, p = cur.get_job()
        if not jt:
            if p:
                QMessageBox.warning(self, "信息缺失", p)
            return
        if jt in ["encode", "mux", "chapter"] and find_exe("ffmpeg") is None:
            QMessageBox.critical(self, "环境缺失", "没找到 FFmpeg，请先在系统设置里配置路径。")
            return

        from core.work import Runner
        from ui.main_ui import TaskDialog
        self.run_btn.setEnabled(False)
        self.run_btn.setText("任务执行中...")
        self._runner = Runner(jt, p)
        self._dlg = TaskDialog(self, self._runner)
        self._runner.sig.done.connect(self.on_run_done)
        self._runner.start()
        self._dlg.exec()

    def on_run_done(self) -> None:
        """单任务执行完成回调"""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("执行当前任务")
        self.post_task(is_q=False)

    def on_all_done(self) -> None:
        """队列全部完成回调"""
        self.post_task(is_q=True)

    def post_task(self, is_q: bool = True) -> None:
        """任务完成后的预设动作（通知/打开文件夹/退出/关机）"""
        cfg = load_cfg()
        action = cfg.get("post_task_action", "无动作")
        if action == "无动作":
            return

        if action == "系统通知":
            self.showNormal()
            self.raise_()
            self.activateWindow()
            msg = "任务队列已全部执行完毕！" if is_q else "压制任务已执行完毕！"
            QMessageBox.information(self, "提示", msg)

        elif action == "打开输出文件夹":
            out_dir = None
            if is_q:
                for job in reversed(self.q.all()):
                    if job.state == JobState.DONE:
                        params = job.params
                        p = params.get("out") or params.get("output") or params.get("out_dir")
                        if p:
                            path = Path(p)
                            if path.is_file():
                                out_dir = str(path.parent.resolve())
                            elif path.is_dir():
                                out_dir = str(path.resolve())
                            break
            else:
                cur = self.stack.currentWidget()
                cur = self.pg_widgets.get(self.cur_route, cur)
                if hasattr(cur, "out_in"):
                    p = cur.out_in.text().strip()
                    if p:
                        path = Path(p)
                        if path.parent.exists():
                            out_dir = str(path.parent.resolve())

            if not out_dir:
                out_dir = os.getcwd()

            if out_dir:
                try:
                    os.startfile(out_dir)
                except Exception:
                    pass

        elif action == "退出软件":
            self.close()

        elif action == "关机":
            self.showNormal()
            self.raise_()
            self.activateWindow()

            from ui.main_ui import ShutdownCountdownDialog
            dlg = ShutdownCountdownDialog(self)
            dlg.exec()

    def add_job(self) -> None:
        """将当前页面的任务添加到后台队列支持多文件拆分"""
        cur = self.stack.currentWidget()
        cur = self.pg_widgets.get(self.cur_route, cur)
        if not hasattr(cur, "get_job"):
            return
        jt, p = cur.get_job()
        if not jt:
            if p:
                QMessageBox.warning(self, "信息缺失", p)
            return
        if jt in ["encode", "mux", "chapter"] and find_exe("ffmpeg") is None:
            QMessageBox.critical(self, "环境缺失", "没找到 FFmpeg，请先在系统设置里配置路径。")
            return

        if jt == "encode" and len(p.get("vid_list", [])) > 1:
            vid_list = p["vid_list"]
            for vp in vid_list:
                single_p = dict(p)
                single_p["vid_list"] = [vp]
                job = Job(jtype=jt, name=f"压制 {vp.name}", params=single_p)
                self.q.add(job)
            InfoBar.success("已添加", f"已拆分 {len(vid_list)} 个压制任务加入队列",
                            position=InfoBarPosition.TOP, parent=self)
        else:
            job = Job(jtype=jt, name=Job.type_name(jt), params=p)
            self.q.add(job)
            InfoBar.success("已添加", f"任务已加入队列（共 {len(self.q.all())} 个）",
                            position=InfoBarPosition.TOP, parent=self)


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    setTheme(Theme.LIGHT)
    setThemeColor("#39C5BB") # 初音未来应援色
    win = Win()
    win.show()

    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    sys.exit(app.exec())
