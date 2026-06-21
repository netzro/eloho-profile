from datetime import datetime
from eloho.config import LOG_PATH


def append_log(entry: str):
    """Append a timestamped entry to log.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M WAT")
    with open(LOG_PATH, "a") as f:
        f.write(f"\n## {timestamp}\n{entry}\n")
