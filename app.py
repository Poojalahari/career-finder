"""Compatibility launcher for `python app.py`; the Flask app lives in Backend."""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Backend"))
os.environ.setdefault("FLASK_ENV", "development")

from wsgi import app  # noqa: E402


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=debug)
