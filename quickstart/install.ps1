$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

param(
    [string]$InstallDir = 'knowledgebase-ai'
)

$AppName = 'KnowledgeBase AI'
$ArchiveUrl = 'https://github.com/Tim-M-83/knowledgebase-ai/releases/latest/download/knowledgebase-ai.zip'
$LicenseServerAdminToken = '__LICENSE_SERVER_ADMIN_TOKEN__'
$InstallerRenderMarker = '__INSTALLER_RENDERED__'

function Write-Info {
    param([string]$Message)
    Write-Host "`n[INFO] $Message"
}

function Write-WarnText {
    param([string]$Message)
    Write-Warning $Message
}

function Fail {
    param([string]$Message)
    throw $Message
}

function Test-PortInUse {
    param([int]$Port)

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    }

    $netstatMatches = netstat -ano | Select-String -Pattern ":$Port\s"
    return [bool]$netstatMatches
}

function Assert-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Fail 'Docker is not installed. Install Docker Desktop first.'
    }

    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Fail 'Docker is installed but not running. Start Docker Desktop first.'
    }

    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        Fail 'Docker Compose plugin is required. Install Docker Desktop or a recent Docker Engine with docker compose support.'
    }
}

function Assert-PortsFree {
    foreach ($port in 3000, 8000, 5432, 6379) {
        if (Test-PortInUse -Port $port) {
            Fail "Port $port is already in use. Stop the conflicting service before installing $AppName."
        }
    }
}

function New-HexSecret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }

    return -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

function Set-EnvValue {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$Value
    )

    $lines = Get-Content -LiteralPath $FilePath
    $updated = $false
    $newLines = foreach ($line in $lines) {
        if ($line.StartsWith("$Key=")) {
            $updated = $true
            "$Key=$Value"
        }
        else {
            $line
        }
    }

    if (-not $updated) {
        $newLines += "$Key=$Value"
    }

    Set-Content -LiteralPath $FilePath -Value $newLines
}

function Wait-ForApi {
    $maxAttempts = 120
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 5 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    Fail 'The API did not become healthy in time. Check logs with: docker compose logs api'
}

function Get-BootstrapCredentials {
    param([string]$ProjectDir)

    $maxAttempts = 30
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        $logs = docker compose -f (Join-Path $ProjectDir 'docker-compose.yml') --project-directory $ProjectDir logs api --no-color 2>&1 | Out-String
        $emailMatch = [regex]::Match($logs, 'Email:\s*(.+)')
        $passwordMatch = [regex]::Match($logs, 'Password:\s*(.+)')
        if ($emailMatch.Success -and $passwordMatch.Success) {
            return [pscustomobject]@{
                Email = $emailMatch.Groups[1].Value.Trim()
                Password = $passwordMatch.Groups[1].Value.Trim()
            }
        }

        Start-Sleep -Seconds 2
    }

    return $null
}

function Main {
    if ([string]::IsNullOrWhiteSpace($LicenseServerAdminToken) -or $InstallerRenderMarker -ne 'rendered') {
        Fail 'This installer template has not been rendered with a shared LICENSE_SERVER_ADMIN_TOKEN yet.'
    }

    Assert-DockerReady
    Assert-PortsFree

    $targetPath = Join-Path (Get-Location) $InstallDir
    if (Test-Path -LiteralPath $targetPath) {
        Fail "Target directory already exists: $targetPath"
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("knowledgebase-ai-" + [guid]::NewGuid().ToString('N'))
    $archivePath = Join-Path $tempRoot 'knowledgebase-ai.zip'

    try {
        New-Item -ItemType Directory -Path $tempRoot | Out-Null

        Write-Info 'Downloading the latest stable release from GitHub'
        try {
            Invoke-WebRequest -Uri $ArchiveUrl -OutFile $archivePath
        }
        catch {
            Fail 'Could not download the latest release archive. Make sure the repository is public and the release asset exists.'
        }

        Expand-Archive -LiteralPath $archivePath -DestinationPath $tempRoot -Force

        $extractedProjectDir = Join-Path $tempRoot 'knowledgebase-ai'
        if (-not (Test-Path -LiteralPath $extractedProjectDir)) {
            Fail 'The downloaded release archive is missing the expected knowledgebase-ai folder.'
        }

        Move-Item -LiteralPath $extractedProjectDir -Destination $targetPath

        Write-Info 'Preparing environment configuration'
        Copy-Item -LiteralPath (Join-Path $targetPath '.env.example') -Destination (Join-Path $targetPath '.env')

        $envFile = Join-Path $targetPath '.env'
        Set-EnvValue -FilePath $envFile -Key 'JWT_SECRET' -Value (New-HexSecret)
        Set-EnvValue -FilePath $envFile -Key 'SECRETS_ENCRYPTION_KEY' -Value (New-HexSecret)
        Set-EnvValue -FilePath $envFile -Key 'NEXT_PUBLIC_API_URL' -Value 'http://localhost:8000'
        Set-EnvValue -FilePath $envFile -Key 'FRONTEND_URL' -Value 'http://localhost:3000'
        Set-EnvValue -FilePath $envFile -Key 'LICENSE_SERVER_BASE_URL' -Value 'https://app.automateki.de'
        Set-EnvValue -FilePath $envFile -Key 'LICENSE_SERVER_ADMIN_TOKEN' -Value $LicenseServerAdminToken
        Set-EnvValue -FilePath $envFile -Key 'LICENSE_COMPANY_NAME' -Value 'KnowledgeBase AI'
        Set-EnvValue -FilePath $envFile -Key 'LICENSE_BILLING_EMAIL' -Value ''
        Set-EnvValue -FilePath $envFile -Key 'LICENSE_WORKSPACE_ID' -Value ''
        Set-EnvValue -FilePath $envFile -Key 'LICENSE_ENFORCEMENT_ENABLED' -Value 'true'
        Set-EnvValue -FilePath $envFile -Key 'OPENAI_API_KEY' -Value ''

        Write-Info 'Starting Docker containers'
        Push-Location $targetPath
        try {
            docker compose up -d --build
        }
        finally {
            Pop-Location
        }

        Wait-ForApi
        $bootstrap = Get-BootstrapCredentials -ProjectDir $targetPath
        if (-not $bootstrap) {
            Write-WarnText 'Bootstrap credentials were not found automatically in the API logs. You can inspect them manually with: docker compose logs api --no-color'
        }

        Write-Host ''
        Write-Host '========================================================================'
        Write-Host "$AppName installed successfully."
        Write-Host 'Open: http://localhost:3000/login'
        if ($bootstrap) {
            Write-Host "Bootstrap email: $($bootstrap.Email)"
            Write-Host "Bootstrap password: $($bootstrap.Password)"
        }
        Write-Host 'Next steps:'
        Write-Host '1. Open the login page and sign in with the bootstrap credentials above.'
        Write-Host '2. Open Settings > License & Subscription.'
        Write-Host '3. Click Buy / Renew Subscription, start the 7-day free trial or purchase, then activate the installation.'
        Write-Host '4. Add your OpenAI API key later in Settings if you want to use OpenAI immediately.'
        Write-Host '========================================================================'
        Write-Host ''
    }
    finally {
        if (Test-Path -LiteralPath $tempRoot) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force
        }
    }
}

Main
