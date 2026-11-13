# Ableton + ChatGPT no Windows

O ChatGPT controla o Ableton Live do seu PC por este conector: cria faixas, clips, MIDI,
carrega instrumentos, mexe em mixer e arranjo.

## O que você precisa

- Windows 10 ou 11 e Ableton Live 11 ou 12.
- ChatGPT num plano que tenha o **Modo desenvolvedor** (Plus, Pro, Business...), no site
  chatgpt.com ou no app de desktop.

## 1. Instalar (uma vez)

Abra o **PowerShell** (menu Iniciar → digite "PowerShell") e cole:

```powershell
irm https://raw.githubusercontent.com/lukas0512/ableton-claude/main/scripts/windows/install.ps1 | iex
```

O instalador:
- instala o `uv`, que baixa o Python sozinho;
- baixa o conector para `%LOCALAPPDATA%\AbletonClaude`;
- copia o **ClaudeBridge** para `Documentos\Ableton\User Library\Remote Scripts`;
- baixa o `cloudflared`, que dá ao ChatGPT um endereço HTTPS que chega ao seu PC;
- cria o atalho **Ableton + ChatGPT** na Área de Trabalho.

Para atualizar depois, é só rodar o mesmo comando de novo.

Se a sua User Library do Ableton não estiver em `Documentos\Ableton\User Library`, veja o
caminho em Live → Options → Preferences → Library e rode o instalador assim:

```powershell
$env:ABLETON_USER_LIBRARY = 'D:\Caminho\User Library'; irm https://raw.githubusercontent.com/lukas0512/ableton-claude/main/scripts/windows/install.ps1 | iex
```

## 2. Ligar o ClaudeBridge no Ableton (uma vez)

1. Abra (ou reinicie) o Live.
2. Options → Preferences → **Link, Tempo & MIDI**.
3. Numa linha vazia de **Control Surface**, escolha **ClaudeBridge** (Input e Output: None).

## 3. Toda vez que for usar

1. Abra o Live com o seu projeto.
2. Clique duas vezes em **Ableton + ChatGPT** na Área de Trabalho. A janela mostra uma URL
   `https://….trycloudflare.com/<código>/mcp` e já copia ela.
3. No ChatGPT: **Configurações → Apps e conectores → Avançado → Modo desenvolvedor** (ligar).
   Depois **Criar** conector: nome "Ableton", cole a URL, Autenticação **Sem autenticação**,
   marque que confia no app, salve.
4. Num chat novo, ative o conector (botão **+** → Modo desenvolvedor → Ableton) e peça, por
   exemplo: *"Use o Ableton: veja o status do Live e crie um groove de house de 8 compassos a 126 BPM."*

Deixe a janela do atalho aberta enquanto usa; Enter nela desliga tudo.

**A URL muda toda vez que você abre o atalho** (é um túnel grátis e temporário): edite o
conector no ChatGPT e cole a nova. **Não compartilhe a URL**: quem tiver ela controla o seu
Ableton enquanto a janela estiver aberta.

## Limites no Windows

- Funciona: tudo que mexe no Live (faixas, clips, notas, devices, mixer, arranjo, locators,
  render) e as ferramentas de música (acordes, grooves, baterias).
- Não vem instalado: o "ouvido" pesado (separar stems, ouvir referências, notas de estética),
  que precisa de PyTorch. Essas ferramentas respondem com erro.
- O app MOTRA (interface gráfica) é só para Mac.

## Problemas

- **"o Ableton não respondeu"**: o Live está fechado ou o ClaudeBridge não está escolhido em
  Control Surface.
- **O túnel não abriu**: veja `%LOCALAPPDATA%\AbletonClaude\tunnel.log` (firewall ou antivírus
  podem bloquear o `cloudflared.exe`).
- **O conector parou**: veja `%LOCALAPPDATA%\AbletonClaude\server.log`.
- **Render falha com "playback never started"**: o Live está sem placa de som de saída
  (Preferences → Audio).
