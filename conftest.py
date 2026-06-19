import sys
import pathlib

# 让 pytest 能 import registry（未安装为 pip 包，需手动加 path）
sys.path.insert(0, str(pathlib.Path(__file__).parent))
