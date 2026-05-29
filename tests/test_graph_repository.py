from dataclasses import dataclass

import pytest

from novel_assistant.graph_repository import GraphRepository
from novel_assistant.models import ChapterPlan
from novel_assistant.writing_pipeline import DeterministicWritingPipeline


class FakeSession:
    def __init__(self, rows=None):
        self.queries = []
        self.rows = rows or []

    def run(self, query, **params):
        self.queries.append((query, params))
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeDriver:
    def __init__(self, rows=None):
        self.session_obj = FakeSession(rows=rows)
        self.closed = False

    def session(self):
        return self.session_obj

    def close(self):
        self.closed = True


@dataclass
class Blueprint:
    title: str = "Falling Star River"
    genre: str = "fantasy"
    premise: str = "A runaway searches for a family secret."
    main_conflict: str = "The hero opposes a hidden sect."
    worldview: str = "Star fragments carry different laws."
    protagonist_arc: str = "From isolated survivor to responsible leader."
    ending_direction: str = "The truth is revealed and order is restored."


@dataclass
class Character:
    id: str = "char-1"
    name: str = "Lu Chen"
    role: str = "protagonist"
    identity: str = "runaway youth"
    goal: str = "discover the family truth"
    motivation: str = "honor his mother's wish"
    weakness: str = "acts alone"
    growth_arc: str = "learns to trust allies"
    current_state: str = "entering the sect"

    def model_dump(self):
        return self.__dict__.copy()


class Delta:
    project_id = "novel-1"
    source_chapter_number = 1
    node_upserts = []
    relationship_upserts = []


def test_repository_creates_unique_constraints_for_core_labels():
    driver = FakeDriver()
    repo = GraphRepository(driver=driver)

    repo.ensure_constraints()

    queries = [query for query, _ in driver.session_obj.queries]
    for label in ["Novel", "Character", "Chapter", "Event", "Hook"]:
        assert any(f"FOR (n:{label})" in query for query in queries)
        assert any("REQUIRE n.id IS UNIQUE" in query for query in queries)


def test_repository_upserts_blueprint_and_characters_with_relationship():
    driver = FakeDriver()
    repo = GraphRepository(driver=driver)

    repo.upsert_initial_graph("novel-1", Blueprint(), [Character()])

    queries = [query for query, _ in driver.session_obj.queries]
    assert any("MERGE (n:Novel {id: $id})" in query for query in queries)
    assert any("MERGE (c:Character {id: $id})" in query for query in queries)
    assert any("MERGE (n)-[:HAS_CHARACTER]->(c)" in query for query in queries)


def test_apply_delta_rejects_labels_outside_allowlist():
    driver = FakeDriver()
    repo = GraphRepository(driver=driver)
    delta = Delta()
    delta.node_upserts = [
        {"label": "Character`) DETACH DELETE n //", "id": "bad", "properties": {}}
    ]

    with pytest.raises(ValueError, match="Unsupported node label"):
        repo.apply_delta(delta)

    assert driver.session_obj.queries == []


def test_apply_delta_writes_allowed_nodes_and_relationships():
    driver = FakeDriver()
    repo = GraphRepository(driver=driver)
    delta = Delta()
    delta.node_upserts = [
        {"label": "Chapter", "id": "chapter-1", "properties": {"title": "Opening"}},
        {"label": "Event", "id": "event-1", "properties": {"summary": "A clue appears"}},
    ]
    delta.relationship_upserts = [
        {
            "source_label": "Chapter",
            "source_id": "chapter-1",
            "target_label": "Event",
            "target_id": "event-1",
            "type": "CONTAINS_EVENT",
            "properties": {"source": "chapter-1"},
        }
    ]

    repo.apply_delta(delta)

    queries = [query for query, _ in driver.session_obj.queries]
    assert any("MERGE (n:Chapter {id: $id})" in query for query in queries)
    assert any("MERGE (a)-[r:CONTAINS_EVENT]->(b)" in query for query in queries)


def test_repository_accepts_pipeline_graph_delta_directly():
    driver = FakeDriver()
    repo = GraphRepository(driver=driver)
    pipeline = DeterministicWritingPipeline()
    plan = ChapterPlan(
        chapter_number=1,
        title="雨夜来信",
        goal="让主角收到来自未来的信。",
        key_events=["未来来信出现"],
    )
    draft = pipeline.draft_chapter(plan)
    delta = pipeline.extract_graph_delta("novel-1", draft)

    repo.apply_delta(delta)

    queries = [query for query, _ in driver.session_obj.queries]
    assert any("MERGE (n:Chapter {id: $id})" in query for query in queries)
    assert any("MERGE (a)-[r:CONTAINS_EVENT]->(b)" in query for query in queries)


def test_export_visualization_returns_basic_shape_and_raw_count():
    driver = FakeDriver(rows=[{"row": 1}, {"row": 2}])
    repo = GraphRepository(driver=driver)

    result = repo.export_visualization("novel-1")

    assert result == {"nodes": [], "edges": [], "raw_count": 2}
