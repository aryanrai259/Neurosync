import pytest
import pytest_asyncio
from uuid import uuid4

from backend.db.repositories.config_repo import config_repo
from backend.db.models.config import (
    ConfigTeamModel,
    ConfigServiceModel,
    ConfigRepositoryModel,
)

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def workspace_id(db_session):
    return uuid4()

async def test_duplicate_team_name(db_session, workspace_id):
    # Upsert should handle duplicates cleanly via on_conflict_do_update
    team1 = await config_repo.upsert_team(db_session, workspace_id, "Backend Team", "Original")
    team2 = await config_repo.upsert_team(db_session, workspace_id, "Backend Team", "Updated")
    
    await db_session.commit()
    
    teams = await config_repo.get_teams(db_session, workspace_id)
    assert len(teams) == 1
    assert teams[0].description == "Updated"

async def test_duplicate_service_name(db_session, workspace_id):
    svc1 = await config_repo.upsert_service(db_session, workspace_id, "auth-service")
    svc2 = await config_repo.upsert_service(db_session, workspace_id, "auth-service")
    
    await db_session.commit()
    
    services = await config_repo.get_services(db_session, workspace_id)
    assert len(services) == 1
    assert services[0].id == svc1.id
    assert services[0].id == svc2.id

async def test_duplicate_repository_url(db_session, workspace_id):
    svc1 = await config_repo.upsert_service(db_session, workspace_id, "svc1")
    svc2 = await config_repo.upsert_service(db_session, workspace_id, "svc2")
    await db_session.commit()
    
    repo1 = await config_repo.upsert_repository(db_session, workspace_id, "https://github.com/org/repo", svc1.id)
    repo2 = await config_repo.upsert_repository(db_session, workspace_id, "https://github.com/org/repo", svc2.id)
    
    await db_session.commit()
    
    repos = await config_repo.get_repositories(db_session, workspace_id)
    assert len(repos) == 1
    assert repos[0].service_id == svc2.id

async def test_registry_version_incrementing(db_session, workspace_id):
    v1 = await config_repo.get_version(db_session, workspace_id)
    assert v1 == 0
    
    await config_repo.upsert_team(db_session, workspace_id, "T1")
    await db_session.commit()
    
    v2 = await config_repo.get_version(db_session, workspace_id)
    assert v2 == 1
    
    await config_repo.upsert_service(db_session, workspace_id, "S1")
    await db_session.commit()
    
    v3 = await config_repo.get_version(db_session, workspace_id)
    assert v3 == 2

async def test_invalid_ownership_references(db_session, workspace_id):
    # Foreign key constraints should prevent invalid ownership mappings
    # But overwrite_ownership bulk deletes/inserts, let's see if it throws IntegrityError
    from sqlalchemy.exc import IntegrityError
    
    with pytest.raises(IntegrityError):
        await config_repo.overwrite_ownership(
            db_session, 
            workspace_id, 
            [{"team_id": uuid4(), "service_id": uuid4()}]
        )
        await db_session.flush()

async def test_dependency_cycle_detection(db_session, workspace_id):
    # Config repo does not currently detect cycles. It allows them. 
    # This is a known architectural drift/missing validation.
    # We will write the test to assert it DOES NOT throw, which proves the bug exists.
    svc1 = await config_repo.upsert_service(db_session, workspace_id, "S1")
    svc2 = await config_repo.upsert_service(db_session, workspace_id, "S2")
    
    await config_repo.overwrite_dependencies(
        db_session, 
        workspace_id, 
        [
            {"service_id": svc1.id, "depends_on_service_id": svc2.id},
            {"service_id": svc2.id, "depends_on_service_id": svc1.id}
        ]
    )
    await db_session.commit()
    
    deps = await config_repo.get_dependencies(db_session, workspace_id)
    assert len(deps) == 2
