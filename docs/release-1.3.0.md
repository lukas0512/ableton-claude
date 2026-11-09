# Versão 1.3.0 — estúdio e motion

Implementada e instalada em 30 de outubro de 2026, neste Mac Apple Silicon.

O estúdio usa grafite, texto claro e acento cítrico; sidebar e tipografia foram
reorganizadas para destacar a ação atual. O ponto de partida tem duas opções visuais:
Criar do zero e Continuar projeto. A retomada explica por que o chat aguarda confirmação.
O painel do Ableton separa Faixas de Ouvir e comparar, mantendo transporte e tempo
acessíveis mesmo em projetos longos. O ícone acompanha a nova paleta.

A geração musical, as confirmações de projeto e a revisão antes da aplicação continuam
conectadas às mesmas ações do backend. Os testes Python da rodada anterior não foram
repetidos para esta mudança de SwiftUI; a compilação nativa e a verificação visual dos
fluxos tocados foram concluídas. Live, lista de faixas, biblioteca e abas do inspector
foram conferidos sem alterar nem tocar o projeto aberto.

- Compilação Swift e assinatura passaram.
- Backend reutilizado do bundle 1.2.2 já validado; autoteste do pacote passou.
- Instalador 1.3.0 gerado, payload extraído e assinatura verificada.
- Interface instalada confirmou versão 1.3.0, Live e ferramentas conectados.
- Versão anterior preservada em build/macos/Ableton Claude-before-1.3.0.app.

O primeiro motion editável está em marketing/loop-to-track, com prévia de 30,5 s.
Usa capturas reais e trecho do render v8 do projeto aberto. A revisão descreve os limites:
é uma montagem explicativa, não uma gravação contínua de criação do zero.

Artefato: dist/Ableton-Claude-1.3.0-arm64.pkg. Build local com assinatura ad hoc;
nesta rodada não foram gerados um DMG nem uma versão Intel. A venda pública e a qualidade
musical de uma sessão completa não são demonstradas pela compilação ou por este teaser.
