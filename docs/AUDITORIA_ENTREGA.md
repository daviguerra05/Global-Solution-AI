# Auditoria pragmática — 09/11/2026

## Parecer

Os artefatos acadêmicos estão presentes, mas a entrega ainda tem uma pendência de funcionamento neste computador. A suíte completa não inicia porque o Controle de Aplicativo do Windows bloqueia a biblioteca nativa `pydantic_core`. A reinstalação da mesma versão oficial (2.50.4) não resolveu. Não foi desativada nenhuma proteção do sistema.

O resultado científico é limitado: C supera A no acerto total revisado (20% contra 0%), porém só acerta 1 de 40 perguntas respondíveis; B acerta 20 de 40. Não há demonstração robusta de redução de alucinações semânticas nem qualidade para uso livre. O treinamento real e a comparação existem; não se deve declarar que todos os objetivos de qualidade foram atingidos. Nova melhoria exige outro ciclo de treino/validação e teste independente, sem ajustar pelo teste já examinado.

## Conferência dos critérios

| Critério do enunciado | Evidência e parecer |
| --- | --- |
| Tarefa e teste com gabarito e “não consta” | `avaliacao/teste.jsonl`: 60 perguntas, 40 respondíveis e 20 sem resposta; partições factuais separadas. Atendido. |
| Base em trechos com fonte | `base/trechos.jsonl`, `fontes.json`, `fontes.csv`, `LICENCA.md`: 30 notas de 11 fontes. Atendido. |
| Recall@1, recall@3 e limiar | `avaliacao/calibracao.json` e placar: limiar escolhido na validação; recall de teste reportado separadamente. Atendido. |
| JSON, citação e recusa | API valida estrutura e IDs; avaliação registra falhas reais. Atendimento parcial em qualidade: o modelo ainda produz erros factuais e contradições. |
| Especialização comparada ao RAG | Adaptador LoRA, histórico, proveniência e saídas A/B/C. Atendido como experimento, sem superioridade factual sobre B. |
| Placar e interpretação | Placar automático preservado e revisão semântica assistida separada. Atendido, com limites explícitos. |
| Cinco erros, causa e correção | Cinco casos distintos no relatório e JSON, ligados às saídas originais e à revisão. Atendido. |
| README e reprodução | Instalação, modelos fixados, conferência sem treino e fluxo de novo experimento documentados. Execução atual bloqueada pelo ambiente. |
| Equipe, ficha, diagrama e tabela da base | Presentes em `RELATORIO.md`. Atendido. |
| Notebooks com saídas | Três notebooks da execução original preservados. Saídas históricas, não uma nova execução nesta auditoria. A seleção de erros foi ampliada no relatório; a saída histórica do notebook 03 mostra a seleção anterior. |
| API e integração | Código, testes e demonstração histórica presentes. Revalidação atual pendente. |
| Segurança, explicabilidade e LGPD | Inferência local, fontes visíveis, dados sintéticos e ausência de persistência de perguntas documentadas; não é certificação jurídica ou ambiente de produção. |
| Repositório público e vídeo | Pendências manuais do aluno, conforme combinado; roteiro em `ENTREGA_MANUAL.md`. |

## Correções desta revisão

- Limite da API passa a conferir bytes recebidos, inclusive sem cabeçalho de tamanho confiável; inicialização do assistente protegida contra concorrência.
- Busca com corpus/calibração incompatíveis devolve erro orientativo, em vez de falha interna não tratada.
- Cinco erros editoriais usam a revisão semântica, incluindo falsos acertos do corretor automático; geração do relatório rejeita resultados de outra execução antes de sobrescrever os casos.
- Treinamento direto não sobrescreve um adaptador existente; a documentação separa conferir a entrega de executar um novo experimento e exige nova revisão semântica.
- Verificador confere IDs únicos e cobertura das anotações e não declara aprovação funcional se os testes falham.

## Validação realizada

- **3 testes de protocolo aprovados**, registrados em `avaliacao/testes_protocolo.xml`.
- Compilação dos módulos Python aprovada.
- Integridade dos artefatos conferida com `scripts.verificar_entrega --somente-artefatos`; essa opção não aprova funcionamento.
- Suíte completa interrompida em três erros de importação, registrados em `avaliacao/testes.xml`. As duas novas verificações da API ainda não puderam executar.
- Pesos, conjuntos de dados, prompts e as 180 respostas brutas do experimento original não foram alterados.

## Pendência antes de gravar

Permitir a instalação/execução das dependências oficiais pelo procedimento autorizado do Windows ou usar um computador onde elas sejam permitidas. Reinstalar repetidamente não resolveu neste ambiente. Depois executar, a partir de `Projeto_IA`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=avaliacao/testes.xml
.\.venv\Scripts\python.exe -m scripts.servicos iniciar
.\.venv\Scripts\python.exe -m scripts.gerar_notebooks --executar
.\.venv\Scripts\python.exe -m scripts.verificar_entrega
```

Somente após sucesso dessas etapas atualizar este parecer de funcionamento. A publicação, gravação e inclusão dos links continuam manuais.
