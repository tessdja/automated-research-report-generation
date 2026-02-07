import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

# Keep a module-level connection so it doesn't get garbage-collected
_CONN = None
_SAVER = None

def get_checkpointer():
    global _CONN, _SAVER
    if _SAVER is not None:
        return _SAVER

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    db_path = os.path.join(project_root, "checkpoints.sqlite")

    # Create a real sqlite connection
    _CONN = sqlite3.connect(db_path, check_same_thread=False)

    # Create a real saver instance (NOT a context manager)
    _SAVER = SqliteSaver(_CONN)
    return _SAVER


