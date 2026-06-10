import subprocess, shutil, os
from dataclasses import dataclass, field

@dataclass
class EncEntry:
    """编码器条目信息"""
    name: str
    desc: str = ""
    etype: str = "video"


class FFCap:
    """FFmpeg 编码器能力检测器

    通过 ``ffmpeg -encoders`` 扫描可用的视频/音频编码器，并按 GPU 加速类型分类
    """

    def __init__(self, ff_path: str = "ffmpeg"):
        self.ff: str = ff_path
        self.v_encs: dict[str, EncEntry] = {}
        self.a_encs: dict[str, EncEntry] = {}
        self.gpu_encs: dict[str, str] = {}
        self.ok: bool = False

    def scan(self) -> bool:
        """执行编码器扫描，返回 True 表示扫描成功"""
        try:
            self._do_scan()
            self.ok = True
            return True
        except Exception as e:
            print(f"[FFmpeg] 检测失败: {e}")
            return False

    def _do_scan(self) -> None:
        """内部扫描实现，解析 ffmpeg -encoders 输出"""
        c_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run([self.ff, "-encoders"], capture_output=True,
                           text=True, creationflags=c_flag)
        for line in r.stdout.split("\n"):
            line = line.strip()
            if line.startswith(" V"):
                parts = line[7:].strip().split(None, 1)
                if parts:
                    self.v_encs[parts[0]] = EncEntry(parts[0], parts[1] if len(parts) > 1 else parts[0], "video")
            elif line.startswith(" A"):
                parts = line[7:].strip().split(None, 1)
                if parts:
                    self.a_encs[parts[0]] = EncEntry(parts[0], parts[1] if len(parts) > 1 else parts[0], "audio")

        gpu_map = {"nvenc": "nvidia", "amf": "amd", "qsv": "intel",
                   "videotoolbox": "apple", "vaapi": "linux"}
        for name in self.v_encs:
            for suf, gtype in gpu_map.items():
                if name.endswith("_" + suf):
                    self.gpu_encs[name] = gtype
                    break

    def has(self, name: str) -> bool:
        """检查指定编码器名称是否可用"""
        if not self.ok:
            self.scan()
        return name in self.v_encs or name in self.a_encs

    def list_v(self, names: list[str]) -> list[str]:
        """从候选列表中筛选出本机可用的视频编码器名称"""
        if not self.ok:
            self.scan()
        return [n for n in names if n in self.v_encs]

    def v_by_cat(self) -> dict[str, list[str]]:
        """按类别分组返回可用的视频编码器

        Returns:
            字典，键为类别名（如 "CPU 软件编码"、"NVIDIA GPU"），值为编码器名称列表
        """
        if not self.ok:
            self.scan()
        cats = {
            "CPU 软件编码": ["libx264", "libx265", "libsvtav1"],
            "NVIDIA GPU": ["h264_nvenc", "hevc_nvenc", "av1_nvenc"],
            "AMD GPU": ["h264_amf", "hevc_amf"],
            "Intel GPU": ["h264_qsv", "hevc_qsv", "av1_qsv"],
        }
        res = {}
        for cat, names in cats.items():
            avail = self.list_v(names)
            if avail:
                res[cat] = avail
        return res




_ff_cap: FFCap | None = None


def get_ffcap(ff_path: str = "ffmpeg") -> FFCap:
    """获取 FFCap 单例，首次调用或路径变化时重新扫描

    Args:
        ff_path: ffmpeg 可执行文件路径

    Returns:
        FFCap 实例
    """
    global _ff_cap
    if _ff_cap is None:
        _ff_cap = FFCap(ff_path)
        _ff_cap.scan()
    elif _ff_cap.ff != ff_path:
        _ff_cap.ff = ff_path
        _ff_cap.scan()
    return _ff_cap



