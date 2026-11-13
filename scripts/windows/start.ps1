# Starts the connector over HTTP and a Cloudflare quick tunnel, then prints the URL to paste
# into ChatGPT (Settings > Apps & Connectors > Developer mode > Create). The URL carries a
# secret token: whoever has it can drive this Ableton, so do not share it.
$ErrorActionPreference = 'Stop'
$App = Join-Path $env:LOCALAPPDATA 'AbletonClaude'
$Repo = Join-Path $App 'repo'
$Port = 8000
$server = Join-Path $Repo 'mcp_server\.venv\Scripts\ableton-claude-mcp.exe'
$cf = Join-Path $App 'cloudflared.exe'
foreach ($f in @($server, $cf, (Join-Path $App 'token.txt'))) {
    if (-not (Test-Path $f)) { Write-Host "Falta $f - rode o instalador de novo." -ForegroundColor Red; Read-Host 'Enter para sair'; exit 1 }
}
$token = (Get-Content (Join-Path $App 'token.txt') -Raw).Trim()

$env:ABLETON_MCP_TOKEN = $token
$env:ABLETON_MCP_PORT = "$Port"
$libFile = Join-Path $App 'user_library.txt'
if (Test-Path $libFile) { $env:ABLETON_USER_LIBRARY = (Get-Content $libFile -Raw).Trim() }

# Live answers on 9878 once ClaudeBridge is selected as a Control Surface
$live = $false
try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', 9878); $live = $c.Connected; $c.Close() } catch {}
if (-not $live) {
    Write-Host 'Aviso: o Ableton nao respondeu. Abra o Live e escolha ClaudeBridge em Preferences > Link, Tempo & MIDI > Control Surface.' -ForegroundColor Yellow
}

$serverLog = Join-Path $App 'server.log'
$tunnelLog = Join-Path $App 'tunnel.log'
if (Test-Path $tunnelLog) { Remove-Item $tunnelLog -Force }
$srv = Start-Process -FilePath $server -ArgumentList '--http' -WindowStyle Hidden -PassThru `
    -RedirectStandardError $serverLog -RedirectStandardOutput (Join-Path $App 'server.out.log')
$tunErr = Join-Path $App 'tunnel.err.log'
$tun = Start-Process -FilePath $cf -ArgumentList "tunnel --no-autoupdate --logfile `"$tunnelLog`" --url http://127.0.0.1:$Port" `
    -WindowStyle Hidden -PassThru -RedirectStandardError $tunErr -RedirectStandardOutput (Join-Path $App 'tunnel.out.log')

function Read-Shared($path) {
    # the writer keeps the log open: read it without asking for exclusive access
    try {
        $fs = [IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
        try { (New-Object IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Close() }
    } catch { '' }
}

try {
    Write-Host 'Abrindo o tunel...'
    $base = $null
    for ($i = 0; $i -lt 60 -and -not $base; $i++) {
        Start-Sleep -Seconds 1
        if ($srv.HasExited) { throw "O conector parou. Veja $serverLog" }
        if ($tun.HasExited) { throw "O tunel parou. Veja $tunErr" }
        $text = (Read-Shared $tunnelLog) + (Read-Shared $tunErr)
        $m = [regex]::Match($text, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($m.Success) { $base = $m.Value }
    }
    if (-not $base) { throw "O tunel nao abriu em 60 s. Veja $tunnelLog" }
    $url = "$base/$token/mcp"
    try { Set-Clipboard -Value $url } catch {}

    Write-Host "`nURL do conector (ja copiada):`n" -ForegroundColor Green
    Write-Host "  $url`n" -ForegroundColor White
    Write-Host 'No ChatGPT: Configuracoes > Apps e conectores > Avancado > Modo desenvolvedor (ligado),'
    Write-Host 'depois Criar: cole a URL, Autenticacao = Sem autenticacao, marque que confia.'
    Write-Host 'A URL muda toda vez que voce abre este atalho: atualize o conector no ChatGPT.'
    Write-Host 'Nao compartilhe essa URL: quem tiver ela controla o seu Ableton.' -ForegroundColor Yellow
    Read-Host "`nDeixe esta janela aberta enquanto usa. Aperte Enter para desligar"
}
catch {
    Write-Host $_ -ForegroundColor Red
    Read-Host 'Enter para sair'
}
finally {
    foreach ($p in @($tun, $srv)) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
}
