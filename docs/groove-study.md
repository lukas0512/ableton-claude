# Estudo aplicado: groove, espaço e identidade

Pesquisa consultada em 17 de outubro de 2026. Este guia separa conhecimento técnico,
hipóteses de composição e decisões confirmadas pela escuta. A data da consulta não
transforma uma fonte antiga em evidência de tendências atuais.

## Fundamentos e limites

1. **Swing, microtiming e dinâmica são controles diferentes.** O [manual de grooves do
   Live 12](https://www.ableton.com/en/live-manual/12/using-grooves/) distingue resolução,
   quantização, timing, random e velocity. A aleatoriedade pode separar ataques antes
   simultâneos. Nossa aplicação: começar com uma célula repetível, testar offsets por
   função e só introduzir aleatoriedade com uma intenção audível. Isso é uma escolha
   de projeto, não uma proibição de grooves humanos ou livres.
2. **Síncope precisa de uma pulsação perceptível.** [Witek e colaboradores, 2014](https://doi.org/10.1371/journal.pone.0094446)
   encontraram maiores avaliações de prazer e vontade de mover com síncope intermediária
   nos drum breaks estudados. O experimento não define um swing ideal, nem certifica
   qualidade em house. Hipótese prática: manter âncoras e deslocar parte dos acentos;
   comparar com a versão simples sem calcular uma suposta nota de qualidade.
3. **Arranjo pode nascer da retirada.** [Arranging as a Subtractive Process](https://makingmusic.ableton.com/arranging-as-a-subtractive-process)
   propõe desenvolver a estrutura pela remoção de material de uma combinação existente.
   Aplicação nossa: comparar as versões main/stripped antes de procurar outro sample.
4. **Surpresa ganha significado sobre repetição.** [Unique Events](https://makingmusic.ableton.com/unique-events)
   explora acontecimentos particulares dentro do arranjo. Nossa hipótese: guardar uma
   alteração reconhecível para o fim da frase, em vez de trocar todas as notas a cada volta.
5. **Seções não precisam trocar tudo juntas.** [Fuzzy Boundaries](https://makingmusic.ableton.com/fuzzy-boundaries)
   oferece caminhos para flexibilizar fronteiras. Testar uma cauda que cruza a transição
   e entradas escalonadas; não aplicar a mesma receita em todos os breaks.

## Laboratório dentro do app

Escolher um trecho de oito compassos, manter instrumentos, níveis e seed e salvar
versões comparáveis. O primeiro estudo é house/tech house em 4/4; outros estilos pedem
padrões próprios. Os valores abaixo são condições de experimento, não padrões do mercado.

| Estudo | Alterar apenas | Manter | Critério de escuta |
|---|---|---|---|
| Espaço | main versus stripped | Kick, baixo, clap, timbres | A ideia continua forte? A percussão acrescenta uma função reconhecível? |
| Swing | 50, 56 e 60%, conforme contexto | Padrão, velocity, gate, offsets | Qual relação move sem parecer arrastada? |
| Microtiming | Clap em 0, 5 e 10 ms | Swing e restantes partes | Há profundidade sem perder firmeza? |
| Articulação | Gate e depois release, separadamente | Notas, pitches e swing | O grave respira entre ataques? Há buracos indesejados? |
| Identidade | Uma pausa ou acento no fim da frase | Célula principal | A volta é reconhecível e a mudança tem propósito? |
| Timbre | Um único som substituído | MIDI e equilíbrio percebido | O som resolve a função com menos processamento? |
| Transição | Uma retirada ou cauda atravessando a borda | Seções vizinhas | A chegada cumpre a expectativa criada? |

Não mudar densidade, swing, timbre e ganho juntos durante um estudo causal. Depois de
entender cada efeito, combinar decisões numa proposta musical coerente. Ouvir o loop,
a transição e o contexto da faixa. Comparar em volume percebido semelhante; LUFS ajuda,
mas não equaliza sozinho impacto transitório nem cor sonora. Testar o grave em mono.

## Ferramenta implementada

`music_pocket_sketch(style, tonic, mode, bars, bpm, swing, seed, drum_layers,
clap_delay_ms, percussion_delay_ms)` é uma geração local sem alterações no Live.

- `main`: bateria com 3–5 vozes e baixo esparso; uma única voz de hat.
- `stripped`: mesmos baixo e âncoras, sem rim/shaker e sem ghosts do hat.
- Apoios percussivos evitam os slots do baixo e compartilham pausas; não é detector
  de mascaramento acústico. A cauda real depende do instrumento/sample.
- Kick fixo; clap com atraso explícito; hats/percussão com offset comum em milissegundos
  convertido pelo BPM. A célula mantém identidade sem jitter independente.
- `midi_diagnostics` conta notas e retiradas; não mede groove percebido.
- O swing já está escrito nas notas. Outro Groove Pool pode acumular deslocamentos.
- O baixo usa a receita esparsa de club existente também no esboço deep house; ouvir
  e adaptar à referência, sem atribuir autenticidade de estilo ao nome do preset.

No chat integrado, o material completo pode ser reutilizado sem copiar arrays:
`{"$result":"material-1","field":"main.kick"}` ou `field="stripped.bass"`.
O identificador real vem da chamada. A aplicação no Live continua passando pela revisão
existente. Conferir pads do Drum Rack, instrumentos, BPM e tonalidade antes de aplicar.

Exemplo de pedido: “Crie duas propostas de oito compassos no tom e BPM do projeto,
com quatro vozes de bateria e baixo esparso. Compare a versão enxuta primeiro;
preserve a identidade e explique qual diferença vamos escutar.”

## Como estudar o padrão atual sem inventá-lo

Selecionar 3–5 referências relevantes ao objetivo musical, incluindo lançamentos
recentes com data verificável e uma referência de identidade. Registrar artista, faixa,
versão, lançamento, fonte da data e o que interessa aprender. Não confundir data de
upload com lançamento. Uma faixa recente pode não representar o subgênero desejado.

Usar arquivos disponíveis legitimamente no fluxo existente de aprendizado do app.
Analisar trechos equivalentes (groove/drop/break), andamento e fase do grid, dinâmica,
articulação, densidade, espectro e transições. Identificar limites da separação de stems.
Comparar as medidas com a escuta, nunca copiar melodias como atalho de qualidade.
Referências sem datas conhecidas continuam úteis para som; atualidade fica desconhecida.
Não foi analisado um novo corpus de lançamentos nesta implementação.

## Registro de aprendizado por experimento

Guardar: projeto e trecho; referências/datas; hipótese; variável alterada; versões A/B;
BPM/tom/seed; instrumentos; medições; preferência ou ausência dela; motivo ouvido;
próxima decisão. Registrar “inconclusivo” quando a diferença não for convincente.
Uma preferência local não vira regra global. Promover às lições do produtor somente
observações repetidas, com condições e limites. Este guia orienta o estudo; não cria
um treinamento automático nem executa pesquisas recorrentes sozinho.
