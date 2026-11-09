# Versão 1.2.2 — uso local

Validada em 29 de outubro de 2026, neste Mac Apple Silicon.

- 371 testes locais passaram.
- App Swift compilado e assinatura ad hoc verificada.
- Serviço empacotado: protocolo desktop, instalação da ponte numa pasta temporária,
  61 ferramentas MCP, contexto dos gêneros, análise de áudio e kit de bateria passaram.
- Instalador gerado; payload extraído, assinatura e autoteste passaram. O `pkgbuild`
  emitiu avisos `write: Permission denied`, mas terminou com código zero e o payload
  resultante passou nas verificações acima.
- App instalado em `/Applications/Ableton Claude.app`, versão 1.2.2, e aberto.
- Interface confirmou Live e ferramentas conectados. Live abriu um set vazio,
  com quatro faixas a 120 BPM e saída MacBook Pro Speakers.
- Ponte atualizada com backup e recarregada sem reiniciar Live.
- Conta ChatGPT consultou os modelos disponíveis com sucesso.

## Correções de fechamento

Configurações anteriores que já usavam ChatGPT recuperam essa escolha ao atualizar.
O instalador inclui o JSON do kit `let_the_rhythm`; seu autoteste e o teste MCP agora
verificam esse recurso. Consultar o kit é reconhecido como leitura pelo produtor.
As instruções do instalador apresentam os dois assistentes e o fluxo do estúdio.

## Começar a produzir

O app encontrou uma sessão anterior e pede confirmação antes de retomá-la. Abra o
projeto correspondente no Live e clique em **O projeto correto está aberto · retomar**.
Para outra produção, use **Guardar e trocar de projeto** e escolha **Criar do zero**
ou **Continuar projeto**. Essa confirmação depende do projeto que o usuário quer
trabalhar; não foi dada automaticamente durante a validação.

Nenhum comando de produção, edição de clipes ou reprodução foi usado nesta rodada.
Falta validar a qualidade musical numa sessão real com o modelo remoto e escuta do
produtor. A consulta de modelos comprova acesso à conta, não uma produção completa.

O instalador é local, com assinatura ad hoc, sem notarização. Esta rodada validou
Apple Silicon; não gerou uma nova versão Intel.

A versão anterior do app foi preservada em
`build/macos/Ableton Claude-before-1.2.2.app`. Perfis, samples, referências e sessões
do usuário permanecem nos locais existentes.
