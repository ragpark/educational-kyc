import types
import joblib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_run_etl_handles_no_centres(tmp_path, monkeypatch):
    """run_etl should not fail when there are no centres in the database."""
    import backend.etl as etl

    course = types.SimpleNamespace(
        id=1,
        title="Sample Course",
        delivery_mode="online",
        min_lab_req=[],
        skill_prereqs=[],
        online_content_ok=True,
    )

    class FakeQuery:
        def __init__(self, data):
            self.data = data

        def options(self, *args, **kwargs):
            return self

        def all(self):
            return self.data

    class FakeSession:
        def query(self, model):
            if model is etl.Centre:
                return FakeQuery([])
            if model is etl.Course:
                return FakeQuery([course])
            return FakeQuery([])

        def close(self):
            pass

    monkeypatch.setattr(etl, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(etl, "init_db", lambda: None)

    etl.run_etl(output_dir=str(tmp_path))

    centre_meta = joblib.load(tmp_path / "centre_metadata.pkl")
    assert centre_meta == []
