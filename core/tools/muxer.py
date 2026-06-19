from pathlib import Path
from typing import Any

from utils import find_exe, run_ff, info, warn, get_vdur, uniq_out
from core.tools.chapters import make_meta, read_chap


def mux(
    v_path: str,
    a_path: str | None,
    out_path: str | None,
    mode: str,
    times_ms: list[int] | None = None,
    names: list[str] | None = None,
    worker: Any = None,
) -> bool:
    """简易混流封装（MP4Box 或 FFmpeg 模式）

    Args:
        v_path: 视频文件路径
        a_path: 音频文件路径（可选）
        out_path: 输出路径，留空自动生成
        mode: 混流引擎，"mp4box" 或 "ffmpeg"
        times_ms: 章节时间列表（毫秒）
        names: 章节名称列表
        worker: Runner 实例

    Returns:
        True 表示混流成功
    """
    vp = Path(v_path)
    if not out_path:
        out_path = str(vp.with_suffix(".mp4"))
    meta_f = None
    if times_ms and names:
        dur = get_vdur(vp) or 999999999
        meta_f = vp.parent / f"{vp.stem}_meta.txt"
        make_meta(times_ms, names, str(meta_f), total_ms=dur)

    if mode == "mp4box":
        mp4 = find_exe("mp4box") or "mp4box"
        cmd = [mp4, '-add', f'{vp}#video']
        if a_path:
            cmd.extend(['-add', f'{a_path}#audio'])
        if meta_f:
            cmd.extend(['-chap', str(meta_f)])
        cmd.extend(['-new', out_path])
    else:
        ff = find_exe("ffmpeg") or "ffmpeg"
        cmd = [ff, '-i', v_path]
        if a_path:
            cmd.extend(['-i', a_path])
        if meta_f:
            cmd.extend(['-i', str(meta_f)])
            mi = '2' if a_path else '1'
            cmd.extend(['-map_metadata', mi, '-map_chapters', mi])
        cmd.extend(['-map', '0:v:0', '-map', '0:a?'])
        if a_path:
            cmd.extend(['-map', '1:a?'])
        cmd.extend(['-c', 'copy', '-y', out_path])

    log_cb = worker.log if worker else None
    ok = run_ff(cmd, "混流封装", 0, worker, log_cb=log_cb)
    if meta_f and meta_f.exists():
        try:
            meta_f.unlink()
        except Exception:
            pass
    return ok


def mux_ff(
    sources: list[str],
    tracks: list[dict[str, Any]],
    attachments: list[str] | None = None,
    chap_path: str | None = None,
    out_path: str | None = None,
    fmt: str = "mkv",
    worker: Any = None,
) -> bool:
    """高级多轨道混流封装（FFmpeg）

    支持多源文件、多轨道、语言/标题元数据、MKV 字体附件

    Args:
        sources: 源文件路径列表
        tracks: 轨道信息列表，每项含 src_idx, st_idx, type, name, lang
        attachments: 字体附件文件路径列表（仅 MKV）
        chap_path: 章节 TXT 文件路径
        out_path: 输出路径
        fmt: 输出容器格式，"mkv" 或 "mp4"
        worker: Runner 实例

    Returns:
        True 表示混流成功
    """
    ff = find_exe("ffmpeg") or "ffmpeg"
    meta_f = None

    if chap_path and Path(chap_path).exists() and sources:
        times_ms, names = read_chap(chap_path)
        if times_ms and names:
            first_path = Path(sources[0])
            meta_f = first_path.parent / f"{first_path.stem}_ffmeta.txt"
            dur = get_vdur(first_path) or 999999999
            make_meta(times_ms, names, str(meta_f), total_ms=dur)

    cmd = [ff]

    for src in sources:
        cmd.extend(["-i", src])

    meta_idx = None
    if meta_f:
        meta_idx = len(sources)
        cmd.extend(["-i", str(meta_f)])

    for tk in tracks:
        cmd.extend(["-map", f"{tk['src_idx']}:{tk['st_idx']}"])

    if meta_idx is not None:
        cmd.extend(["-map_metadata", str(meta_idx)])
        cmd.extend(["-map_chapters", str(meta_idx)])

    for out_idx, tk in enumerate(tracks):
        lang = tk.get("lang", "")
        name = tk.get("name", "")
        if lang:
            cmd.extend([f"-metadata:s:{out_idx}", f"language={lang}"])
        if name:
            cmd.extend([f"-metadata:s:{out_idx}", f"title={name}"])

    if fmt == "mkv" and attachments:
        attach_idx = 0
        for att in attachments:
            att_lower = att.lower()
            if att_lower.endswith(".otf"):
                mime = "application/vnd.ms-opentype"
            else:
                mime = "application/x-truetype-font"
            cmd.extend(["-attach", att,
                        f"-metadata:s:t:{attach_idx}", f"mimetype={mime}"])
            attach_idx += 1

    if not out_path and sources:
        vp = Path(sources[0])
        out_path = str(vp.with_suffix(f".muxed.{fmt}"))

    cmd.extend(["-c", "copy", "-y", out_path or ""])

    log_cb = worker.log if worker else None
    ok = run_ff(cmd, "高级混流", 0, worker, log_cb=log_cb)

    if meta_f and meta_f.exists():
        try:
            meta_f.unlink()
        except Exception:
            pass

    return ok
