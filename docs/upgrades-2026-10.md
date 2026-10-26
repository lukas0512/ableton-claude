# O que muda para quem usa o Ableton Claude (outubro de 2026)

Tudo aqui é gratuito e roda no Mac do usuário. Os modelos novos baixam sozinhos na
primeira vez que são usados (de 0,1 a 0,9 GB cada) e ficam em
`~/Music/Ableton Claude/Models/`.

## 1. "Abre esse sample em canais": cada elemento no seu canal

Peça em palavras simples: "separa esse loop em canais", "isola o vocal dessa faixa",
"abre o PERC LOOP". A IA usa a nova ferramenta `split_elements` e:

- separa o áudio em **bumbo, caixa, toms, chimbal, ride, prato, baixo, música
  (harmonia/instrumentos), voz principal e backing vocal**;
- com "separa também o reverb da voz", divide a voz em **voz seca** e **reverb** (cada um
  no seu fader: dá para tirar o reverb de um acapella ou deixá-lo mais molhado);
- cria uma faixa por elemento logo abaixo da original, com os clipes nas mesmas posições
  e com o mesmo warp, e silencia a original. **Tudo volta atrás** com "desfaz isso"
  (revert_changes);
- diz **o que tem em cada pedaço** do vocal ao longo do tempo: rap ou fala, canto,
  scratch, plateia, efeitos. Assim a IA corta o scratch, o grito ou o hook para canais
  separados em vez de tratar o stem de voz como uma coisa só.

Qualidade (números publicados pelos autores dos modelos, SDR em dB, maior = mais limpo):
voz 12,6 (antes 8,4), bumbo 16,7, caixa 11,5, toms 12,3. O **chimbal separa mal (4 dB)**:
a IA avisa para ouvir antes de usar.

Tempo medido num MacBook Apple Silicon: a música "Murder" inteira (5 min) abriu em
~6 minutos; um loop de 8 s abre em ~10 s; colocar 3 canais com 47 clipes cada no set
levou ~1 minuto. A IA avisa antes de começar e não roda durante um render.

## 2. Medir o volume de todos os elementos numa passada só (modo rápido)

A regra da mix é: o bumbo é o mais alto e tudo se guia por ele. A medição antiga toca
cada elemento sozinho pelo master, uma vez por elemento (5 elementos em 8 compassos:
107 s). O modo rápido novo (`one_pass`) grava **todas as faixas ao mesmo tempo**:
10 elementos em 34 s.

Limite medido no Murder Pista: o modo rápido mede no fader de cada faixa, antes dos
buses. Quando a faixa passa por um bus (DRUMS, LOW END...), o número muda bastante (o
chimbal leu 9 LU mais baixo que no modo antigo). Por isso o modo antigo continua sendo o
padrão para acertar faders; o rápido serve de panorama e avisa quais faixas passam por
bus.

## 3. Palavras de leigo viram ajustes medidos

Quem não é técnico diz "tá abafado", "o vocal sumiu", "tá sem peso", "tá molhado".
A IA agora tem uma tabela de tradução: para cada palavra, **o que medir** (qual banda,
qual elemento) e **o menor ajuste** no elemento culpado (nunca um boost no master para
o problema de um elemento), seguido de um render dos mesmos compassos para conferir.
A ideia vem de um estudo da Sony (LLM2Fx): a IA acerta muito mais os parâmetros quando
vê as medidas do áudio, e não só a palavra.

## 4. A IA aprende o gosto de cada usuário

Cada mudança que o usuário desfaz ("desfaz isso") fica registrada. A nova ferramenta
`taste_report` conta, por tipo de movimento (volume, EQ nos agudos, compressor, notas...),
quanto o usuário manteve e quanto desfez. A IA consulta isso no começo e evita repetir o
que a pessoa sempre desfaz, ou pergunta antes. O aprendizado começa a partir desta
versão (desfazer pelo Cmd+Z do Live não entra na conta).

## Testado nas faixas do Lukas (26/10/2026)

- **Murder (original, UGK)**: aberto em bumbo, caixa, chimbal, prato, baixo, música, voz
  seca, reverb da voz e backing. O reverb da voz está 25 dB abaixo da voz seca (é um
  vocal seco); o stem de música tem guitarra e um **scratch aos 0:08**. Arquivos em
  `Desktop/TRACKS 2027/Murder/Murder original - elements/`.
- **Murder Pista** (numa cópia: `Murder pista - teste upgrades.als`): o PERC LOOP (loop de
  pack, 47 clipes) virou 3 canais, SNARE, TOMS e HATS, com a origem silenciada. Um vocal
  de hook foi aberto em voz/backing e desfeito com revert_changes: tudo voltou.
- Níveis do DROP 1 contra o bumbo (modo antigo, pelos buses): clap -7,6, chimbal -11,3,
  vocal do hook -13,3, riff -8,9 LU.

## O que ficou para depois e por quê

- **Busca de samples por descrição do som** ("um bumbo seco tipo 909"), com o modelo
  CLAP: precisa indexar a biblioteca inteira do usuário com um modelo novo. É a próxima
  etapa.
- **Separar qualquer som descrito em texto** (SAM Audio da Meta): os pesos têm acesso
  controlado e licença própria, que precisa ser lida antes.
- **Ajustar EQ/compressor por stem contra a referência fora do Live** (ideia do ST-ITO):
  é um projeto maior, depende da separação que entrou agora.
- **Master casada com a referência**: o código pronto (matchering) é GPL; vamos
  reimplementar a ideia.
- **Mac Intel**: a separação nova precisa de PyTorch 2.13+, que não existe para Intel.
  No Intel, `split_elements` não está disponível; o resto funciona.
