from pathlib import Path

def get_checkpointer():
    from langgraph.checkpoint.sqlite import SqliteSaver  # common in recent versions

    db_path = Path("data/checkpoints/langgraph.sqlite")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return SqliteSaver(str(db_path))
