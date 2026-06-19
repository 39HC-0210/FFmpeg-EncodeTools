from pathlib import Path
from typing import Any

from utils import uniq_out, run_ff, info, find_exe, get_vinfo
from core.tools.encoder import EncBook


def _make_vf(
    scale: str | None = None,
    sub_path: str | None = None,
    font_path: str | None = None,
) -> str | None:
    """构建 FFmpeg -vf 滤镜参数

    Args:
        scale: 缩放参数（如 "-2:1080"）
        sub_path: 字幕文件路径
        font_path: 字体目录路径

    Returns:
        -vf 参数字符串，无滤镜时返回 None
    """
    parts = []
    if scale:
        parts.append(scale)
    if sub_path:
        s = Path(sub_path).resolve().as_posix().replace(':', '\\:')
        sub_str = f"subtitles=filename='{s}'"
        if font_path:
            f_dir = Path(font_path).resolve().as_posix().replace(':', '\\:')
            sub_str += f":fontsdir='{f_dir}'"
        parts.append(sub_str)
    return ','.join(parts) if parts else None

def encode(
    vid_list: list[Path],
    enc_name: str,
    crf: float,
    preset: str,
    scale: str | None = None,
    pix_fmt: str = 'yuv420p10le',
    sub_path: str | None = None,
    font_path: str | None = None,
    aud_cfg: dict[str, Any] | None = None,
    out_dir: str | None = None,
    worker: Any = None,
    ext_params: dict[str, Any] | None = None,
) -> None:
    """对视频文件执行 FFmpeg 编码压制

    Args:
        vid_list: 待编码视频文件路径列表
        enc_name: 编码器内部名（如 "libx264"）
        crf: 恒定质量因子
        preset: 编码速度预设
        scale: 缩放滤镜参数
        pix_fmt: 像素格式
        sub_path: 烧入字幕文件路径
        font_path: 字幕字体目录
        aud_cfg: 音频编码配置字典
        out_dir: 输出目录或文件路径
        worker: Runner 实例，用于进度回调与取消
        ext_params: 高级编码参数字典
    """
    ff = find_exe("ffmpeg") or "ffmpeg"
    total = len(vid_list)

    for idx, vp in enumerate(vid_list):
        # 检查是否存在文件
        
        if worker and worker.is_cancelled:
            break
        if not vp.is_file():
            continue

        if out_dir and len(vid_list) == 1:
            op = Path(out_dir)
            if op.is_dir():
                op = uniq_out(op, vp.stem, ".mp4")
            else:
                if not op.suffix:
                    op = op.with_suffix(".mp4")
                op.parent.mkdir(parents=True, exist_ok=True)
        else:
            d = Path(out_dir) if out_dir and Path(out_dir).is_dir() else vp.parent
            op = uniq_out(d, vp.stem, ".mp4")

        vf = _make_vf(scale, sub_path, font_path)
        vi = get_vinfo(vp)
        dur_ms = vi.get('dur_ms', 0) if vi else 0

        all_p = {"crf": crf, "preset": preset}
        if ext_params:
            all_p.update(ext_params)
        book = EncBook()
        enc_cmd = book.build_cmd(enc_name, all_p)

        cmd = [ff, '-i', str(vp)] + enc_cmd
        if '-pix_fmt' not in cmd:
            cmd += ['-pix_fmt', pix_fmt]

        if vi:
            cs = vi.get('cspace')
            if cs and cs.strip():
                cmd += ['-colorspace', cs, '-color_primaries', cs, '-color_trc', cs]
            cr = vi.get('crange')
            if cr and cr.strip():
                cmd += ['-color_range', cr]

        if vf:
            cmd += ['-vf', vf]
        cmd += ['-map', '0:v:0', '-map', '0:a?']

        if aud_cfg and aud_cfg.get('ok'):
            cmd += ['-c:a', aud_cfg['enc']]
            if aud_cfg.get('bitrate') and aud_cfg.get('bitrate') != "无损" and aud_cfg['enc'] != "flac":
                cmd += ['-b:a', aud_cfg['bitrate']]
            if aud_cfg.get('ar'):
                cmd += ['-ar', aud_cfg['ar']]
        else:
            cmd += ['-c:a', 'copy']
        cmd += ['-y', str(op)]

        log_cb = worker.log if worker else None
        status_prefix = f"正在压制 ({idx+1}/{total}): {vp.name}" if total > 1 else f"正在压制: {vp.name}"
        if run_ff(cmd, f"压制 {vp.name}", dur_ms, worker, log_cb=log_cb, status_prefix=status_prefix):
            info(f"压制完成 -> {op}")
