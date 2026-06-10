from dataclasses import dataclass, field
from typing import Any


@dataclass
class EncParam:
    """单个编码器参数定义"""
    key: str
    label: str
    w_type: str
    default: Any
    rng: list | None = None
    opts: list | None = None
    step: float = 1.0
    tip: str = ""
    ff_flag: str = ""
    x265_key: str | None = None
    nvenc_key: str | None = None
    svtav1_key: str | None = None


@dataclass
class ParamGrp:
    """编码器参数分组"""
    label: str
    params: list


@dataclass
class EncInfo:
    """编码器完整信息：名称、格式、参数分组等"""
    name: str
    show_name: str
    cat: str
    fmts: list = field(default_factory=lambda: [".mp4", ".mkv"])
    pix_fmts: list = field(default_factory=lambda: ["yuv420p", "yuv420p10le"])
    groups: list = field(default_factory=list)
    use_x265: bool = False
    use_nvenc: bool = False
    use_svtav1: bool = False


class EncBook:
    """编码器参数手册（单例）

    预定义了 libx264、libx265、libsvtav1 三种编码器的参数组，
    并通过 :meth:`build_cmd` 将用户参数转换为命令行参数
    """

    _one: "EncBook | None" = None
    _dict: dict[str, "EncInfo"]

    def __new__(cls) -> "EncBook":
        if cls._one is None:
            cls._one = super().__new__(cls)
            cls._one._dict = {}
            cls._one._load()
        return cls._one

    def _load(self) -> None:
        self._load_builtin()

    def _load_builtin(self) -> None:
        """加载内置编码器定义"""
        self._add_libx264()
        self._add_libx265()
        self._add_libsvtav1()

    def _add(self, info: EncInfo) -> None:
        """注册一个编码器信息"""
        self._dict[info.name] = info

# 关于内置编码器参数的加载

    def _add_libx264(self) -> None:
        """注册 libx264 编码器参数定义"""
        self._add(EncInfo(
            name="libx264", show_name="H.264/AVC (libx264)", cat="cpu",
            groups=[
                ParamGrp("码率控制", [
                    EncParam("crf", "CRF", "float_spin", 18.0, [0, 51], step=0.5,
                             ff_flag="-crf", tip="恒定质量因子。推荐 16~22"),
                    EncParam("preset", "Preset", "combo", "medium",
                             opts=["ultrafast","superfast","veryfast","faster","fast",
                                   "medium","slow","slower","veryslow","placebo"],
                             ff_flag="-preset", tip="编码速度预设。推荐 medium 或 slow"),
                    EncParam("tune", "Tune", "combo", "none",
                             opts=["none","film","animation","grain","stillimage",
                                   "psnr","ssim","fastdecode","zerolatency"],
                             ff_flag="-tune", tip="针对特定片源的微调预设。例如：animation 适合动漫"),
                    EncParam("profile", "Profile", "combo", "high",
                             opts=["baseline","main","high","high10","high422","high444"],
                             ff_flag="-profile:v", tip="规范解码器的兼容性与特性支持。默认 high"),
                ]),
                ParamGrp("流媒体/码率限制", [
                    EncParam("minrate", "最小码率", "text", "", ff_flag="-minrate", tip="限制最低码率，留空不限制"),
                    EncParam("maxrate", "最大码率", "text", "", ff_flag="-maxrate", tip="限制峰值码率，留空不限制"),
                    EncParam("bufsize", "缓冲区大小", "text", "", ff_flag="-bufsize", tip="VBV 缓冲区大小，留空不限制"),
                ]),
                ParamGrp("GOP 结构", [
                    EncParam("keyint", "关键帧间隔", "int_spin", 250, [1, 9999], ff_flag="-g", tip="两个关键帧之间的最大距离。推荐设为视频帧率的 10 倍"),
                    EncParam("bframes", "B帧数", "int_spin", 3, [0, 16], ff_flag="-bf", tip="允许的最大连续 B 帧数量，推荐 3~4"),
                    EncParam("refs", "参考帧", "int_spin", 3, [1, 16], ff_flag="-refs", tip="运动估计参考帧数，推荐 3~5"),
                    EncParam("sc_threshold", "场景切换阈值", "int_spin", 40, [0, 100], ff_flag="-sc_threshold", tip="场景剧烈变化插入关键帧的灵敏度，默认 40"),
                ]),
                ParamGrp("运动估计", [
                    EncParam("me_method", "ME算法", "combo", "hex",
                             opts=["dia","hex","umh","esa","tesa"],
                             ff_flag="-me_method", tip="运动估计搜索算法，推荐 hex 或 umh"),
                    EncParam("subq", "子像素ME", "int_spin", 7, [0, 11], ff_flag="-subq",
                             tip="子像素运动估计质量级别，推荐 7"),
                    EncParam("me_range", "搜索范围", "int_spin", 16, [4, 128], ff_flag="-me_range", tip="运动向量搜索半径，默认 16"),
                ]),
                ParamGrp("高级", [
                    EncParam("level", "Level", "combo", "auto",
                             opts=["auto","3.0","3.1","4.0","4.1","4.2","5.0","5.1","5.2","6.0","6.1","6.2"],
                             ff_flag="-level", tip="解码器级别限制，默认 auto"),
                ]),
            ]
        ))

    def _add_libx265(self) -> None:
        """注册 libx265 编码器参数定义"""
        self._add(EncInfo(
            name="libx265", show_name="H.265/HEVC (libx265)", cat="cpu",
            use_x265=True, pix_fmts=["yuv420p", "yuv420p10le", "yuv422p10le", "yuv444p10le"],
            groups=[
                ParamGrp("码率控制", [
                    EncParam("crf", "CRF", "float_spin", 18.0, [0, 51], step=0.5,
                             ff_flag="-crf", tip="恒定质量因子，推荐 18~24"),
                    EncParam("preset", "Preset", "combo", "medium",
                             opts=["ultrafast","superfast","veryfast","faster","fast",
                                   "medium","slow","slower","veryslow","placebo"],
                             ff_flag="-preset", tip="编码速度预设，推荐 medium 或 slow"),
                    EncParam("tune", "Tune", "combo", "none",
                             opts=["none","psnr","ssim","grain","fastdecode","zerolatency"],
                             ff_flag="-tune", tip="针对特定片源的微调预设"),
                    EncParam("qcomp", "量化曲线压缩", "float_spin", 0.6, [0.0, 1.0], step=0.05, x265_key="qcomp", tip="码率分配压缩系数"),
                ]),
                ParamGrp("流媒体/码率限制", [
                    EncParam("vbv_minrate", "最小码率", "int_spin", 0, [0, 999999], x265_key="vbv-minrate", tip="0 表示不限制"),
                    EncParam("vbv_maxrate", "最大码率", "int_spin", 0, [0, 999999], x265_key="vbv-maxrate", tip="0 表示不限制"),
                    EncParam("vbv_bufsize", "缓冲区大小", "int_spin", 0, [0, 999999], x265_key="vbv-bufsize", tip="0 表示不限制"),
                ]),
                ParamGrp("GOP 结构", [
                    EncParam("keyint", "关键帧间隔", "int_spin", 250, [1, 9999], x265_key="keyint", tip="最大关键帧间隔，推荐 250"),
                    EncParam("min_keyint", "最小关键帧", "int_spin", 25, [1, 9999], x265_key="min-keyint", tip="默认 25"),
                    EncParam("bframes", "B帧数", "int_spin", 4, [0, 16], x265_key="bframes", tip="允许的最大连续 B 帧数量，推荐 3~4"),
                    EncParam("ref", "参考帧", "int_spin", 3, [1, 16], x265_key="ref", tip="参考帧数，推荐 3~5"),
                    EncParam("open_gop", "Open GOP", "check", False, x265_key="open-gop", tip="默认关闭"),
                    EncParam("scenecut", "场景检测", "int_spin", 40, [0, 100], x265_key="scenecut", tip="场景切换检测灵敏度，默认 40"),
                ]),
                ParamGrp("运动估计", [
                    EncParam("me", "ME算法", "combo", "hex",
                             opts=["dia","hex","umh","star","sea","full"], x265_key="me", tip="运动估计搜索算法，推荐 hex 或 umh"),
                    EncParam("subme", "子像素ME", "int_spin", 2, [0, 7], x265_key="subme",
                             tip="子像素运动估计质量，推荐 2~3"),
                    EncParam("merange", "搜索范围", "int_spin", 57, [1, 32768], x265_key="merange", tip="运动向量搜索半径，默认 57"),
                    EncParam("limit_refs", "限制参考帧", "int_spin", 3, [0, 3], x265_key="limit-refs", tip="限制非必要参考帧的搜索，推荐 3"),
                    EncParam("rect", "非对称划分 (rect)", "check", False, x265_key="rect", tip="允许非对称的 CU 划分，默认关闭"),
                    EncParam("amp", "不对称运动划分 (amp)", "check", False, x265_key="amp", tip="允许非对称运动划分，默认关闭"),
                ]),
                ParamGrp("色度与心理视觉", [
                    EncParam("aq_mode", "AQ 模式", "combo", "2", opts=["0","1","2","3","4"],
                             x265_key="aq-mode", tip="自适应量化模式。0=关闭 1=普通方差 2=自动方差 3=暗部优化"),
                    EncParam("aq_strength", "AQ 强度", "float_spin", 1.0, [0.0, 3.0],
                             step=0.1, x265_key="aq-strength", tip="默认 1.0"),
                    EncParam("psy_rd", "Psy-RD", "float_spin", 2.0, [0.0, 5.0],
                             step=0.1, x265_key="psy-rd", tip="心理视觉失真优化强度，默认 2.0"),
                    EncParam("psy_rdoq", "Psy-RDOQ", "float_spin", 1.0, [0.0, 50.0],
                             step=0.1, x265_key="psy-rdoq", tip="默认 1.0"),
                    EncParam("cbqpoffs", "Cb 色度偏移", "int_spin", 0, [-12, 12], x265_key="cbqpoffs", tip="默认 0"),
                    EncParam("crqpoffs", "Cr 色度偏移", "int_spin", 0, [-12, 12], x265_key="crqpoffs", tip="默认 0"),
                ]),
                ParamGrp("滤波", [
                    EncParam("sao", "SAO", "check", True, x265_key="sao", tip="样本自适应偏移，默认开启"),
                    EncParam("deblock", "去块滤波", "text", "0:0", x265_key="deblock",
                             tip="去块滤波器参数，格式为 tC_offset:Beta_offset"),
                    EncParam("strong_intra_smoothing", "帧内强平滑", "check", True,
                             x265_key="strong-intra-smoothing", tip="默认开启"),
                ]),
                ParamGrp("高级树划分", [
                    EncParam("ctu", "CTU 大小", "int_spin", 64, [16, 64], x265_key="ctu", tip="最大编码树单元，默认 64"),
                    EncParam("tu_intra_depth", "帧内划分深度", "int_spin", 1, [1, 4], x265_key="tu-intra-depth", tip="默认 1"),
                    EncParam("tu_inter_depth", "帧间划分深度", "int_spin", 1, [1, 4], x265_key="tu-inter-depth", tip="默认 1"),
                    EncParam("rd", "RD 级别", "int_spin", 3, [1, 6], x265_key="rd", tip="率失真决策复杂度，推荐 3~4"),
                    EncParam("rdoq_level", "RDOQ级别", "int_spin", 0, [0, 2], x265_key="rdoq-level", tip="推荐 0 或 1"),
                ]),
            ]
        ))

    def _add_libsvtav1(self) -> None:
        """注册 libsvtav1 编码器参数定义"""
        av1p = ["0","1","2","3","4","5","6","7","8","9","10","11","12","13"]
        self._add(EncInfo(
            name="libsvtav1", show_name="AV1 (libsvtav1)", cat="cpu", use_svtav1=True,
            pix_fmts=["yuv420p", "yuv420p10le"], fmts=[".mp4", ".mkv", ".webm"],
            groups=[
                ParamGrp("码率控制", [
                    EncParam("crf", "CRF", "int_spin", 35, [0, 63], ff_flag="-crf",
                             tip="恒定质量因子，推荐 20~40"),
                    EncParam("preset", "Preset", "combo", "8", opts=av1p, ff_flag="-preset",
                             tip="编码速度预设。0 最慢，13 最快。推荐 8~10"),
                    EncParam("tune", "优化指标", "combo", "0", opts=["0","1","2"], svtav1_key="tune", tip="0=VQ(主观质量，推荐) 1=PSNR 2=SSIM"),
                ]),
                ParamGrp("GOP 结构", [
                    EncParam("keyint", "关键帧间隔", "text", "-1", svtav1_key="keyint", tip="-1 表示自动"),
                    EncParam("lookahead", "RC前瞻帧数", "text", "-1", svtav1_key="lookahead", tip="-1 表示自动"),
                ]),
                ParamGrp("高级", [
                    EncParam("svtav1_film_grain", "Film Grain", "int_spin", 0, [0, 50],
                             svtav1_key="film-grain", tip="模拟胶片颗粒效果，0 表示关闭，推荐 0~10"),
                    EncParam("svtav1_enable_overlays", "Enable Overlays", "check", True,
                             svtav1_key="enable-overlays", tip="默认开启"),
                    EncParam("scm", "屏幕内容优化 (SCM)", "combo", "0", opts=["0","1","2"], svtav1_key="scm", tip="0=关闭 1=开启 2=自动"),
                ]),
            ]
        ))


    def get(self, name: str) -> EncInfo | None:
        """根据编码器名称获取 EncInfo"""
        return self._dict.get(name)

    def build_cmd(self, enc_name: str, params: dict[str, Any]) -> list[str]:
        """根据编码器名称和用户参数动态构建命令行参数列表

        Args:
            enc_name: 编码器内部名（如 "libx264"）
            params: 用户参数字典，键为 EncParam.key

        Returns:
            FFmpeg 编码器相关命令行参数列表
        """
        info = self.get(enc_name)
        if not info:
            return ['-c:v', enc_name]

        cmd = ['-c:v', enc_name]
        x265_opts = {}
        svtav1_opts = {}

        pmap = {}
        for g in info.groups:
            for p in g.params:
                pmap[p.key] = p

        for key, val in params.items():
            if val is None:
                continue
            pd = pmap.get(key)
            if not pd:
                continue
            if val == pd.default:
                continue
            if isinstance(val, bool) and not val:
                continue

            if pd.x265_key and info.use_x265:
                x265_opts[pd.x265_key] = str(val).lower() if isinstance(val, bool) else val
            elif pd.svtav1_key and info.use_svtav1:
                svtav1_opts[pd.svtav1_key] = str(val).lower() if isinstance(val, bool) else val
            elif pd.ff_flag:
                cmd.append(pd.ff_flag)
                if not isinstance(val, bool):
                    cmd.append(str(val))

        if x265_opts:
            s = ":".join(f"{k}={v}" for k, v in x265_opts.items())
            cmd += ["-x265-params", s]
        if svtav1_opts:
            s = ":".join(f"{k}={v}" for k, v in svtav1_opts.items())
            cmd += ["-svtav1-params", s]

        return cmd
