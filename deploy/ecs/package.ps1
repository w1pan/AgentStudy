$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$archivePath = Join-Path $projectRoot ('deploy/qingheng-ecs-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.tar.gz')

Push-Location (Join-Path $projectRoot 'Agent')
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally {
    Pop-Location
}

Push-Location $projectRoot
try {
    # Explicit allowlist: do not upload .env, local databases, or virtual environments.
    & tar.exe -czf $archivePath --exclude=__pycache__ --exclude=*.pyc --exclude=.env --exclude=.env.local --exclude=*.dump --exclude=*.pem --exclude=*.key `
        Agent/dist agent-learning/app agent-learning/db `
        agent-learning/pyproject.toml agent-learning/uv.lock agent-learning/README.md `
        deploy/ecs/compose.yaml deploy/ecs/Dockerfile.api deploy/ecs/Dockerfile.api.dockerignore `
        deploy/ecs/Dockerfile.web deploy/ecs/Dockerfile.web.dockerignore `
        deploy/ecs/nginx.conf deploy/ecs/.env.example deploy/ecs/README.md deploy/ecs/install-docker-ubuntu.sh
    if ($LASTEXITCODE -ne 0) { throw 'Archive creation failed.' }
} finally {
    Pop-Location
}
Write-Output "Deployment archive: $archivePath"
