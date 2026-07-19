"""Compatibility launcher for `python app.py`; the Flask app lives in Backend."""

import os
import subprocess
import sys


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "flask",
        "--app",
        "Backend/wsgi.py",
        "run",
        "--host=127.0.0.1",
        f"--port={os.getenv('PORT', '5000')}",
    ]
    if os.getenv("FLASK_DEBUG", "false").lower() == "true":
        command.append("--debug")
    env = {**os.environ, "FLASK_ENV": os.getenv("FLASK_ENV", "development")}
    return subprocess.call(command, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
