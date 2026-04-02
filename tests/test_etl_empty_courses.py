import types
import joblib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_run_etl_handles_empty_courses(tmp_path, monkeypatch):
    """run_etl should not fail when there are no courses in the database."""
    import backend.etl as etl

    centre = types.SimpleNamespace(
        id=1, name="Test Centre", labs=[], skills=[], online_rating=4.5
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
                return FakeQuery([centre])
            if model is etl.Course:
                return FakeQuery([])
            return FakeQuery([])

        def close(self):
            pass

    monkeypatch.setattr(etl, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(etl, "init_db", lambda: None)

    etl.run_etl(output_dir=str(tmp_path))

    course_meta = joblib.load(tmp_path / "course_metadata.pkl")
    assert course_meta == []
