# Ableton + ChatGPT on Windows: one-line installer.
#   irm https://raw.githubusercontent.com/lukas0512/ableton-claude/main/scripts/windows/install.ps1 | iex
# Installs uv (Python), the connector (without the heavy "ear" models), the ClaudeBridge
# Remote Script into Live's User Library and cloudflared (the tunnel ChatGPT reaches the PC
# through), then puts an "Ableton + ChatGPT" shortcut on the Desktop. Running it again updates.
& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $App = Join-Path $env:LOCALAPPDATA 'AbletonClaude'
    $Repo = Join-Path $App 'repo'
    New-Item -ItemType Directory -Force -Path $App | Out-Null

    function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

    Step 'uv (gerenciador de Python)'
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    $uv = (Get-Command uv).Source
    Write-Host "uv: $uv"

    Step 'Baixando o conector (github.com/lukas0512/ableton-claude)'
    $zip = Join-Path $env:TEMP 'ableton-claude.zip'
    $tmp = Join-Path $env:TEMP 'ableton-claude-unzip'
    Invoke-WebRequest https://github.com/lukas0512/ableton-claude/archive/refs/heads/main.zip -OutFile $zip
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Expand-Archive $zip -DestinationPath $tmp
    if (Test-Path $Repo) { Remove-Item -Recurse -Force $Repo }
    Move-Item (Get-ChildItem $tmp | Select-Object -First 1).FullName $Repo
    Remove-Item -Force $zip; Remove-Item -Recurse -Force $tmp

    Step 'Instalando as dependencias (Python baixa sozinho na primeira vez)'
    Push-Location (Join-Path $Repo 'mcp_server')
    # uv reports progress on stderr, which Windows PowerShell 5.1 would turn into an error
    $ErrorActionPreference = 'Continue'
    try { & $uv sync --frozen --no-default-groups; $code = $LASTEXITCODE }
    finally { Pop-Location; $ErrorActionPreference = 'Stop' }
    if ($code) { throw "uv sync falhou (codigo $code)" }

    Step 'ClaudeBridge -> User Library do Ableton'
    $lib = $env:ABLETON_USER_LIBRARY
    if (-not $lib) { $lib = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Ableton\User Library' }
    $dest = Join-Path $lib 'Remote Scripts\ClaudeBridge'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item (Join-Path $Repo 'remote_script\ClaudeBridge\*.py') $dest -Force
    if (Test-Path (Join-Path $dest '__pycache__')) { Remove-Item -Recurse -Force (Join-Path $dest '__pycache__') }
    Set-Content -Path (Join-Path $App 'user_library.txt') -Value $lib
    Write-Host "instalado em $dest"

    Step 'cloudflared (tunel para o ChatGPT)'
    $cf = Join-Path $App 'cloudflared.exe'
    Invoke-WebRequest https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile $cf

    $tokenFile = Join-Path $App 'token.txt'
    if (-not (Test-Path $tokenFile)) {
        $bytes = New-Object byte[] 24
        [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $token = -join ($bytes | ForEach-Object { $_.ToString('x2') })
        Set-Content -Path $tokenFile -Value $token
    }

    Step 'Atalho na Area de Trabalho'
    $lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ableton + ChatGPT.lnk'
    $sh = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $sh.TargetPath = 'powershell.exe'
    $sh.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $Repo 'scripts\windows\start.ps1') + '"'
    $sh.WorkingDirectory = $App
    $sh.Save()

    Write-Host "`nPronto!" -ForegroundColor Green
    Write-Host @"
1. Abra (ou reinicie) o Ableton Live. Em Options > Preferences > Link, Tempo & MIDI,
   escolha ClaudeBridge em 'Control Surface' (Input/Output: None).
2. Clique duas vezes no atalho 'Ableton + ChatGPT' na Area de Trabalho.
   Ele mostra a URL para colar no ChatGPT (e ja copia para a area de transferencia).
Guia completo: https://github.com/lukas0512/ableton-claude/blob/main/docs/windows-chatgpt.md
"@
}
