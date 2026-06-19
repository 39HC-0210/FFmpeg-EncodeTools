import os, re, subprocess, shutil, json, time
from pathlib import Path
from typing import Any, Callable

from config import ROOT, SET_FILE


def warn(msg: str) -> None:
    """输出红色警告信息到控制台"""
    print(f"\033[91m{msg}\033[0m")


def info(msg: str) -> None:
    """输出绿色提示信息到控制台"""
    print(f"\033[92m{msg}\033[0m")


def load_cfg() -> dict[str, Any]:
    """加载配置文件，对缺失的键补入默认值

    Returns:
        dict: 合并默认值后的配置字典
    """
    cfg: dict[str, Any] = {}
    if SET_FILE.exists():
        try:
            with open(SET_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            pass

    defaults = {
        # 以下为默认配置，可以根据需要修改
        "ffmpeg_path": ".\\EncodeTools\\ffmpeg.exe",
        "ffprobe_path": ".\\EncodeTools\\ffprobe.exe",
        "mp4box_path": "",
        "vspipe_path": ".\\EncodeTools\\Vapoursynth\\vspipe.exe",
        "x265_path": ".\\EncodeTools\\x265.exe",
        "x264_path": "",
        "v_enc": "libx264",
        "v_crf": 11.0,
        "a_enabled": False,
        "a_ok": False,
        "a_enc": "aac",
        "adv_ok": False,
        "v_pre": "medium",
        "a_sr": "保持原始采样率",
        "if_fail": "继续处理任务并最终反馈错误清单",
        "temp_vpy_dir": ".\\vpy\\temp",
        "del_temp_vpy": False,
        "enc_temp_dir": ".\\enc\\temp",
        "del_temp_enc": False,
    }
    for k, v in defaults.items():
        if k not in cfg:
            cfg[k] = v
    return cfg

def save_cfg(cfg: dict[str, Any]) -> None:
    """将配置字典写入 JSON 配置文件"""
    with open(SET_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def set_cfg(key: str, val: Any) -> None:
    """设置单个配置项并持久化

    Args:
        key: 配置键名
        val: 配置值
    """
    cfg = load_cfg()
    cfg[key] = val
    save_cfg(cfg)


def bind_cfg(widget: Any, key: str, default_val: Any) -> None:
    """将 GUI 控件与配置文件单项双向绑定

    控件值变化时自动写回配置；初始化时从配置读取值设置到控件

    Args:
        widget: qfluentwidgets 输入控件（ComboBox/SpinBox/DoubleSpinBox/CheckBox）
        key: 配置键名
        default_val: 配置不存在时的回退值
    """
    from qfluentwidgets import ComboBox, SpinBox, DoubleSpinBox, CheckBox
    cfg = load_cfg()
    val = cfg.get(key, default_val)

    if isinstance(widget, ComboBox):
        idx = widget.findText(str(val))
        if idx >= 0:
            widget.setCurrentIndex(idx)
        else:
            widget.setCurrentText(str(default_val))
            set_cfg(key, default_val)
        widget.currentTextChanged.connect(lambda t: set_cfg(key, t))
    elif isinstance(widget, DoubleSpinBox):
        widget.setValue(float(val))
        widget.valueChanged.connect(lambda v: set_cfg(key, v))
    elif isinstance(widget, SpinBox):
        widget.setValue(int(val))
        widget.valueChanged.connect(lambda v: set_cfg(key, v))
    elif isinstance(widget, CheckBox):
        widget.setChecked(bool(val))
        widget.toggled.connect(lambda c: set_cfg(key, c))

def _resolve_path(path_str: str) -> str | None:
    """解析相对或绝对路径，返回存在的文件路径或 None"""
    if not path_str:
        return None
    if path_str.startswith(".\\") or path_str.startswith("./"):
        p = ROOT / path_str
        if p.is_file():
            return str(p.resolve())
    else:
        if Path(path_str).is_file():
            return path_str
    return None


def find_exe(name: str) -> str | None:
    """查找可执行文件路径

    优先级：配置文件路径 > FFmpeg 同目录推导 > 系统 PATH

    Args:
        name: 工具名（如 "ffmpeg", "ffprobe", "x264", "x265"）

    Returns:
        可执行文件路径，找不到返回 None
    """
    cfg = load_cfg()
    path = cfg.get(f"{name}_path", "").strip()
    res = _resolve_path(path)
    if res:
        return res

    if name == "ffprobe":
        ffmpeg_path = _resolve_path(cfg.get("ffmpeg_path", "").strip()) or shutil.which("ffmpeg")
        if ffmpeg_path:
            p = Path(ffmpeg_path).parent / "ffprobe.exe"
            if p.is_file():
                return str(p.resolve())
    elif name in ["x264", "x265"]:
        vspipe_path = _resolve_path(cfg.get("vspipe_path", "").strip()) or shutil.which("vspipe")
        if vspipe_path:
            p = Path(vspipe_path).parent / f"{name}.exe"
            if p.is_file():
                return str(p.resolve())

    return shutil.which(name)

def uniq_out(out_dir: Path, base_name: str, ext: str) -> Path:
    """生成不重复的输出文件路径

    首次生成 `{base_name}_output{ext}`，冲突时追加 `~1`, `~2` …

    Args:
        out_dir: 输出目录
        base_name: 基础文件名（不含扩展名）
        ext: 文件扩展名（含点号）

    Returns:
        不冲突的输出文件 Path
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    while True:
        name = f"{base_name}_output{ext}" if n == 0 else f"{base_name}_output~{n}{ext}"
        p = out_dir / name
        if not p.exists():
            return p
        n += 1

def fmt_dur(sec: float) -> str:
    """将秒数格式化为 HH:MM:SS.mmm 时间字符串

    Args:
        sec: 秒数（可带小数）

    Returns:
        格式为 ``00:00:00.000`` 的时间字符串
    """
    h, m, s = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def read_txt(path: str) -> tuple[str, list[str]]:
    """尝试多种编码读取文本文件

    Args:
        path: 文件路径

    Returns:
        (完整文本内容, 按行分割的列表)

    Raises:
        ValueError: 所有编码均失败
    """
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'ansi']:
        try:
            with open(path, 'r', encoding=enc) as f:
                content = f.read()
                return content, content.splitlines(keepends=True)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别文件编码：{path}")

def get_vinfo(vpath: Path, save_json: bool = False) -> dict[str, Any]:
    """调用 ffprobe 获取视频信息

    Args:
        vpath: 视频文件路径
        save_json: 是否将原始 ffprobe JSON 保存到配置文件目录

    Returns:
        包含 ``dur_ms``, ``cspace``, ``crange`` 键的字典；
        若 ``save_json=True`` 还会包含 ``raw_json`` 键指向 JSON 文件路径
    """
    if not isinstance(vpath, Path):
        vpath = Path(vpath)
    if not vpath.is_file():
        return {'dur_ms': None, 'cspace': None, 'crange': None}

    fp = find_exe("ffprobe") or "ffprobe"
    try:
        c_flag = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        cmd = [fp, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(vpath)]
        data = json.loads(subprocess.run(cmd, capture_output=True, encoding='utf-8',
                                         check=True, creationflags=c_flag).stdout)
        dur_ms = int(float(data.get('format', {}).get('duration', 0)) * 1000)
        cspace = crange = None
        for s in data.get('streams', []):
            if s.get('codec_type') == 'video':
                cspace = s.get('color_space')
                crange = s.get('color_range')
                break
        if cspace and cspace.lower() == 'unknown':
            cspace = None
        if crange and crange.lower() == 'unknown':
            crange = None
        res = {'dur_ms': dur_ms, 'cspace': cspace, 'crange': crange}
        if save_json:
            from config import CFG_DIR
            jp = CFG_DIR / f"{vpath.stem}.json"
            with open(jp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            res['raw_json'] = str(jp)
        return res
    except Exception as e:
        warn(f"无法获取视频信息：{e}")
        return {'dur_ms': None, 'cspace': None, 'crange': None, 'raw_json': None}

def get_vdur(vpath: Path) -> int | None:
    """获取视频时长（毫秒）

    Args:
        vpath: 视频文件路径

    Returns:
        时长毫秒数，失败返回 None
    """
    return get_vinfo(vpath).get('dur_ms')


def run_ff(
    cmd_list: list[str],
    desc: str,
    dur_ms: int = 0,
    worker: Any = None,
    log_cb: Callable[..., None] | None = None,
    status_prefix: str = "",
) -> bool:
    """执行 FFmpeg 命令并实时解析进度

    Args:
        cmd_list: FFmpeg 命令行参数列表
        desc: 任务描述，用于日志前缀
        dur_ms: 视频总时长（毫秒），为 0 时不计算进度百分比
        worker: Runner 实例，用于取消/暂停控制
        log_cb: 日志回调函数，签名为 ``(line: str, pct: int, status_desc: str | None)``
        status_prefix: 进度状态行前缀

    Returns:
        True 表示 FFmpeg 正常退出（返回码 0），False 表示失败或被取消
    """
    info(f"\n正在{desc}：")
    c_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, creationflags=c_flags,
                                encoding='utf-8', errors='replace')
        if worker:
            worker.process = proc

        t_pat = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        start_time = time.time()
        assert proc.stdout is not None
        for line in proc.stdout:
            if worker and worker.is_cancelled:
                break
            line = line.strip()
            if not line:
                continue
            pct = -1
            status_desc = None
            if dur_ms > 0:
                m = t_pat.search(line)
                if m:
                    h, mi, s = m.groups()
                    cur = (int(h) * 3600 + int(mi) * 60 + float(s)) * 1000
                    pct = min(100, int((cur / dur_ms) * 100))

                    fps_match = re.search(r"fps=\s*([\d\.]+)", line)
                    speed_match = re.search(r"speed=\s*([\d\.]+)x", line)
                    fps_val = fps_match.group(1) if fps_match else None
                    speed_val = speed_match.group(1) if speed_match else None

                    elapsed = time.time() - start_time
                    eta_str = ""
                    if pct > 0:
                        total_est = elapsed / (pct / 100.0)
                        eta_sec = max(0, int(total_est - elapsed))
                        h_eta = eta_sec // 3600
                        m_eta = (eta_sec % 3600) // 60
                        s_eta = eta_sec % 60
                        if h_eta > 0:
                            eta_str = f"{h_eta:02d}:{m_eta:02d}:{s_eta:02d}"
                        else:
                            eta_str = f"{m_eta:02d}:{s_eta:02d}"

                    metrics = []
                    if fps_val:
                        metrics.append(f"帧率: {fps_val} fps")
                    if speed_val:
                        metrics.append(f"速度: {speed_val}x")
                    if eta_str:
                        metrics.append(f"剩余时间: {eta_str}")

                    metric_str = " | ".join(metrics)
                    prefix = status_prefix if status_prefix else desc
                    if metric_str:
                        status_desc = f"{prefix} ({pct}%) [{metric_str}]"
                    else:
                        status_desc = f"{prefix} ({pct}%)"

            if log_cb:
                try:
                    log_cb(line, pct, status_desc)
                except TypeError:
                    log_cb(line, pct)
            else:
                print(line)

        proc.wait()
        if worker and worker.is_cancelled:
            msg = "[取消] 用户取消任务"
            if log_cb:
                log_cb(msg, -1)
            else:
                print(msg)
            return False
        if proc.returncode != 0:
            msg = f"[错误] {desc} 执行失败，退出码：{proc.returncode}"
            if log_cb:
                log_cb(msg, -1)
            else:
                warn(msg)
            return False
        return True
    except Exception as e:
        msg = f"外部命令执行崩溃: {e}"
        if log_cb:
            log_cb(f"[错误] {msg}", -1)
        else:
            warn(msg)
        return False
    finally:
        if worker:
            worker.process = None
