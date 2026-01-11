# === Project bootstrap ===
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "../..")))
# add the notebooks/utils directory to the import path
sys.path.append(str(Path(__file__).resolve().parent / "utils"))

from utils.env_setup import setup_src_path

setup_src_path()
# =========================
# =========================
