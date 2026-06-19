import subprocess, os, re, shutil, shlex
from pathlib import Path
from typing import Any

from utils.ffmpeg import find_exe

PARAM_MAP = {
    "preset":"--preset","tune":"--tune","crf":"--crf",
    "output_depth":"--output-depth","ctu":"--ctu","bframes":"--bframes",
    "ref":"--ref","me":"--me","subme":"--subme","merange":"--merange",
    "aq_mode":"--aq-mode","aq_strength":"--aq-strength",
    "psy_rd":"--psy-rd","psy_rdoq":"--psy-rdoq","deblock":"--deblock",
    "sao":"--sao","no_sao":"--no-sao","keyint":"--keyint",
    "min_keyint":"--min-keyint","open_gop":"--open-gop",
    "rd":"--rd","rdoq_level":"--rdoq-level",
    "strong_intra_smoothing":"--strong-intra-smoothing",
}


def _find_vs(name: str) -> str:
    """查找 VapourSynth 工具路径，优先配置搜索，再检查常见安装位置

    Args:
        name: 工具名（如 "vspipe", "x264", "x265"）

    Returns:
        可执行文件路径，找不到则返回原始名称
    """
    p = find_exe(name)
    if p and os.path.isfile(p):
        return p
    cands = {
        "vspipe": [
            r"C:\Program Files\VapourSynth\vspipe.exe",
            r"C:\Program Files (x86)\VapourSynth\vspipe.exe",
        ],
    }
    for fb in cands.get(name, []):
        if os.path.isfile(fb):
            return fb
    return name


def run_vs_cli(
    scr: str,
    out: str,
    enc: str,
    enc_p: dict[str, Any],
    worker: Any = None,
) -> bool:
    """使用 vspipe 管道直连 x264/x265 CLI 编码器

    Args:
        scr: VapourSynth 脚本文件路径
        out: 输出文件路径
        enc: 编码器名（"x264" 或 "x265"）
        enc_p: 编码参数字典
        worker: Runner 实例

    Returns:
        True 表示编码成功
    """
    enc_exe = _find_vs(enc)
    vs_exe = _find_vs("vspipe")

    if worker:
        worker.sig.log.emit(f"[配置] vspipe: {vs_exe}")
        worker.sig.log.emit(f"[配置] {enc}: {enc_exe}")

    enc_cmd = [enc_exe, "--y4m", "-"]
    for k, v in enc_p.items():
        if k == "extra_args":
            continue
        flag = PARAM_MAP.get(k)
        if flag and v is not None:
            if isinstance(v, bool):
                if v:
                    enc_cmd.append(flag)
            else:
                enc_cmd.append(flag)
                enc_cmd.append(str(v))
    extra = enc_p.get("extra_args", "")
    if extra:
        enc_cmd.extend(shlex.split(str(extra)))
    enc_cmd.extend(["-o", str(out)])

    c_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    vs_cmd = [vs_exe, "--y4m", str(scr), "-"]

    if worker:
        full_cmd_str = f"{' '.join(vs_cmd)} | {' '.join(enc_cmd)}"
        worker.sig.log.emit(f"[命令] {full_cmd_str}")

    try:
        vs_p = subprocess.Popen(vs_cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, creationflags=c_flag,
                                text=True, errors="replace")
        enc_proc = subprocess.Popen(enc_cmd, stdin=vs_p.stdout,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 creationflags=c_flag, text=True, errors="replace")
        if worker:
            worker.processes = [vs_p, enc_proc]
        assert vs_p.stdout is not None
        vs_p.stdout.close()

        fps_pat = re.compile(r"(\d+\.?\d*)\s+fps")
        total_f = enc_p.get("_total_frames", 0)
        frame_pat = re.compile(r"(\d+)\s+frames")

        assert enc_proc.stdout is not None
        for line in enc_proc.stdout:
            if worker and worker.cancelled:
                vs_p.terminate()
                enc_proc.terminate()
                return False
            line = line.strip()
            if line:
                if worker:
                    worker.sig.log.emit(line)
                fm = fps_pat.search(line)
                if fm and worker:
                    worker.sig.prog.emit(-1, f"速度: {fm.group(1)} fps")
                fm2 = frame_pat.search(line)
                if fm2 and total_f > 0 and worker:
                    pct = min(100, int(int(fm2.group(1)) / total_f * 100))
                    worker.sig.prog.emit(pct, line)

        enc_proc.wait()
        vs_p.wait()
        assert vs_p.stderr is not None
        vs_err = vs_p.stderr.read()
        if vs_err.strip() and worker:
            worker.sig.log.emit(f"[vspipe] {vs_err.strip()}")

        ok = enc_proc.returncode == 0
        if worker:
            worker.sig.log.emit(f">>> VapourSynth 压制{'完成' if ok else '失败'} (退出码 {enc_proc.returncode})")
        return ok
    except Exception as e:
        if worker:
            worker.sig.log.emit(f"[错误] VapourSynth 配置异常: {e}")
        return False


def run_vs_ff(
    scr: str,
    out: str,
    enc: str,
    enc_p: dict[str, Any],
    worker: Any = None,
) -> bool:
    """使用 vspipe 管道直连 FFmpeg 编码器

    Args:
        scr: VapourSynth 脚本文件路径
        out: 输出文件路径
        enc: FFmpeg 编码器名（如 "libx264", "libx265"）
        enc_p: 编码参数字典
        worker: Runner 实例

    Returns:
        True 表示编码成功
    """
    ff = find_exe("ffmpeg") or "ffmpeg"
    vs_exe = _find_vs("vspipe")

    if worker:
        worker.sig.log.emit(f"[配置] vspipe → FFmpeg ({enc})")

    c_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    vs_cmd = [vs_exe, "--y4m", str(scr), "-"]
    ff_cmd = [ff, "-i", "pipe:", "-c:v", enc]
    for k in ("crf", "preset", "tune"):
        v = enc_p.get(k)
        if v is not None:
            ff_cmd.extend([f"-{k}", str(v)])
    extra = enc_p.get("extra_args", "")
    if extra:
        ff_cmd.extend(shlex.split(str(extra)))
    ff_cmd.extend(["-pix_fmt", "yuv420p10le", "-y", str(out)])

    if worker:
        full_cmd_str = f"{' '.join(vs_cmd)} | {' '.join(ff_cmd)}"
        worker.sig.log.emit(f"[命令] {full_cmd_str}")

    try:
        vs_p = subprocess.Popen(vs_cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, creationflags=c_flag,
                                text=True, errors="replace")
        ff_p = subprocess.Popen(ff_cmd, stdin=vs_p.stdout,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                creationflags=c_flag, text=True, errors="replace")
        if worker:
            worker.processes = [vs_p, ff_p]
        assert vs_p.stdout is not None
        vs_p.stdout.close()

        assert ff_p.stdout is not None
        for line in ff_p.stdout:
            if worker and worker.cancelled:
                vs_p.terminate()
                ff_p.terminate()
                return False
            if line.strip() and worker:
                worker.sig.log.emit(line.strip())

        ff_p.wait()
        vs_p.wait()
        ok = ff_p.returncode == 0
        if worker:
            worker.sig.log.emit(f">>> VapourSynth+FFmpeg 压制{'完成' if ok else '失败'}")
        return ok
    except Exception as e:
        if worker:
            worker.sig.log.emit(f"[错误] VapourSynth+FFmpeg 异常: {e}")
        return False
