# Pesquisa 2: gosto, sentimento e velocidade (2026-10-28)

Pergunta: que repositórios com estrelas e avaliados pela comunidade podemos plugar para
(1) ouvir e julgar house, deep house e minimal com gosto, (2) sentir tensão e alívio, e
(3) gastar menos tokens, renderizar mais rápido e decidir mais rápido junto com o usuário.

Continua [research-github-2026-10.md](research-github-2026-10.md): o que já está lá
(separação, PANNs, CLAP para samples, matchering, pedalboard, all-in-one, basic-pitch,
LivePilot) não se repete aqui.

Regra de licença (produto open source + relay pago): MIT/Apache/BSD/CC-BY servem.
GPL só como ideia. CC-BY-NC e AGPL ficam fora do pacote, no máximo como opção que o
usuário instala. Estrelas e licenças conferidas com `gh api` e a API do Hugging Face hoje.

---

## A. Gosto e qualidade: o que funcionou no teste

### 1. Meta audiobox-aesthetics: testado nas faixas do Lukas
[facebookresearch/audiobox-aesthetics](https://github.com/facebookresearch/audiobox-aesthetics)
(777 estrelas, código e pesos **CC-BY 4.0**: uso comercial com crédito). Dá quatro notas de
1 a 10 por trecho:

- **CE**: quanto agrada;
- **CU**: quanto serve para uso;
- **PC**: complexidade da produção;
- **PQ**: qualidade da produção.

Medido aqui (janelas de 10 s, Mac Apple Silicon): **1,7 s para a faixa inteira** de
5,7 min, sem placa de vídeo.

| | CE | CU | PC | PQ |
|---|---|---|---|---|
| Murder v30 | 7,11 | 7,98 | 6,31 | 8,17 |
| Murder v31 | 7,13 | 8,00 | 6,29 | 8,19 |
| 10 refs Dub House Streets (mediana) | **7,37** | 8,14 | 6,39 | **8,26** |
| faixa de variação das refs | 6,73-7,67 | | | 7,54-8,40 |

O que isso mostra:
- A v31 ganhou pouco no total. Nos breaks e builds, porém, subiu de 0,2 a 0,3 em CE e PQ
  (compassos 47-52 e 93-104). Pelo modelo, a mix nova soa mais limpa justamente onde
  ficou mais vazia.
- A v31 está dentro da faixa das referências, mas 0,24 abaixo da mediana em CE.
- **Não mede tensão.** A nota não cai no break nem sobe no drop. Mede qualidade e o quanto
  agrada.

Encaixe:
- Uma ferramenta `aesthetics` que roda depois de cada render: nota por seção e distância
  até as refs do estudo.
- Uma trava no `quality_gate`: nenhuma mudança pode baixar o PQ de uma seção mais que X.
- Desempate entre duas variantes curtas antes de mostrar ao usuário.

Instala com `pip install audiobox_aesthetics`. O torchaudio novo precisa de `torchcodec`
para abrir arquivos, então carregamos com soundfile, como o resto do app.

### 2. Recompensa calibrada pelo próprio usuário: a ideia do TuneJury
[yonghyunk1m/TuneJury](https://github.com/yonghyunk1m/TuneJury) (2026, CC-BY-NC, só a
ideia). É uma cabeça pequena de 2,8 M parâmetros sobre um encoder congelado, treinada com
votos A contra B, mais uma calibração Bradley-Terry com poucos votos. Acerta 72 % dos
pares no Music Arena.

Para nós, reimplementar com código próprio:
- Os votos são os "mantém/desfaz" do journal (`taste_report`) e as escolhas entre duas
  variantes.
- O encoder é o do audiobox (CC-BY).
- O resultado é um "gosto do Lukas" que aprende sozinho. Cada usuário do produto ganha o
  seu.

Parecido: [WuqnEl/MuseCritic](https://github.com/WuqnEl/MuseCritic) (sem licença). Escreve
uma crítica em texto em 5 dimensões antes de dar a nota, um bom formato para explicar ao
usuário o porquê.

---

## B. Sentimento, tensão e alívio

| Projeto | Licença | O que dá | Veredito |
|---|---|---|---|
| [AMAAI-Lab/Music2Emotion](https://github.com/AMAAI-Lab/Music2Emotion) | Apache-2 (código), mas usa o MERT, que é CC-BY-NC | valência e excitação (1-9) e humores | janela a janela daria a curva de energia/emoção. Fora do pacote por causa do MERT; opção instalável |
| [OpenMuQ/MuQ](https://github.com/tencent-ailab/MuQ), [MERT](https://huggingface.co/m-a-p/MERT-v1-95M) | CC-BY-NC | embeddings de música de ponta | só pesquisa |
| [MAEST](https://github.com/palonso/MAEST) / Discogs-EffNet (Essentia) | AGPL / CC-BY-NC-SA | 400 estilos do Discogs: **Deep House, Minimal, Tech House, Microhouse** | o único que conhece os subgêneros underground pelo nome. Opção instalável para "isso soa deep house?" |
| [ASLP-lab/SongEval](https://github.com/ASLP-lab/SongEval) | conflito (Apache no GitHub, CC-BY-NC-SA no README) | coerência, memorável, estrutura, musicalidade | treinado em canções com voz; não serve para house instrumental |
| [felixmeyer6/drop-detector](https://github.com/felixmeyer6/drop-detector) | GPL-3, 5 estrelas | drops de EDM, F1 0,95 segundo o autor | o `production_review` já acha os drops; só ideia |
| [Gariscat/housex-v2](https://github.com/Gariscat/housex-v2) | BSD-3 | subgêneros de house | é house mainstream (big room, future), não underground |
| [laion/larger_clap_music](https://huggingface.co/laion/larger_clap_music) | Apache-2 | áudio e texto ("build tenso", "drop cheio") | **testado e falhou:** com o transformers atual (5.21 e 4.46) os embeddings saem desalinhados (cosseno ~0, curva plana). Precisaria do pacote original `laion_clap`; não validado |

Conclusão: **não existe medidor de tensão pronto e livre** para house. O caminho continua
sendo o nosso: arco de LUFS, sub e agudos a cada 2 compassos, mais `analyze_tension`.

O que dá para melhorar com repo livre é aprender esse arco das referências:
- o [all-in-one](https://github.com/mir-aidj/all-in-one) (MIT) marca as seções de cada
  referência;
- medimos o arco em cada seção (quanto o break cai, quanto o build sobe, quanto o drop
  solta);
- isso vira o alvo de pressão e alívio do estudo, como já fazemos com os níveis.

A v31 fez isso à mão: break -12,6, build -12,7 → -10,3, drop -8,6 LUFS.

---

## C. Velocidade e tokens

### 3. Saída das ferramentas: 43 % a 58 % menos texto (medido)
O servidor devolve dicionários e o FastMCP os serializa como JSON com `indent=2`
(`func_metadata.py:558`). Medido no set aberto agora:

| resposta | JSON indentado | JSON compacto | [TOON](https://github.com/toon-format/toon) |
|---|---|---|---|
| `get_song` (39 faixas) | 15.095 caracteres | 8.618 (-43 %) | 9.072 |
| `get_track` com clipes | 1.304 | 853 | **546 (-58 %)** |

- TOON: 25,6 mil estrelas, MIT, pacote Python `toon-format`. Ganha nas tabelas (clipes,
  níveis solo, arco por compasso).
- Nos dados aninhados, o JSON compacto ganha.
- Como fazer: devolver texto já serializado, compacto por padrão e TOON nas listas
  tabulares. Os benchmarks do TOON mostram acerto do modelo igual ou melhor (72,2 % contra
  71,4 % do JSON).
- Custo: uma função no server e testes.

### 4. Gêmeo da mix: decidir faders sem render
Hoje cada ajuste de nível pede um render em tempo real. A ideia, com código nosso:
1. Uma passada de taps grava cada fonte e cada bus (o `record_tracks` já existe).
2. Os movimentos de fader e o balanço contra o kick são calculados em numpy, na hora.
3. O render real fica só para confirmar o vencedor.

Limite: compressores e saturação não são lineares. Serve para movimentos pequenos
(±3 dB), que são a maioria.

### 5. Separação 2-3× mais rápida no Mac
[ssmall256/demucs-mlx](https://github.com/ssmall256/demucs-mlx) (MIT; pesos MLX MIT no HF)
e [andrade0/demucs-mlx](https://github.com/andrade0/demucs-mlx) (MIT).
- Demucs nativo em MLX: ~73× tempo real num M4 Max, 2,6× mais rápido que o PyTorch MPS,
  segundo o autor.
- Troca direta do `htdemucs` em `ear/stems.py`.
- Os RoFormer do `split_elements` continuam no PyTorch.

### 6. Render offline dentro do Live: Extensions SDK (experimento)
O Live 12.4.5+ tem um [SDK de extensões em TypeScript](https://ableton.github.io/extensions-sdk/)
(beta, Suite, modo desenvolvedor ligado) com
`context.resources.renderPreFxAudio(track, startBeat, endBeat)`. Ele devolve um WAV
**offline, sem esperar o tempo real**. O Lukas está no 12.4.6.

Limites:
- é **antes dos efeitos** da faixa;
- não renderiza grupos nem o master.

Serve para analisar as fontes (afinação, timbre, transcrição) num instante, mas não
substitui o render da mix. Vale um teste: uma extensão pequena que recebe pedidos do nosso
servidor.

### 7. Conectores para estudar (não trocar o nosso)
| Projeto | Estrelas | Licença | O que olhar |
|---|---|---|---|
| [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) | 3.258 | MIT | o mais popular, básico; nada que falte aqui |
| [adamjmurray/producer-pal](https://github.com/adamjmurray/producer-pal) | 349, ativo hoje | MIT | device Max for Live; roda com modelos locais (Ollama) e tem API REST: referência para o relay e para usuários sem Claude |
| [mikecfisher/ableton-lom-skill](https://github.com/mikecfisher/ableton-lom-skill) | 23 | sem licença | referência do Live Object Model 12.3 como skill: só leitura |
| [Ziforge/ableton-liveapi-tools](https://github.com/Ziforge/ableton-liveapi-tools) | 21 | GPL-3 | 220 comandos thread-safe; ideia apenas |

---

## D. Pensar junto e decidir mais rápido (proposta)

**Cartões de decisão.** A cada passo grande (mix, arco, drop), em vez de um render longo e
um relatório:
1. Duas ou três variantes de 8 compassos são renderizadas lado a lado, ou calculadas no
   gêmeo da mix (item 4).
2. O app mostra:
   - a nota do audiobox (item 1) e a distância até as refs;
   - o arco de pressão e alívio;
   - uma frase de por quê.
3. O usuário escolhe A ou B.
4. A escolha treina o gosto dele (item 2) e entra no `taste.md`.

Isso economiza tokens (menos relatório, mais escolha), economiza tempo (renders curtos) e
deixa o usuário decidir o sentimento.

---

## Ordem sugerida

1. **Saída compacta das ferramentas** (item 3): barato, ganho imediato de tokens em tudo.
2. **audiobox-aesthetics** como ferramenta e trava (item 1): já testado, 2 s por faixa.
3. **Gêmeo da mix** (item 4) e **cartões de decisão** (D).
4. **demucs-mlx** (item 5).
5. **Gosto calibrado pelo usuário** (item 2), quando houver votos suficientes.
6. **Arco aprendido das referências** com all-in-one (B).
7. Experimento com o Extensions SDK (item 6).

Testado hoje: item 1 (notas acima), item 3 (tamanhos medidos) e o CLAP de música (falhou).
O resto são números publicados pelos autores.
