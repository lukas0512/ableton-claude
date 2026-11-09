# Ensaio de produção — MOTRA Launch

A trilha do anúncio foi criada em um set separado pelo chat nativo: pesquisa de presets, quatro faixas, MIDI, repetição em16 compassos e revisão do motivo. O projeto anterior e a produção concorrente foram preservados.

O ensaio revelou dois pontos para a próxima revisão do agente:

1. Um pedido com pesquisa, criação e várias aprovações atingiu o limite de120 mil caracteres de contexto. Retomar com pedidos curtos preservou o set. Investigar orçamento de contexto e retenção de resultados sem cortar pares de ferramentas/raciocínio.
2. Lotes contendo apenas get_track/get_notes pediram “Aplicar proposta”. O classificador atual reconhece leituras individuais, mas não lotes só de leitura. Além disso, a compactação de listas profundas de um lote pode omitir notas e provocar consultas repetidas. Qualquer correção precisa manter lotes mistos e comandos desconhecidos sob revisão.

Os cinco cortes finais de MIDI foram aplicados pelo MCP do mesmo aplicativo, com leitura completa antes/depois e recibos salvos em `marketing/loop-to-track/assets/motra/score-final-cuts-receipts.json`. Não se escreveu XML no arquivo ALS. A audição da etapa não foi aprovada pelo agente.

3. `Ouvir loop` iniciou reprodução, mas exibiu erro porque `transport` retornou `playing=false` antes da atualização assíncrona do Live; a leitura seguinte mostrou `is_playing=true` e o playhead avançando. O dispositivo de saída estava configurado. Corrigir com confirmação limitada de avanço do transporte antes de classificar falha; não confundir esse botão de reprodução com exportação de áudio. A trilha foi gravada pelo `render_start(1,17)` do MCP.
