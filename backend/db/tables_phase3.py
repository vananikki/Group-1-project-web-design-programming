
try:
    from db.tables_phase2 import Language
except ModuleNotFoundError:
    from tables_phase2 import Language

__all__ = ["Language"]


