from __future__ import annotations

from typing import Any


ALLOWED_NODE_LABELS = frozenset({"Novel", "Character", "Chapter", "Event", "Hook"})
ALLOWED_RELATIONSHIP_TYPES = frozenset(
    {
        "HAS_CHARACTER",
        "CONTAINS_EVENT",
        "HAS_CHAPTER",
        "MENTIONS",
        "ADVANCES_HOOK",
        "RELATED_TO",
    }
)


class GraphRepository:
    def __init__(self, driver: Any | None = None, settings: Any | None = None):
        self.settings = settings
        self.driver = driver or self._create_driver(settings)

    def close(self) -> None:
        self.driver.close()

    def ensure_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT novel_id IF NOT EXISTS FOR (n:Novel) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT character_id IF NOT EXISTS FOR (n:Character) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (n:Chapter) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (n:Event) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT hook_id IF NOT EXISTS FOR (n:Hook) REQUIRE n.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)

    def upsert_initial_graph(
        self,
        project_id: str,
        blueprint: Any,
        characters: list[Any],
    ) -> None:
        with self.driver.session() as session:
            session.run(
                """
                MERGE (n:Novel {id: $id})
                SET n.title = $title,
                    n.genre = $genre,
                    n.premise = $premise,
                    n.main_conflict = $main_conflict,
                    n.worldview = $worldview,
                    n.protagonist_arc = $protagonist_arc,
                    n.ending_direction = $ending_direction
                """,
                id=project_id,
                title=blueprint.title,
                genre=blueprint.genre,
                premise=blueprint.premise,
                main_conflict=blueprint.main_conflict,
                worldview=blueprint.worldview,
                protagonist_arc=blueprint.protagonist_arc,
                ending_direction=blueprint.ending_direction,
            )
            for character in characters:
                character_data = _to_dict(character)
                session.run(
                    """
                    MERGE (c:Character {id: $id})
                    SET c += $properties
                    WITH c
                    MATCH (n:Novel {id: $project_id})
                    MERGE (n)-[:HAS_CHARACTER]->(c)
                    """,
                    id=character_data["id"],
                    project_id=project_id,
                    properties=character_data,
                )

    def apply_delta(self, delta: Any) -> None:
        self._validate_delta(delta)
        with self.driver.session() as session:
            for node in delta.node_upserts:
                label = node["label"]
                session.run(
                    f"MERGE (n:{label} {{id: $id}}) SET n += $properties",
                    id=node["id"],
                    properties=node.get("properties", {}),
                )
            for relationship in delta.relationship_upserts:
                source_label = relationship["source_label"]
                target_label = relationship["target_label"]
                relationship_type = relationship["type"]
                session.run(
                    f"""
                    MATCH (a:{source_label} {{id: $source_id}})
                    MATCH (b:{target_label} {{id: $target_id}})
                    MERGE (a)-[r:{relationship_type}]->(b)
                    SET r += $properties
                    """,
                    source_id=relationship["source_id"],
                    target_id=relationship["target_id"],
                    properties=relationship.get("properties", {}),
                )

    def export_visualization(self, project_id: str) -> dict[str, Any]:
        with self.driver.session() as session:
            rows = list(
                session.run(
                    """
                    MATCH (n:Novel {id: $project_id})-[r*0..2]-(m)
                    RETURN n, r, m
                    LIMIT 200
                    """,
                    project_id=project_id,
                )
            )
        return {"nodes": [], "edges": [], "raw_count": len(rows)}

    def _validate_delta(self, delta: Any) -> None:
        for node in delta.node_upserts:
            label = node.get("label")
            if label not in ALLOWED_NODE_LABELS:
                raise ValueError(f"Unsupported node label: {label}")
        for relationship in delta.relationship_upserts:
            source_label = relationship.get("source_label")
            target_label = relationship.get("target_label")
            relationship_type = relationship.get("type")
            if source_label not in ALLOWED_NODE_LABELS:
                raise ValueError(f"Unsupported source label: {source_label}")
            if target_label not in ALLOWED_NODE_LABELS:
                raise ValueError(f"Unsupported target label: {target_label}")
            if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
                raise ValueError(f"Unsupported relationship type: {relationship_type}")

    def _create_driver(self, settings: Any | None):
        if settings is None:
            settings = _load_settings()
        from neo4j import GraphDatabase

        self.settings = settings
        return GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))


def _load_settings() -> Any:
    try:
        from .config import Neo4jSettings
    except ImportError:
        return _DefaultNeo4jSettings()
    return Neo4jSettings()


class _DefaultNeo4jSettings:
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "change_me"


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return value.__dict__.copy()
    return dict(value)
