from db.session import SessionLocal
from db.goals import get_root_goal
from app.tree_printer import print_tree

def run():
    session = SessionLocal()
    try:
        root = get_root_goal(session)
        print_tree(root)
    finally:
        session.close()
