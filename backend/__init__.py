# Virgo Agent backend package
# Add backend dir to sys.path so bare imports (import database, from models import ...)
# work alongside relative imports (from . import database, from .models import ...)
import sys
from pathlib import Path
_backend_dir = str(Path(__file__).parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
