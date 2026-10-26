# Pesquisa: o que do GitHub pode melhorar o ableton-claude (2026-10-26)

Pergunta: que repositórios, bibliotecas, modelos ou skills podemos plugar ou adaptar para
chegar mais perto de uma referência com 1-2 prompts, com mix forte (volumes, cortes,
cada elemento no seu canal, saber o que é ambiência, scratch, vocal), para usuários
leigos e avançados.

O que o app já tem e não precisa ser procurado fora: Demucs `htdemucs` (4 stems, em
`ear/stems.py`), `htdemucs_6s` em scripts, Beat This (grade), pyloudnorm, estudo de
referências, perfis de gênero, `solo_pass` (nível e mascaramento por elemento), `timbre`,
`quality_gate`, journal com revert.

Licença importa porque o produto é open source + relay pago: MIT/Apache servem;
GPL-3 só se o app for distribuído sob GPL; AGPL e CC-NC (não comercial) ficam fora do
pacote, no máximo como ideia ou como opção que o usuário instala.

Números de estrelas e datas conferidos com `gh api` em 2026-10-26.

---

## Prioridade 1: separar e reconhecer cada elemento (o pedido central)

### 1. python-audio-separator + o zoo de modelos do ZFTurbo
- [nomadkaraoke/python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator):
  MIT, 1,4k estrelas, ativo (out/2026). Uma API (`Separator().load_model(); separate()`)
  para Demucs, MDX, MDXC e RoFormer. MPS/CoreML no Apple Silicon, ensembles
  (`avg_wave`, `max_fft`), presets como `karaoke`.
- [ZFTurbo/Music-Source-Separation-Training](https://github.com/ZFTurbo/Music-Source-Separation-Training):
  MIT, 1,6k estrelas, ativo. Tabela de modelos treinados com SDR medido
  ([pretrained_models.md](https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/main/docs/pretrained_models.md)).

O que isso dá que o Demucs atual não dá (SDR em dB, maior = mais limpo):

| Alvo | Modelo | SDR | Hoje |
|---|---|---|---|
| Vocal | Mel-Band RoFormer (KimberleyJensen) / BS-RoFormer (viperx) | 10,9-11,0 | htdemucs ~8,4 |
| 4 stems | SCNet XL IHF | ~10,0 média | htdemucs 9,2 |
| Bateria em peças | DrumSep MDX23C (jarredou) | bumbo 16,7, caixa 11,5, toms 12,3, chimbal 4,0, pratos 6,4 | não existe |
| Ambiência (seco vs reverb) | Mel-Band RoFormer DeReverb/DeEcho | 10,0 | não existe |
| Público / plateia | Mel-Band RoFormer Crowd | 6,0 | não existe |
| Respiração | Mel-Band RoFormer Aspiration | 9,9 | não existe |
| Voz principal vs backing | UVR MDX-Net Karaoke 2 | (sem SDR na tabela) | não existe |

Encaixe: trocar o backend de `ear/stems.py` e `stem_remix.py` por essa API, com o modelo
escolhido por tarefa. Fluxo novo, "abrir o sample em canais": mix/loop → 4 stems (SCNet
ou RoFormer) → bateria → DrumSep (bumbo, caixa, toms, chimbal, pratos) → vocal → karaoke
(lead/backing) → dereverb (seco + ambiência). Cada stem vira uma faixa de áudio no Live,
nomeada, no mesmo lugar do original. É isso que pede "cortar elementos isolados, um em
cada canal" e "diferenciar ambiência".

Cuidados: os pesos de comunidade não têm a mesma licença do código (vários sem licença
declarada): conferir modelo por modelo antes de distribuir e baixar sob demanda para
`~/Music/Ableton Claude/Models/`, como já fazemos com o torch. O README pede crédito ao
UVR. Chimbal e pratos separam mal (3-6 dB): para hats, o filtro + `onset_chop` atual pode
continuar melhor. Cada checkpoint tem centenas de MB; a separação em CPU de uma faixa
inteira leva minutos (rodar no estudo, nunca durante render).

### 2. Etiquetar cada pedaço: vocal, rap, scratch, ambiência, FX
- [qiuqiangkong/audioset_tagging_cnn](https://github.com/qiuqiangkong/audioset_tagging_cnn)
  (PANNs): MIT, pesos públicos, 527 classes do AudioSet, roda em janelas de 2 s (detecção
  de evento no tempo). O AudioSet tem as classes que pedimos:
  [Scratching (performance technique)](https://research.google.com/audioset/ontology/scratching_performance_technique.html)
  (2.890 vídeos, rótulo 90% correto), Rapping, Singing, Speech, Reverberation, Echo, Drum
  machine, Synthesizer, Clapping, Crowd, Vinyl/crackle. Leve, roda em CPU.
- [LAION-AI/CLAP](https://github.com/LAION-AI/CLAP): código CC0, pesos treinados em música
  e fala, também no Hugging Face Transformers. Classificação por texto livre ("scratch de
  vinil", "pad com reverb longo", "vocal feminino falado") sem treinar nada.

Encaixe:
- Depois da separação, etiquetar cada trecho de cada stem (PANNs para as classes fixas,
  CLAP para o resto). Assim o produtor distingue scratch de vocal no stem "vocals" do
  Demucs (onde os dois caem juntos), acha onde está só ambiência e corta os pedaços
  certos. Entra em `stem_remix.py` (frases de rap, chops) e `onset_chop`.
- Índice de samples por som, não só por nome: embeddings CLAP de cada arquivo em
  `samples_index.json` deixam `find_samples` / `library_search` responderem a "um bumbo
  seco tipo 909" mesmo quando o arquivo se chama `kick_03.wav`. Isso ajuda muito o leigo,
  que descreve o som e não sabe o nome do pack.
- Medir antes de confiar: CLAP zero-shot erra em instrumentos finos. Testar nos kits que
  já conhecemos (let_the_rhythm, After Midnight) antes de usar como decisão.

### 3. Separar pelo que se descreve (experimental)
- [facebookresearch/sam-audio](https://github.com/facebookresearch/sam-audio) (Meta,
  dez/2025): separa qualquer som pedido por texto ou por um trecho marcado ("isola o
  scratch", "tira o público"). Pesos com acesso controlado no Hugging Face e "SAM
  License": ler a licença antes de usar comercialmente. Modelo grande.
- [Audio-AGI/AudioSep](https://github.com/Audio-AGI/AudioSep): MIT, mesma ideia, mais
  antigo, 32 kHz (perde o topo; serve para detectar, não para entregar o stem).

Uso: só para o que os modelos fixos não cobrem (scratch, foley, efeito vocal). Começar
como opção avançada.

---

## Prioridade 2: a mix chegar perto da referência

### 4. Casar EQ/compressão por stem com a referência (otimizar fora do Live)
- [csteinmetz1/st-ito](https://github.com/csteinmetz1/st-ito) (Apache-2, ativo jul/2026):
  transferência de estilo de produção por otimização na hora (estratégia evolutiva) sobre
  embeddings AFx-Rep (mid e side, 512 dimensões cada). Dá a métrica "quanto este stem soa
  processado como o da referência".
- [csteinmetz1/dasp-pytorch](https://github.com/csteinmetz1/dasp-pytorch) (Apache-2): EQ
  paramétrico, compressor, distorção, reverb diferenciáveis.
- [sai-soum/Diff-MST](https://github.com/sai-soum/Diff-MST) (ISMIR 2024, licença não
  declarada: usar como ideia): um controlador prevê ganho, pan, EQ e compressão de um
  console para N faixas a partir de uma mix de referência, sem gerar áudio.
- StemFX ([arXiv 2607.15634](https://arxiv.org/abs/2607.15634), jul/2026): prevê a cadeia
  de FX de cada stem separado, 4000x mais rápido que otimização iterativa. Sem código
  confirmado; acompanhar.

Encaixe (adaptação, não plugar direto): o gargalo hoje é que todo render é tempo real.
Ideia: modelar em scipy/torch os aparelhos que usamos (EQ Eight, Compressor, Utility,
Glue) com as fórmulas do Live; separar a referência em stems (item 1); com os stems
soloed que o `solo_pass` já grava, otimizar os parâmetros fora do Live até o espectro de
1/3 de oitava e a métrica AFx-Rep chegarem nos da referência; aplicar o resultado com
`set_param` e conferir com UM render. Isso troca dezenas de renders por um.

### 5. Gravar todos os elementos numa passada só (ideia do Agent Audio Tap)
- [bschoepke/ableton-live-mcp](https://github.com/bschoepke/ableton-live-mcp) (MIT): um
  Max for Live "Agent Audio Tap" capta áudio em qualquer ponto da cadeia para o agente
  analisar.

Encaixe: o `solo_pass` hoje renderiza um elemento por vez (N x tempo real). O Live já
permite uma faixa de áudio gravar a saída de outra (input = faixa X, "Post FX"). Armar N
faixas de gravação, uma por elemento, e gravar uma vez dá todos os stems da nossa própria
mix numa passada só. Sem dependência nova; só comandos no bridge.

### 6. Palavras do usuário → parâmetros (o que funciona com LLM)
- [SonyResearch/LLM2Fx](https://github.com/SonyResearch/LLM2Fx): dois trabalhos da Sony.
  LLM2Fx: um LLM sem treino mapeia texto ("mais quente", "mais aberto") para parâmetros de
  EQ e reverb; acerta mais quando o prompt leva (a) medidas DSP do áudio, (b) o código da
  função DSP e (c) exemplos. LLM2Fx-Tools (ICLR 2026): a partir do áudio cru e do
  processado, o LLM escreve a cadeia de tool calls (efeito, ordem, parâmetros) com
  raciocínio antes. Licença não declarada: usar o método, não o código.
- [vaclisinc/InstructFX2FX](https://github.com/vaclisinc/InstructFX2FX) (DAFx 2026): o LLM
  monta a cadeia e um refinamento guiado por CLAP ajusta os parâmetros, em várias rodadas
  de conversa. É o nosso ciclo (propor → render → comparar) com uma métrica a mais.
- [mclemcrew/MixAssist](https://github.com/mclemcrew/MixAssist) (MIT, scripts) +
  dataset ([arXiv 2507.06329](https://arxiv.org/html/2507.06329)): diálogos reais de mix
  entre profissional e amador. Serve para dois fins: exemplos de como explicar ao leigo e
  um juiz automático para avaliar as respostas do nosso produtor.

Encaixe direto, sem dependência: uma tabela "palavra → movimento" em
`briefs/lessons.md` (ou `taste.md`) com exemplos medidos ("abafado" = 2-5 kHz X dB sob o
perfil → shelf +2 dB em 3 kHz no EQ Eight), e o `producer_brief` sempre passando as medidas
do elemento junto com o pedido. É o que o LLM2Fx mostrou que melhora o acerto.

---

## Prioridade 3: taste e experiência do usuário

### 7. Taste que aprende sozinho
- [dreamrec/LivePilot](https://github.com/dreamrec/LivePilot): MCP para Live 12, licença
  BSL-1.1 (não copiar código). Ideias boas: "Taste Graph" (registra quais tipos de
  movimento o usuário mantém ou desfaz e quais aparelhos prefere), "Wonder Mode" (gera
  variantes, toca cada uma, o usuário escolhe, a escolha alimenta o taste) e relatórios
  que marcam cada achado como medido, heurística ou gosto.

Encaixe: o journal já registra cada mudança e o `revert_changes`. Contar manter/reverter
por tipo de movimento e por usuário vira um `taste.md` por usuário montado
automaticamente, igual ao que fazemos à mão com o Lukas. Para o produto isso diferencia:
cada usuário ganha seu próprio taste.

### 8. Skills de produtor
- [glincker/ableton-skills](https://github.com/glincker/ableton-skills) (MIT): skills de
  Claude para produtores (diagnóstico de mix, voice leading, humanizar MIDI). Comparar com
  `briefs/producer.md` e pegar só checklists que faltem. Baixa prioridade: nossos briefs
  já são mais específicos e medidos.

---

## Prioridade 4: segunda etapa (master, transcrição, ouvido que descreve)

| Projeto | Licença | Para quê | Observação |
|---|---|---|---|
| [sergree/matchering](https://github.com/sergree/matchering) | GPL-3 | master casada com referência (RMS, resposta, pico, largura) | o algoritmo é simples; reimplementar a ideia em `mixing.py` evita a GPL |
| [spotify/pedalboard](https://github.com/spotify/pedalboard) | GPL-3 | aplicar cadeias e VSTs offline, rápido | útil para pré-escutar sem render; GPL |
| [spotify/basic-pitch](https://github.com/spotify/basic-pitch) | Apache-2 | áudio → MIDI polifônico com bends, leve | "pega a melodia da referência" para leigo; complementa `heard_midi` |
| [mir-aidj/all-in-one](https://github.com/mir-aidj/all-in-one) | MIT | batidas, downbeats e seções rotuladas (intro, refrão...) | conferir contra o nosso `ear/arrangement.py` antes de trocar |
| [nvidia/music-flamingo-hf](https://huggingface.co/nvidia/music-flamingo-hf) | não comercial | modelo que ouve e descreve harmonia, timbre, estrutura | só pesquisa; serve para ver o que um "ouvido que fala" acertaria |
| [Qwen2-Audio](https://github.com/QwenLM/Qwen2-Audio) / Qwen3-Omni | conferir | descrever áudio em texto | pesado para Mac de usuário; candidato para o relay |
| [ace-step/ACE-Step](https://github.com/ace-step/ACE-Step) | Apache-2 | gerar texturas e one-shots quando o usuário não tem sample | o taste do Lukas é sample-first; baixa prioridade |

Fora do pacote por licença: Essentia e os modelos do MTG (AGPL; modelos CC BY-NC,
comercial só com licença da UPF), YourMT3 (GPL-3), pesos do MusicGen (CC-BY-NC).

---

## Ordem sugerida

1. **Separação melhor + bateria em peças + ambiência** (item 1): protótipo de
   `split_elements(path|track)` com python-audio-separator, medir SDR/escuta em 3 loops
   conhecidos e uma faixa da City 2 City contra o `htdemucs` atual.
2. **Etiquetas por trecho** (item 2, PANNs) no mesmo protótipo: o resultado vira faixas
   nomeadas no Live ("Bumbo", "Caixa", "Vocal lead", "Backing", "Scratch", "Ambiência").
3. **Gravação de todos os elementos numa passada** (item 5) e a **tabela palavra →
   movimento** (item 6): baratos, sem dependência.
4. **Índice CLAP dos samples** (item 2).
5. **Otimizador por stem contra a referência** (item 4) e taste automático (item 7).
6. Master casada (reimplementação), basic-pitch, ouvido que descreve.

Nada aqui foi testado ainda no app; os números são os publicados pelos autores.
