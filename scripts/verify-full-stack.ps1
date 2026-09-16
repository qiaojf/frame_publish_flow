param(
    [int]$StartupTimeoutSeconds = 180,
    [int]$WorkflowTimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$originalLocation = (Get-Location).Path

try {
    Set-Location -LiteralPath $projectRoot
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw '未找到 Docker。请先安装并启动 Docker Desktop。'
    }
    & docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker daemon 不可用，请先启动 Docker Desktop。'
    }

    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) {
        Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination (Join-Path $projectRoot '.env')
        Write-Host '[verify] 已从 .env.example 创建开发环境 .env'
    }

    Write-Host '[verify] 构建并启动 PostgreSQL、Redis、API、Celery Worker 和前端...'
    & docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        throw 'docker compose up 失败。'
    }

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $healthy = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 3
        }
    }
    if (-not $healthy) {
        throw "API 在 $StartupTimeoutSeconds 秒内未通过健康检查。"
    }

    Write-Host '[verify] 检查 Alembic 当前版本和 ORM/Migration 漂移...'
    & docker compose exec -T api alembic current
    if ($LASTEXITCODE -ne 0) {
        throw '无法读取 Alembic 当前版本。'
    }
    & docker compose exec -T api alembic check
    if ($LASTEXITCODE -ne 0) {
        throw 'ORM 与 Alembic Migration 存在结构漂移。'
    }

    Write-Host '[verify] 服务已就绪，执行真实全栈业务闭环...'
    # Route business requests through the frontend Nginx so upload-size and
    # reverse-proxy behavior are covered as part of the real full-stack test.
    & docker compose exec -T api python scripts/integration_smoke.py --base-url http://frontend --timeout $WorkflowTimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
        throw '全栈业务闭环验证失败。'
    }

    Write-Host '[verify] PASS：完整联调通过。服务保持运行，可访问 http://localhost:5173 继续人工测试。'
}
catch {
    Write-Error $_
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host '[verify] 最近的 API/Worker 日志：'
        & docker compose logs --tail=200 api worker
    }
    exit 1
}
finally {
    Set-Location -LiteralPath $originalLocation
}
