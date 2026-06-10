from pathlib import Path
from typing import Any

from utils import find_exe, run_ff, info, warn, get_vdur, uniq_out
from core.tools.chapters import make_meta


def inject_chap(
    v_path: str,
    times_ms: list[int],
    names: list[str],
    out_path: str | None = None,
    worker: Any = None,
) -> bool:
    """将章节元数据注入视频文件

    Args:
        v_path: 视频文件路径
        times_ms: 各章节起始时间列表（毫秒）
        names: 各章节名称列表
        out_path: 输出文件路径，留空自动生成
        worker: Runner 实例，用于进度回调

    Returns:
        True 表示注入成功
    """
    vp = Path(v_path)
    if not out_path:
        out_p = uniq_out(vp.parent, vp.stem, "_chapter.mp4")
    else:
        out_p = Path(out_path)
        if not out_p.suffix:
            out_p = out_p.with_suffix(".mp4")
        out_p.parent.mkdir(parents=True, exist_ok=True)
    out_path = str(out_p)

    if not times_ms or not names:
        warn("章节数据为空，取消任务")
        return False

    dur = get_vdur(vp) or 999999999
    meta_f = vp.parent / f"{vp.stem}_metadata.txt"
    make_meta(times_ms, names, str(meta_f), total_ms=dur)

    ff = find_exe("ffmpeg") or "ffmpeg"
    cmd = [ff, '-i', str(vp), '-i', str(meta_f),
           '-map_metadata', '1', '-map_chapters', '1',
           '-map', '0', '-c', 'copy', '-y', str(out_path)]

    log_cb = worker.log if worker else None
    ok = run_ff(cmd, "章节注入", 0, worker, log_cb=log_cb)
    if meta_f.exists():
        try:
            meta_f.unlink()
        except Exception:
            pass
    if ok:
        info(f"章节封装完成 -> {out_path}")
    return ok
