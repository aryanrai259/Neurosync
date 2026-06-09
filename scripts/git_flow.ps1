# Phase 5 Git Workflow
Write-Host "Committing Phase 5 changes..."
git add .
git commit -m "Phase 5 reasoning layer, config registry, dynamic entities, token budgeting, cycle detection"

Write-Host "Checking out dev branch..."
git checkout dev

Write-Host "Merging phase/5-reasoning-layer into dev..."
git merge phase/5-reasoning-layer -m "Merge Phase 5 into dev"

Write-Host "Running database migrations..."
.venv\Scripts\python -m alembic upgrade head

Write-Host "Running pytest on dev branch..."
.venv\Scripts\python -m pytest tests\integration\config\test_config_registry.py tests\integration\reasoning\test_pipeline.py

Write-Host "Running smoke test on dev branch..."
.venv\Scripts\python scripts\smoke_test_llm.py

Write-Host "Done!"
