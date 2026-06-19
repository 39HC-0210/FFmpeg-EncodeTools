from utils import read_txt, warn


def read_chap(chap_path: str) -> tuple[list[int], list[str]]:
    """解析 FFmpeg CHAPTER 格式的章节 TXT 文件

    Args:
        chap_path: 章节文件路径

    Returns:
        (时间列表（毫秒）, 名称列表) 的元组
    """
    times: list[int] = []
    names: list[str] = []
    try:
        _, raw = read_txt(chap_path)
        lines = [l.strip() for l in raw if l.strip()]
    except Exception as e:
        warn(f"章节文件读取失败: {chap_path} - {e}")
        return times, names

    i = 0
    # 解析导入的章节文件的每一行
    while i < len(lines):
        line = lines[i]
        if line.startswith('CHAPTER') and '=' in line:
            key, val = line.split('=', 1)
            if key.startswith('CHAPTER') and key[-4:] != 'NAME':
                try:
                    parts = val.replace('.', ':').split(':')
                    if len(parts) < 3:
                        raise ValueError("时间量错误")
                    h, m, s = parts[:3]
                    ms = parts[3] if len(parts) > 3 else '0'
                    times.append(int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms))
                    if i+1 < len(lines) and lines[i+1].startswith('CHAPTER') and 'NAME' in lines[i+1]:
                        names.append(lines[i+1].split('=', 1)[1].strip())
                        i += 2
                    else:
                        names.append('')
                        i += 1
                except Exception as e:
                    warn(f"章节行解析失败：{line} - {e}")
                    i += 1
            else:
                i += 1
        else:
            i += 1
    return times, names


def make_meta(
    times_ms: list[int],
    names: list[str],
    meta_path: str,
    total_ms: int | None = None,
) -> None:
    """生成 FFmpeg FFMETADATA1 格式的章节元数据文件

    Args:
        times_ms: 各章节起始时间（毫秒）
        names: 各章节名称
        meta_path: 输出元数据文件路径
        total_ms: 视频总时长（毫秒），用于最后一章的结束时间
    """
    if total_ms is None:
        total_ms = 999999999
    with open(meta_path, 'w', encoding='utf-8') as f:
        f.write(";FFMETADATA1\n")
        for i, start in enumerate(times_ms):
            f.write("[CHAPTER]\nTIMEBASE=1/1000\n")
            end = times_ms[i+1] if i < len(times_ms)-1 else total_ms
            f.write(f"START={start}\nEND={end}\n")
            f.write(f"title={names[i]}\n")
