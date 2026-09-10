import sys
from pathlib import Path

# harness/ ไม่ใช่ package เลยต้องเติม path เองก่อน import run
sys.path.insert(0, str(Path(__file__).parent.parent / "harness"))
