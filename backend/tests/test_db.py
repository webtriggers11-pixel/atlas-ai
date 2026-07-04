"""
Phase 1 verification script — run directly to confirm all 4 tables work.

Usage (from backend/ with venv active):
    python tests/test_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal
from app.models import Map, Node, NodeExplanation, Edge  # noqa: F401 — registers tables in Base.metadata
from migrations.migration_manager import MigrationManager


def run():
    # Run migrations first so tables exist before we touch them
    manager = MigrationManager(settings.DATABASE_URL, Base.metadata)
    manager.generate_migration()
    manager.apply_migrations()

    db = SessionLocal()
    try:
        # --- CREATE ---
        map_row = Map(topic="transformers in AI", title="Transformers in AI")
        db.add(map_row)
        db.flush()  # get the UUID without committing

        root = Node(map_id=map_row.id, label="Transformers in AI", is_root=True)
        db.add(root)
        db.flush()

        child = Node(map_id=map_row.id, parent_id=root.id, label="Attention mechanism")
        db.add(child)
        db.flush()

        explanation = NodeExplanation(
            node_id=root.id,
            depth="standard",
            content="Transformers are a neural network architecture based on self-attention.",
        )
        db.add(explanation)

        edge = Edge(map_id=map_row.id, source_node_id=root.id, target_node_id=child.id)
        db.add(edge)

        db.commit()

        # --- READ BACK ---
        saved_map = db.query(Map).filter_by(id=map_row.id).first()
        nodes = db.query(Node).filter_by(map_id=map_row.id).all()
        exp = db.query(NodeExplanation).filter_by(node_id=root.id, depth="standard").first()
        edges = db.query(Edge).filter_by(map_id=map_row.id).all()

        print(f"\n[OK] Map:         {saved_map.title}")
        print(f"[OK] Nodes:       {[n.label for n in nodes]}")
        print(f"[OK] Explanation: {exp.content[:60]}...")
        print(f"[OK] Edges:       {len(edges)} edge(s)")

        # --- CLEANUP ---
        db.delete(saved_map)
        db.commit()
        print("\n[OK] Cleanup done — all 4 tables verified.\n")

    except Exception as e:
        db.rollback()
        print(f"\n[FAIL] {e}\n")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
