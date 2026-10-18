# Versão 1 — candidata para testes

Validação realizada em 7 de outubro de 2026, em macOS Apple Silicon com Live 12.4.6.

## Melhorias desta rodada

- Revisão com faixa, posição, valores e quantidade real de notas; lotes mostram cada ação.
- O contrato do produtor pede evidência, intenção audível, suposições e verificação junto da proposta.
- Lotes do desktop executam em ordem e interrompem novas alterações ao encontrar uma falha.
- Registro independente de ações aplicadas, falhas, ações não executadas e IDs para reversão.
- O registro permanece disponível se a resposta seguinte da IA falhar.
- Aplicação confere mudanças detectáveis no resumo do projeto desde a revisão.
- Falhas de conexão durante a preparação da revisão preservam um histórico utilizável.
- Respostas vazias/inválidas da ponte geram erros recuperáveis, sem repetir comandos automaticamente.
- Instalação da ponte a partir do código fonte usa o diretório correto.
- Teste de integração usa áudio sintético local e recusa nomes de teste já existentes.
- Compilação leve de desenvolvimento e teste reproduzível de revisão/aplicação/reversão via MCP.

## Evidências

| Verificação | Resultado |
|---|---|
| Regressão local | 225 testes passaram |
| Compilação Swift nativa | Passou |
| Integração com Live | 18/18 verificações passaram |
| Revisão antes da alteração | O volume permaneceu em −8 dB até a aprovação |
| Aplicação e leitura no Live | O baixo foi ajustado para −10 dB, conforme a proposta |
| Reversão pelo diário | Volume restaurado para −8 dB |
| Serviço empacotado | Protocolo desktop, instalação temporária da ponte, 43 ferramentas MCP e análise de áudio passaram |
| Aprendizado no pacote | Referência sintética, detecção neural de batidas e Demucs passaram |
| Instalador | Pacote 1.0.0 gerado; payload extraído, assinatura ad hoc e serviço verificados |

O teste de revisão usa uma resposta de modelo **simulada** e MCP/Live reais. Não comprova
a qualidade criativa de um modelo remoto e não utiliza credenciais ou tokens de IA.
O aprendizado completo verifica uma referência sintética, não a qualidade de transcrição
de qualquer música comercial. A correção final do histórico foi incluída depois dessas
verificações do payload e do aprendizado; o pacote foi reconstruído e o serviço retestado.

## Projeto musical usado

Uma cópia separada foi salva no próprio Live como **indie dance #4 - App V1 QA.als**.
O original **indie dance #4 - Maccabi v03.als** foi preservado. As faixas de integração
foram removidas e o tempo voltou a 127 BPM. O ajuste de volume usado no teste foi revertido.

O render dos compassos 101–109 mediu:

| Medida | Resultado |
|---|---|
| Duração | 15,16 s |
| Loudness integrado | −12,5 LUFS |
| True peak | −1,83 dBTP |
| Crest | 11,4 dB |
| Energia entre 60 e 250 Hz | 68,1% |
| Correlação estéreo | 0,982 |

O perfil **Indie Maccabi**, treinado com duas referências, indicou diferença de loudness
e maior concentração de energia nos graves. O relatório completo está em
`build/v1-qa/drop-baseline.json`; o WAV permanece em `Samples/Recorded/` do projeto.
Um trecho de drop contra estatísticas de referências inteiras é um diagnóstico inicial.
Para decidir a mix, comparar seções equivalentes, ajustar a percepção de volume na escuta,
investigar kick/baixo e preservar o motivo antes de mexer no master.

## Limites para considerar a v1 aprovada

- Falta uma rodada de produção com o modelo remoto escolhido pelo usuário, incluindo escuta e refinamento do resultado.
- A qualidade profissional e a fidelidade à intenção musical precisam de aprovação auditiva; execução técnica não as demonstra.
- O resumo do Live não fornece identidade única do set, todas as notas ou todos os parâmetros; a proteção de revisão não identifica mudanças invisíveis nesse resumo.
- O instalador é local, com assinatura ad hoc; distribuição pública ainda requer assinatura Developer ID e notarização.

## Espaço recuperado

Foi removido cache reproduzível do uv: 32,7 GiB de entradas órfãs e aproximadamente
535 MiB de entradas de torch/torchaudio. A recuperação física é menor porque parte dos
arquivos compartilha blocos com ambientes instalados. Projetos, samples, referências,
perfis, modelos aprendidos e histórico das conversas foram preservados. As cópias
temporárias usadas no empacotamento/verificação também foram limpas.

## Reproduzir

```bash
cd mcp_server
.venv/bin/python -m pytest -q
.venv/bin/python ../scripts/smoke_live.py --force
.venv/bin/python ../scripts/qa_producer_live.py --copy-confirmed --track '02 BASS - Voltage'
.venv/bin/python ../scripts/smoke_desktop.py '../build/macos/product/Ableton Claude.app/Contents/Resources/backend/ableton-claude-backend' --train
```

Executar os testes que alteram Live apenas na cópia de QA. Para recriar o instalador:
`python3 scripts/build_macos.py` a partir da raiz do repositório.
