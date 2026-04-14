"""Neo4j database client with connection pooling and meal operations."""

import structlog
from neo4j import GraphDatabase
from config import settings
from models.meal import Meal

log = structlog.get_logger()


class Neo4jClient:
    """Thread-safe Neo4j driver wrapper."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self._uri = uri or settings.neo4j_uri
        self._user = user or settings.neo4j_user
        self._password = password or settings.neo4j_password
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            log.info("neo4j_connected", uri=self._uri)
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            log.info("neo4j_disconnected")

    def verify_connectivity(self) -> bool:
        """Test the connection."""
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            log.error("neo4j_connection_failed", error=str(e))
            return False

    # ── Meal queries ─────────────────────────────────────────────────────────

    def get_meals_by_slot(
        self, slot: str, diet_type: str, limit: int = 20
    ) -> list[Meal]:
        """Fetch meals for a specific slot and diet type."""
        query = """
        MATCH (m:Meal)
        WHERE m.meal_slot = $slot
          AND (m.diet_type = $diet_type OR $diet_type = 'any')
        RETURN m
        LIMIT $limit
        """
        return self._run_meal_query(query, slot=slot, diet_type=diet_type, limit=limit)

    def get_meals_by_tags(
        self, tags: list[str], diet_type: str, limit: int = 20
    ) -> list[Meal]:
        """Fetch meals that match any of the given tags."""
        query = """
        MATCH (m:Meal)
        WHERE ANY(tag IN $tags WHERE tag IN m.tags)
          AND (m.diet_type = $diet_type OR $diet_type = 'any')
        RETURN m
        LIMIT $limit
        """
        return self._run_meal_query(query, tags=tags, diet_type=diet_type, limit=limit)

    def get_meals_for_persona(
        self,
        persona: str,
        diet_type: str,
        avoid_conditions: list[str] | None = None,
        avoid_ids: list[str] | None = None,
        limit: int = 30,
    ) -> list[Meal]:
        """
        Fetch meals suitable for a persona, filtering out those that should
        be avoided for specific medical conditions or already-used IDs.
        """
        avoid_conditions = avoid_conditions or []
        avoid_ids = avoid_ids or []

        query = """
        MATCH (m:Meal)
        WHERE (m.diet_type = $diet_type OR $diet_type = 'any')
          AND NOT m.id IN $avoid_ids
          AND NONE(c IN $avoid_conditions WHERE c IN m.avoid_for)
        RETURN m
        ORDER BY
          CASE WHEN $persona IN m.suitable_for THEN 0 ELSE 1 END,
          m.protein DESC
        LIMIT $limit
        """
        return self._run_meal_query(
            query,
            persona=persona,
            diet_type=diet_type,
            avoid_conditions=avoid_conditions,
            avoid_ids=avoid_ids,
            limit=limit,
        )

    def get_meal_by_id(self, meal_id: str) -> Meal | None:
        """Fetch a single meal by ID."""
        query = "MATCH (m:Meal {id: $meal_id}) RETURN m"
        meals = self._run_meal_query(query, meal_id=meal_id)
        return meals[0] if meals else None

    def get_all_meals(self) -> list[Meal]:
        """Fetch all meals from the database."""
        query = "MATCH (m:Meal) RETURN m"
        return self._run_meal_query(query)

    def get_meal_count(self) -> int:
        """Get total meal count."""
        with self.driver.session() as session:
            result = session.run("MATCH (m:Meal) RETURN count(m) AS count")
            return result.single()["count"]

    def get_high_protein_meals(
        self, min_protein: float, diet_type: str, limit: int = 20
    ) -> list[Meal]:
        """Fetch meals with protein above a threshold."""
        query = """
        MATCH (m:Meal)
        WHERE m.protein >= $min_protein
          AND (m.diet_type = $diet_type OR $diet_type = 'any')
        RETURN m
        ORDER BY m.protein DESC
        LIMIT $limit
        """
        return self._run_meal_query(
            query, min_protein=min_protein, diet_type=diet_type, limit=limit
        )

    def get_low_sodium_meals(
        self, max_sodium: float, diet_type: str, limit: int = 20
    ) -> list[Meal]:
        """Fetch meals under a sodium threshold."""
        query = """
        MATCH (m:Meal)
        WHERE m.sodium <= $max_sodium
          AND (m.diet_type = $diet_type OR $diet_type = 'any')
        RETURN m
        ORDER BY m.sodium ASC
        LIMIT $limit
        """
        return self._run_meal_query(
            query, max_sodium=max_sodium, diet_type=diet_type, limit=limit
        )

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run_meal_query(self, query: str, **params) -> list[Meal]:
        """Execute a Cypher query and return a list of Meal objects."""
        meals = []
        with self.driver.session() as session:
            result = session.run(query, **params)
            for record in result:
                node = record["m"]
                try:
                    meal = Meal.from_neo4j(dict(node))
                    meals.append(meal)
                except Exception as e:
                    log.warning(
                        "meal_parse_error",
                        meal_id=dict(node).get("id", "unknown"),
                        error=str(e),
                    )
        return meals


# Singleton instance
neo4j_client = Neo4jClient()
