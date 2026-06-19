import re, math
from pathlib import Path

from config.subs_rule import wash
from utils import info, read_txt, uniq_out, warn


def _read_ass(path: str) -> list[str]:
    """读取 ASS 字幕文件，提取对话文本并清洗

    Args:
        path: ASS 文件路径

    Returns:
        清洗后的对话文本行列表
    """
    try:
        text, _ = read_txt(path)
    except Exception as e:
        warn(f"读 ASS 失败：{path} - {e}")
        return []
    ok, fields, lines = False, [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('[Events]'):
            ok = True
            continue
        if ok:
            if line.startswith('Format:'):
                fields = [f.strip() for f in line[7:].split(',')]
            elif line.startswith('Dialogue:') and fields:
                parts = line[9:].split(',', len(fields)-1)
                if len(parts) >= len(fields):
                    d = dict(zip(fields, parts))
                    if 'Rubi' not in d.get('Style', ''):
                        if t := d.get('Text', ''):
                            lines.append(t)
    cleaned = [wash(t) for t in lines]
    return [c for c in cleaned if c.strip()]


def _read_srt(path: str) -> list[str]:
    """读取 SRT 字幕文件，提取对话文本并清洗

    Args:
        path: SRT 文件路径

    Returns:
        清洗后的对话文本行列表
    """
    try:
        text, _ = read_txt(path)
    except Exception as e:
        warn(f"读 SRT 失败：{path} - {e}")
        return []
    lines = []
    for block in re.split(r'\n\s*\n', text.strip()):
        parts = block.strip().splitlines()
        if len(parts) >= 3:
            if t := ' '.join(parts[2:]):
                lines.append(t)
    cleaned = [wash(t) for t in lines]
    return [c for c in cleaned if c.strip()]


def _split(lines: list[str], n: int) -> list[list[str]]:
    """将文本行列表尽量均分为 n 份

    Args:
        lines: 文本行列表
        n: 目标份数

    Returns:
        二维列表，每个子列表为一个分片
    """
    total = len(lines)
    base = math.ceil(total / n)
    res = []
    for i in range(n):
        s = i * base
        e = min((i+1) * base, total)
        if s >= total:
            break
        res.append(lines[s:e])
    return res


def clean_subs(
    in_path: Path,
    mode: str,
    split_n: int | None = None,
    out_dir: str | None = None,
    single: bool = True,
) -> bool:
    """清洗字幕文件（ASS/SRT），支持等分导出

    Args:
        in_path: 输入字幕文件路径
        mode: 处理模式，"clean" 仅清洗，"split" 清洗并等分
        split_n: 等分份数（仅 mode="split" 时有效）
        out_dir: 输出目录或文件路径
        single: 是否为单文件模式（影响输出路径策略）
    """
    ext = in_path.suffix.lower()
    if ext == '.ass':
        lines = _read_ass(str(in_path))
    elif ext == '.srt':
        lines = _read_srt(str(in_path))
    else:
        warn(f"不支持的字幕格式：{ext}")
        return False
    if not lines:
        warn("没提取到对白文本")
        return False

    if out_dir and single:
        cp = Path(out_dir)
        if cp.is_dir():
            od, ot = cp, cp / f"{in_path.stem}.txt"
        else:
            od, ot = cp.parent, cp
    else:
        od = Path(out_dir) if out_dir and Path(out_dir).is_dir() else in_path.parent
        ot = od / f"{in_path.stem}.txt"

    od.mkdir(parents=True, exist_ok=True)
    if ot.exists() and not single:
        ot = uniq_out(od, in_path.stem, ".txt")

    with open(ot, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    info(f"清洗完成 -> {ot}")

    if mode == 'split' and split_n:
        parts = _split(lines, split_n)
        for idx, pl in enumerate(parts, 1):
            pp = od / f"{ot.stem}_part{idx}{ot.suffix}"
            with open(pp, 'w', encoding='utf-8') as f:
                f.write('\n'.join(pl))

    return True
