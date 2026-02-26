#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FFmpeg EncodeTools (Python 版)
功能：视频压制（内嵌字幕可选）、添加章节
支持拖拽多个文件（路径含空格时需加引号，拖拽自动添加）
"""

import os
import sys
import subprocess
from pathlib import Path

# 获取正确的脚本/可执行文件所在目录
if getattr(sys, 'frozen', False):
    # 打包成 exe 后的情况
    SCRIPT_DIR = Path(sys.executable).parent
else:
    # 直接运行 .py 脚本的情况
    SCRIPT_DIR = Path(__file__).parent

OUTPUT_DIR = SCRIPT_DIR / "Output"
SUBTITLE_DIR = SCRIPT_DIR / "Subtitles"
FONT_DIR = SCRIPT_DIR / "Fonts"

# 确保目录存在
for d in [OUTPUT_DIR, SUBTITLE_DIR, FONT_DIR]:
    d.mkdir(exist_ok=True)

# 预设映射（数字 -> 预设名）
PRESET_MAP = {
    '1': 'veryslow',
    '2': 'slower',
    '3': 'slow',
    '4': 'medium',
    '5': 'fast',
    '6': 'faster',
    '7': 'veryfast',
    '8': 'superfast',
    '9': 'ultrafast'
}
VALID_PRESETS = set(PRESET_MAP.values())

def clear_screen():
    """清屏（跨平台）"""
    os.system('cls' if os.name == 'nt' else 'clear')

def split_file_paths(input_str):
    """
    将用户输入的多个文件路径（可能含引号）分割成列表
    处理 Windows 拖拽时自动添加的引号
    """
    files = []
    current = []
    in_quote = False
    for ch in input_str:
        if ch == '"' and not in_quote:
            in_quote = True
        elif ch == '"' and in_quote:
            in_quote = False
        elif ch.isspace() and not in_quote:
            if current:
                files.append(''.join(current))
                current = []
        else:
            current.append(ch)
    if current:
        files.append(''.join(current))
    # 去除每个路径两端的引号（如果还存在）
    return [f.strip('"') for f in files if f.strip()]

def get_unique_output_path(output_dir, base_name, ext):
    """
    生成不重复的输出文件路径
    规则：若文件已存在，则在文件名后添加 ~1, ~2, ...
    """
    counter = 0
    while True:
        if counter == 0:
            name = f"{base_name}{ext}"
        else:
            name = f"{base_name}~{counter}{ext}"
        out_path = output_dir / name
        if not out_path.exists():
            return out_path
        counter += 1

def validate_crf(value):
    """验证 CRF 是否为 0-51 的整数"""
    try:
        crf = int(value)
        if 0 <= crf <= 51:
            return crf
    except ValueError:
        pass
    return None

def validate_preset(value):
    """验证预设名或数字快捷输入，返回标准预设名"""
    v = value.strip().lower()
    if v in PRESET_MAP:
        return PRESET_MAP[v]
    if v in VALID_PRESETS:
        return v
    return None

def get_user_input(prompt, validator=None, retry_message=None):
    """
    通用输入函数，循环直到输入合法
    validator：接收输入字符串，返回合法值或 None
    """
    while True:
        user_input = input(prompt).strip()
        if validator:
            result = validator(user_input)
            if result is not None:
                return result
            if retry_message:
                print(retry_message)
            else:
                print("输入无效，请重新输入。")
        else:
            return user_input

def select_mode():
    """选择主模式"""
    clear_screen()
    print("===================== 视频处理模式选择 =====================")
    print("1. 普通压制视频（无内嵌字幕）")
    print("2. 压制内嵌字幕的视频")
    print("3. 为视频添加章节（无损混流）")
    print("============================================================")
    mode = get_user_input("请输入模式编号（1/2/3）：",
                          validator=lambda x: x if x in ('1','2','3') else None,
                          retry_message="错误：请输入有效的模式编号（1、2 或 3）！")
    return mode

def select_subtitle():
    """选择字幕文件（模式2使用）"""
    clear_screen()
    print("===================== 内嵌字幕配置 =====================")
    print("字幕文件需放在脚本目录下的 Subtitles 文件夹中")
    print("请输入ASS字幕文件名（例如：JPTC.ass）")
    print("============================================================")
    print("当前Subtitles文件夹中的ASS文件：")
    ass_files = list(SUBTITLE_DIR.glob("*.ass"))
    if ass_files:
        for f in ass_files:
            print(f.name)
    else:
        print("未找到ASS文件！")
    print()
    while True:
        sub_file = input("请输入ASS文件名：").strip()
        full_path = SUBTITLE_DIR / sub_file
        if full_path.is_file():
            return full_path
        print(f"错误：未在Subtitles文件夹中找到文件「{sub_file}」！")

def select_encoder():
    """选择编码器"""
    clear_screen()
    print("===================== 视频编码器选择 =====================")
    print("可选值：")
    print("- libx264 / 264")
    print("- libx265 / 265")
    print("============================================================")
    encoder = get_user_input("请输入编码器（支持264/265快捷输入）：",
                             validator=lambda x: ('libx264' if x in ('264','libx264') else
                                                  'libx265' if x in ('265','libx265') else None),
                             retry_message="错误：请输入有效的编码器（libx264/libx265 或 264/265）！")
    return encoder

def select_crf():
    """选择CRF值"""
    clear_screen()
    print("===================== CRF值选择 =====================")
    print("CRF范围：0~51（值越小画质越高，文件越大）")
    print("============================================================")
    crf = get_user_input("请输入CRF值（0-51）：",
                         validator=validate_crf,
                         retry_message="错误：CRF值必须是0~51之间的数字！")
    return crf

def select_preset():
    """选择Preset"""
    clear_screen()
    print("===================== Preset选择 =====================")
    print("数字快捷输入（1=最慢，9=最快）：")
    print("1=veryslow  2=slower  3=slow  4=medium  5=fast")
    print("6=faster    7=veryfast 8=superfast 9=ultrafast")
    print("也可直接输入预设名（如：medium）")
    print("============================================================")
    preset = get_user_input("请输入Preset（数字1-9或预设名）：",
                            validator=validate_preset,
                            retry_message="错误：Preset输入无效！")
    return preset

def select_resolution():
    """选择分辨率缩放"""
    clear_screen()
    print("===================== 分辨率选择 =====================")
    print("可选值：")
    print("- 720 / 0     --缩放到720P")
    print("- 1080 / 1    --保持原分辨率，不缩放")
    print("============================================================")
    res = get_user_input("请输入分辨率选项：",
                         validator=lambda x: x if x in ('720','0','1080','1') else None,
                         retry_message="错误：请输入有效的分辨率选项（720/1080 或 0/1）！")
    # 转换为 scale 参数
    if res in ('720', '0'):
        return "scale=-1:720"
    else:
        return None

def select_input_files(prompt="请输入/拖拽视频文件："):
    """获取用户输入的文件路径列表（支持拖拽多个）"""
    clear_screen()
    print("===================== 选择视频文件 =====================")
    print("请将需要处理的视频文件拖拽到本窗口，然后按回车")
    print("（多个文件请连续拖拽，自动以空格分隔）")
    print("============================================================")
    line = input(prompt).strip()
    if not line:
        print("错误：未选择任何视频文件！")
        input("按回车键继续...")
        return select_input_files(prompt)
    paths = split_file_paths(line)
    # 过滤空字符串并转换为 Path 对象
    valid_paths = [Path(p) for p in paths if p]
    if not valid_paths:
        print("错误：未识别到有效文件路径！")
        input("按回车键继续...")
        return select_input_files(prompt)
    return valid_paths

def build_vf_filter(scale_param, subtitle_path=None):
    """构建 -vf 滤镜字符串，使用简化的路径格式"""
    filters = []
    if scale_param:
        filters.append(scale_param)
    if subtitle_path:
        # 获取相对路径（相对于当前目录）
        try:
            # 尝试获取相对路径
            sub_rel = os.path.relpath(subtitle_path, SCRIPT_DIR)
            font_rel = os.path.relpath(FONT_DIR, SCRIPT_DIR)
            
            # 将反斜杠转为正斜杠
            sub_rel = sub_rel.replace('\\', '/')
            font_rel = font_rel.replace('\\', '/')
            
            # 使用相对路径
            filters.append(f"subtitles={sub_rel}:fontsdir={font_rel}")
        except:
            # 如果相对路径失败，使用绝对路径但转义冒号和反斜杠
            sub_abs = str(subtitle_path.resolve()).replace('\\', '/')
            font_abs = str(FONT_DIR.resolve()).replace('\\', '/')
            
            # 将盘符后的冒号替换为特殊标记
            if ':' in sub_abs:
                drive, path = sub_abs.split(':', 1)
                sub_abs = drive + '\\:' + path
            if ':' in font_abs:
                drive, path = font_abs.split(':', 1)
                font_abs = drive + '\\:' + path
            
            filters.append(f"subtitles={sub_abs}:fontsdir={font_abs}")
    
    return ','.join(filters) if filters else None

def show_encode_info(subtitle_flag, encoder, crf, preset, scale_param):
    """显示压制前的确认信息（模拟原批处理的环境显示）"""
    clear_screen()
    print("===================== 开始压制 =====================")
    if subtitle_flag:
        print("压制模式：内嵌字幕压制")
    else:
        print("压制模式：普通压制视频")
    print(f"编码器：{encoder}")
    print(f"CRF值：{crf}")
    print(f"Preset：{preset}")
    if scale_param:
        print("分辨率：720P")
    else:
        print("分辨率：原分辨率")
    print(f"输出目录：{OUTPUT_DIR}")
    print("============================================================")
    print("按任意键继续...")
    input()

def run_ffmpeg(cmd_list, description):
    """执行 FFmpeg 命令"""
    print(f"\n正在{description}：")
    print("执行命令：", ' '.join(str(x) for x in cmd_list))
    try:
        subprocess.run(cmd_list, check=True)
        print("完成。")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 执行失败，错误码：{e.returncode}")
        input("按回车键继续...")
        return False
    except FileNotFoundError:
        print("错误：未找到 ffmpeg，请确保 ffmpeg 已安装并加入 PATH。")
        input("按回车键继续...")
        return False
    return True

def encode_videos(input_paths, encoder, crf, preset, scale_param, subtitle_path=None):
    """执行压制任务（可带字幕）"""
    # 显示确认信息
    show_encode_info(subtitle_path is not None, encoder, crf, preset, scale_param)
    
    for inp in input_paths:
        if not inp.is_file():
            print(f"跳过：文件不存在 {inp}")
            continue
        # 生成输出文件名
        stem = inp.stem
        ext = ".mp4"  # 固定输出为 mp4
        out_path = get_unique_output_path(OUTPUT_DIR, stem, ext)

        # 构建滤镜
        vf_filter = build_vf_filter(scale_param, subtitle_path)

        # 构建命令
        cmd = [
            'ffmpeg', '-i', str(inp),
            '-c:v', encoder,
            '-crf', str(crf),
            '-preset', preset,
            '-pix_fmt', 'yuv420p10le'
        ]
        if vf_filter:
            cmd += ['-vf', vf_filter]
        cmd += [
            '-map', '0:v:0',
            '-map', '0:a:0',
            '-c:a', 'copy',
            '-y', str(out_path)
        ]

        if not run_ffmpeg(cmd, f"压制 {inp.name}"):
            continue
        print(f"输出文件：{out_path}")
        print("=" * 60)

def parse_chapter_file(chap_path):
    """
    解析章节文件（格式如 CHAPTER01=00:00:00.000 和 CHAPTER01NAME=Avant）
    返回 (times_ms, names) 两个列表，times_ms 为毫秒时间戳列表，names 为标题列表
    """
    times = []
    names = []
    with open(chap_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    # 按顺序读取，每两行一个章节（时间+名称）
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('CHAPTER') and '=' in line:
            key, val = line.split('=', 1)
            if key.startswith('CHAPTER') and key[-4:] != 'NAME':  # 时间行
                time_str = val
                # 解析时间 00:00:00.000
                parts = time_str.replace('.', ':').split(':')
                if len(parts) == 4:
                    h, m, s, ms = parts
                else:
                    # 尝试其他格式，简单处理
                    h, m, s = parts[:3]
                    ms = parts[3] if len(parts) > 3 else '0'
                h, m, s, ms = int(h), int(m), int(s), int(ms)
                total_ms = h * 3600000 + m * 60000 + s * 1000 + ms
                times.append(total_ms)
                # 下一行应为名称
                if i+1 < len(lines) and lines[i+1].startswith('CHAPTER') and 'NAME' in lines[i+1]:
                    name_line = lines[i+1]
                    _, name_val = name_line.split('=', 1)
                    names.append(name_val.strip())
                    i += 2
                else:
                    names.append('')  # 无名称
                    i += 1
            else:
                i += 1
        else:
            i += 1
    return times, names

def manual_input_chapters():
    """手动输入章节，返回 (times_ms, names)"""
    times = []
    names = []
    print("===================== 手动输入章节 =====================")
    print("请输入章节时间，推荐格式：00:00:00.000")
    print("(提示：在时间输入栏输入 over 即可结束录入)")
    print("============================================================")
    while True:
        time_str = input("请输入章节时间：").strip()
        if time_str.lower() == 'over':
            if not times:
                print("未录入任何章节，返回主菜单...")
                input("按回车键继续...")
                return None, None
            break
        name_str = input("请输入章节名称：").strip()
        # 解析时间
        try:
            parts = time_str.replace('.', ':').split(':')
            if len(parts) == 4:
                h, m, s, ms = parts
            elif len(parts) == 3:
                h, m, s = parts
                ms = '0'
            else:
                raise ValueError
            h, m, s, ms = int(h), int(m), int(s), int(ms)
            total_ms = h * 3600000 + m * 60000 + s * 1000 + ms
            times.append(total_ms)
            names.append(name_str)
        except ValueError:
            print("时间格式错误，请使用 00:00:00.000 格式。")
            continue
    return times, names

def create_metadata_file(times_ms, names, meta_path):
    """生成 FFMETADATA 文件"""
    with open(meta_path, 'w', encoding='utf-8') as f:
        f.write(";FFMETADATA1\n")
        for i, start in enumerate(times_ms):
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={start}\n")
            if i < len(times_ms) - 1:
                end = times_ms[i+1]
            else:
                end = 999999999  # 最后一章结束时间设为大值
            f.write(f"END={end}\n")
            f.write(f"title={names[i]}\n")

def add_chapters(input_paths, times_ms, names):
    """为视频添加章节（混流）"""
    # 生成临时元数据文件
    meta_file = OUTPUT_DIR / "ffmetadata.txt"
    create_metadata_file(times_ms, names, meta_file)
    print(f"临时元数据文件已生成：{meta_file}")

    for inp in input_paths:
        if not inp.is_file():
            print(f"跳过：文件不存在 {inp}")
            continue
        stem = inp.stem + "_chapter"
        ext = inp.suffix  # 保持原扩展名
        out_path = get_unique_output_path(OUTPUT_DIR, stem, ext)

        cmd = [
            'ffmpeg',
            '-i', str(inp),
            '-i', str(meta_file),
            '-map_metadata', '1',
            '-map_chapters', '1',
            '-map', '0',
            '-c', 'copy',
            '-y', str(out_path)
        ]
        if not run_ffmpeg(cmd, f"添加章节到 {inp.name}"):
            continue
        print(f"输出文件：{out_path}")
        print("=" * 60)

    print(f"临时元数据文件保留在：{meta_file}")

def main():
    while True:
        mode = select_mode()
        if mode == '1':      # 普通压制
            encoder = select_encoder()
            crf = select_crf()
            preset = select_preset()
            scale_param = select_resolution()
            input_files = select_input_files()
            encode_videos(input_files, encoder, crf, preset, scale_param, subtitle_path=None)
            print("所有文件压制完成！")
            input("按回车键返回主菜单...")

        elif mode == '2':    # 内嵌字幕压制
            subtitle_path = select_subtitle()
            encoder = select_encoder()
            crf = select_crf()
            preset = select_preset()
            scale_param = select_resolution()
            input_files = select_input_files()
            encode_videos(input_files, encoder, crf, preset, scale_param, subtitle_path)
            print("所有文件压制完成！")
            input("按回车键返回主菜单...")

        elif mode == '3':    # 添加章节
            clear_screen()
            print("===================== 为视频添加章节 =====================")
            print("1. 添加已有章节文件（自动解析并转换为FFMETADATA）")
            print("2. 手动输入章节")
            print("============================================================")
            chap_mode = get_user_input("请输入模式编号（1/2）：",
                                       validator=lambda x: x if x in ('1','2') else None,
                                       retry_message="错误：请输入1或2！")
            if chap_mode == '1':
                # 从文件导入
                chap_file = get_user_input("请拖入章节TXT文件，然后按回车：")
                # 处理可能的多余引号
                chap_path = Path(chap_file.strip('"'))
                if not chap_path.is_file():
                    print("错误：找不到文件，请重新操作！")
                    input("按回车键继续...")
                    continue
                times, names = parse_chapter_file(chap_path)
                if not times:
                    print("错误：未能解析到任何章节信息，请检查文件格式。")
                    input("按回车键继续...")
                    continue
                print(f"解析到 {len(times)} 个章节。")
                # 显示解析结果
                for i, (t, n) in enumerate(zip(times, names), 1):
                    # 将毫秒转回显示格式
                    h = t // 3600000
                    m = (t % 3600000) // 60000
                    s = (t % 60000) // 1000
                    ms = t % 1000
                    time_str = f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
                    print(f"[{i}] 时间: {time_str}  名称: {n}")
            else:  # chap_mode == '2'
                times, names = manual_input_chapters()
                if times is None:
                    continue  # 返回主菜单

            # 选择视频文件
            input_files = select_input_files("请输入/拖拽需要添加章节的视频文件：")
            # 执行添加章节
            add_chapters(input_files, times, names)
            print("所有视频章节添加完成！")
            input("按回车键返回主菜单...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断，退出。")
        sys.exit(0)