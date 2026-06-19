import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    ROOT = Path(sys.executable).parent
    CFG_DIR = ROOT / "config" # 配置文件目录
else:
    ROOT = Path(__file__).parent.parent
    CFG_DIR = Path(__file__).parent

SET_FILE = CFG_DIR / "config.json" # 创建配置文件路径
