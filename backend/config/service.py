# Purpose:      Config service and Neo4j graph synchronization logic.
#               Ensures that the authoritative PostgreSQL config registry is
#               idempotently projected into Neo4j as high-confidence edges.
# Called By:    api/v1/config.py
# Dependencies: config_repo.py, neo4j, sqlalchemy

import logging
from uuid import UUID

from neo4j import AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.config_repo import config_repo
from backend.graph.client import get_driver

logger = logging.getLogger(__name__)


class ConfigGraphSyncer:
    """
    Synchronizes PostgreSQL Configuration Registry into Neo4j.
    Creates authoritative (confidence=1.0) nodes and edges for:
      - Teams
      - Services
      - Repositories
      - Team -> OWNS -> Service
      - Service -> DEPENDS_ON -> Service
      - Repository -> REPOSITORY_OF -> Service
    """

    def __init__(self, driver: AsyncDriver | None = None):
        self.driver = driver or get_driver()

    async def sync_workspace(self, session: AsyncSession, workspace_id: UUID) -> None:
        """
        Pull all config state for a workspace and execute idempotent MERGEs
        in Neo4j to project the graph.
        """
        version = await config_repo.get_version(session, workspace_id)
        
        teams = await config_repo.get_teams(session, workspace_id)
        services = await config_repo.get_services(session, workspace_id)
        repos = await config_repo.get_repositories(session, workspace_id)
        ownerships = await config_repo.get_ownership(session, workspace_id)
        dependencies = await config_repo.get_dependencies(session, workspace_id)

        w_id = str(workspace_id)

        async with self.driver.session() as neo4j_session:
            # 1. Upsert Teams
            for team in teams:
                await neo4j_session.run(
                    """
                    MERGE (t:Team {workspace_id: $workspace_id, canonical_name: $name})
                    ON CREATE SET t.confidence = 1.0, t.extraction_source = 'config_registry'
                    ON MATCH SET t.confidence = 1.0, t.extraction_source = 'config_registry'
                    """,
                    workspace_id=w_id,
                    name=team.name,
                )

            # 2. Upsert Services
            service_map = {}
            for svc in services:
                service_map[svc.id] = svc.name
                await neo4j_session.run(
                    """
                    MERGE (s:Service {workspace_id: $workspace_id, canonical_name: $name})
                    ON CREATE SET s.confidence = 1.0, s.extraction_source = 'config_registry'
                    ON MATCH SET s.confidence = 1.0, s.extraction_source = 'config_registry'
                    """,
                    workspace_id=w_id,
                    name=svc.name,
                )

            # 3. Upsert Repositories and REPOSITORY_OF edges
            for repo in repos:
                service_name = service_map.get(repo.service_id)
                if not service_name:
                    continue
                await neo4j_session.run(
                    """
                    MERGE (r:Repository {workspace_id: $workspace_id, canonical_name: $repo_url})
                    ON CREATE SET r.confidence = 1.0, r.extraction_source = 'config_registry'
                    ON MATCH SET r.confidence = 1.0, r.extraction_source = 'config_registry'
                    """,
                    workspace_id=w_id,
                    repo_url=repo.repo_url,
                )
                await neo4j_session.run(
                    """
                    MATCH (r:Repository {workspace_id: $workspace_id, canonical_name: $repo_url})
                    MATCH (s:Service {workspace_id: $workspace_id, canonical_name: $service_name})
                    MERGE (r)-[rel:REPOSITORY_OF]->(s)
                    ON CREATE SET rel.confidence = 1.0, rel.extraction_source = 'config_registry'
                    ON MATCH SET rel.confidence = 1.0, rel.extraction_source = 'config_registry'
                    """,
                    workspace_id=w_id,
                    repo_url=repo.repo_url,
                    service_name=service_name,
                )

            # 4. Upsert OWNS edges
            team_map = {t.id: t.name for t in teams}
            for own in ownerships:
                t_name = team_map.get(own.team_id)
                s_name = service_map.get(own.service_id)
                if t_name and s_name:
                    await neo4j_session.run(
                        """
                        MATCH (t:Team {workspace_id: $workspace_id, canonical_name: $t_name})
                        MATCH (s:Service {workspace_id: $workspace_id, canonical_name: $s_name})
                        MERGE (t)-[rel:OWNS]->(s)
                        ON CREATE SET rel.confidence = 1.0, rel.extraction_source = 'config_registry'
                        ON MATCH SET rel.confidence = 1.0, rel.extraction_source = 'config_registry'
                        """,
                        workspace_id=w_id,
                        t_name=t_name,
                        s_name=s_name,
                    )

            # 5. Upsert DEPENDS_ON edges
            for dep in dependencies:
                s1_name = service_map.get(dep.service_id)
                s2_name = service_map.get(dep.depends_on_service_id)
                if s1_name and s2_name:
                    await neo4j_session.run(
                        """
                        MATCH (s1:Service {workspace_id: $workspace_id, canonical_name: $s1_name})
                        MATCH (s2:Service {workspace_id: $workspace_id, canonical_name: $s2_name})
                        MERGE (s1)-[rel:DEPENDS_ON]->(s2)
                        ON CREATE SET rel.confidence = 1.0, rel.extraction_source = 'config_registry'
                        ON MATCH SET rel.confidence = 1.0, rel.extraction_source = 'config_registry'
                        """,
                        workspace_id=w_id,
                        s1_name=s1_name,
                        s2_name=s2_name,
                    )

        logger.info(f"ConfigGraphSyncer synced workspace {w_id} at registry version {version}")

config_graph_syncer = ConfigGraphSyncer()
