<#
.SYNOPSIS
    Helper script to apply Alembic migrations and run audit backfill on a staging environment.

.DESCRIPTION
    Activates the project's virtualenv, runs Alembic migrations using the project's
    alembic.ini, then executes the backfill script. Set `-Config` to 'production' or
    the config name used by your deployment (e.g., 'production').

USAGE
    .\deploy_staging.ps1 -Config production -Batch 500
#>

param(
    [string]$Config = "production",
    [int]$Batch = 500,
    [string]$AlembicIni = "alembic.ini"
)

Write-Host "Applying migrations and running backfill (config=$Config, batch=$Batch)"

if (-Not (Test-Path -Path .\.venv\Scripts\Activate.ps1)) {
    Write-Error ".venv not found or virtualenv missing. Activate manually and re-run."
    exit 1
}

# Activate venv
& .\.venv\Scripts\Activate.ps1

# Ensure FLASK_ENV is set so create_app picks the right configuration
$env:FLASK_ENV = $Config

Write-Host "Running Alembic upgrade head..."
try {
    # Use the alembic executable from the venv to avoid PATH issues
    $alembicExe = Join-Path -Path ".\.venv\Scripts" -ChildPath "alembic.exe"
    if (-Not (Test-Path $alembicExe)) { $alembicExe = "alembic" }
    & $alembicExe -c $AlembicIni upgrade head
}
catch {
    Write-Error "Alembic migration failed: $_"
    exit 2
}

Write-Host "Running audit backfill script..."
try {
    python scripts/backfill_audit_details.py --config $Config --batch $Batch
}
catch {
    Write-Error "Backfill script failed: $_"
    exit 3
}

Write-Host "Migrations and backfill completed. Please verify application health and sampling checks."
Write-Host "Example verification (row counts):"
try {
    python - <<'PY'
    from app import create_app, db
    from app.models.inventory import AuditLog
    app = create_app($env:FLASK_ENV)
    with app.app_context():
    print('Total audit logs:', AuditLog.query.count())
    PY
}
catch {
    # non-fatal
}

Write-Host "Done."
