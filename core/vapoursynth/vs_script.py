import ast
import subprocess
import os
import datetime
from pathlib import Path
from uuid import uuid4

from config import ROOT
from utils.ffmpeg import find_exe, load_cfg


def _cfg_dir(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def check_vs(code: str, temp_dir: str | Path | None = None) -> tuple[bool, str, str]:
    """检查 VapourSynth 脚本语法与运行时合法性

    先通过 AST 解析检查语法，再通过 ``vspipe --info`` 运行时验证

    Args:
        code: VapourSynth Python 脚本源代码

    Returns:
        (是否通过, 简短消息, 完整输出/错误详情) 三元组
    """
    try:
        ast.parse(code)
    except SyntaxError as e:
        msg = f"语法错误 (第 {e.lineno} 行): {e.msg}"
        return False, msg, msg

    vspipe = find_exe("vspipe")
    if not vspipe:
        return True, "语法通过（但未找到vspipe）", ""

    tmp_path = None
    try:
        if temp_dir is None:
            temp_dir = load_cfg().get("temp_vpy_dir", ".\\vpy\\temp")
        folder = _cfg_dir(str(temp_dir))
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        tmp_path = folder / f"check_{ts}_{uuid4().hex[:8]}.vpy"
        tmp_path.write_text(code, encoding="utf-8")

        c_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        p = subprocess.run([vspipe, "--info", str(tmp_path), "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                           text=True, creationflags=c_flag, errors="replace")

        if p.returncode != 0:
            full_output = p.stdout.strip()
            lines = [l.strip() for l in full_output.split('\n') if l.strip()]
            if lines:
                err_text = ""
                for l in lines:
                    if l.startswith("AttributeError:") or l.startswith("ModuleNotFoundError:") or "No attribute with the name" in l:
                        err_text = l
                        break
                if not err_text:
                    err_text = lines[-1]
                return False, f"运行检查失败:\n{err_text}", full_output
            return False, "运行检查失败 (vspipe崩溃)", full_output
            
        return True, "语法与运行检查通过！环境正常。", p.stdout.strip()
    except Exception as e:
        msg = f"检查异常: {e}"
        return False, msg, msg
    finally:
        if tmp_path:
            try:
                tmp_path.unlink()
            except Exception:
                pass
