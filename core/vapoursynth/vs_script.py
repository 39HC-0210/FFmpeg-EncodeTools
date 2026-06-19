import ast
import subprocess
import tempfile
import os
from pathlib import Path
from utils.ffmpeg import find_exe


def check_vs(code: str) -> tuple[bool, str, str]:
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

    try:
        with tempfile.NamedTemporaryFile("w", suffix=".vpy", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        
        c_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        p = subprocess.run([vspipe, "--info", tmp_path, "-"], 
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                           text=True, creationflags=c_flag, errors="replace")
        
        try:
            os.remove(tmp_path)
        except:
            pass
            
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
