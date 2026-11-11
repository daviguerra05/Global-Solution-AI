# Gravação e entrega manual

## Antes de gravar

1. Resolver o bloqueio de ambiente descrito na auditoria e executar a suíte completa. Não apresentar o registro histórico como teste atual.
2. Abrir `Iniciar_Energia_Clara.bat` e confirmar a interface e a API. Usar somente o CSV fictício.
3. Conferir nomes e RMs no relatório.

## Roteiro de gravação — ações e falas em ordem

Duração sugerida: 6 a 8 minutos, sem contar espera pelo modelo. O enunciado fornecido não fixa duração. As falas abaixo correspondem aos resultados atuais; ajuste-as se houver uma nova avaliação. Não anuncie sucesso antes de observar a resposta na tela.

### Preparação — fora da gravação

1. Concluir a validação descrita na auditoria. Se o bloqueio do Windows persistir, não apresentar a aplicação como funcionando atualmente.
2. Abrir `Iniciar_Energia_Clara.bat` e acessar `http://127.0.0.1:8501`.
3. Deixar abertos o relatório em visualização Markdown, os três notebooks com saídas e `http://127.0.0.1:8000/docs`.
4. Localizar `dados/consumo_exemplo.csv`. Em **Simular consumo**, clicar em **Restaurar casa fictícia**; em **Assistente**, limpar a conversa, se houver.
5. Fechar abas pessoais e notificações. Ajustar o zoom para que números e fontes fiquem legíveis.
6. Ensaiar a consulta ao modelo. Para a gravação, limpar a conversa novamente; não substituir uma resposta ruim por texto preparado.

### 1. Apresentar o problema — 0:00 a 0:30

**Ação:** mostrar **Visão geral**, com o nome Energia Clara e os indicadores da casa fictícia.

**Fala recomendada:**

> “Este é o Energia Clara, nosso protótipo para ajudar moradores a entender hábitos de consumo de energia. Ele reúne uma simulação de consumo e um assistente local com fontes. Os dados desta demonstração são fictícios: não usamos contas pessoais nem acesso a medidores.”

### 2. Mostrar a entrada e a simulação — 0:30 a 1:15

**Ações, nesta ordem:**

1. Abrir **Simular consumo**.
2. Selecionar `dados/consumo_exemplo.csv` e clicar em **Validar e usar arquivo**.
3. Mostrar a confirmação de oito equipamentos.
4. Na linha **Chuveiro**, alterar **Horas/dia** de `0,5` para `0,3`. Manter os demais campos e a tarifa fictícia em `0,95`.
5. Clicar em **Comparar cenário** e mostrar a diferença.

**Fala recomendada:**

> “O arquivo passa pela API, que valida os campos e os limites. Aqui temos oito equipamentos. Vou reduzir o uso diário do chuveiro de trinta para dezoito minutos, mantendo as outras hipóteses. A comparação mostra o efeito estimado dessa mudança. Esse cálculo é feito por código, com potência, tempo e quantidade, e não pela LLM. O custo mostrado é somente uma estimativa da parcela de energia, não o valor completo da conta.”

**Conferência para o ensaio:** com exatamente esses valores, o consumo passa de 229,84 para 196,84 kWh, diferença de 33 kWh e R$ 31,35. Se a tela divergir, conferir os campos; não narrar esses valores como se tivessem aparecido.

### 3. Mostrar a base e a consulta documental — 1:15 a 1:55

**Ações, nesta ordem:**

1. Abrir **Base de conhecimento** e mostrar uma nota com sua publicação de origem.
2. Abrir **Assistente** e selecionar **Orientações da base · recomendado**.
3. Enviar: “Como economizar energia com o chuveiro?”.
4. Mostrar a nota retornada e o link da fonte. Se abrir o link, voltar em seguida ao produto.

**Fala recomendada:**

> “A base contém trinta notas com referência a onze publicações. Neste modo, a aplicação busca e apresenta as notas diretamente. Isso permite conferir a orientação e sua origem. Esta consulta documental não gera uma resposta pela LLM e não foi contabilizada como resultado do treinamento.”

### 4. Demonstrar a LLM especializada — 1:55 a 2:40

**Ações, nesta ordem:**

1. Em **Forma de consulta**, escolher **LLM especializada + fontes · experimental**.
2. Enviar: “Aderir à Tarifa Branca sempre deixa a conta mais barata?”.
3. Aguardar a resposta; mostrar o texto, o tempo e as evidências disponíveis.
4. Abrir uma evidência e comparar com o que foi respondido.

**Fala durante a execução:**

> “Agora usamos o SmolLM2 com o adaptador LoRA treinado localmente. A interface envia a pergunta à API, a busca recupera contexto e o modelo gera a resposta. Esta pergunta pertence à família usada no treinamento: ela demonstra integração, mas não prova generalização.”

**Fala após observar a saída:**

> “A resposta precisa ser comparada com a evidência. A aplicação verifica o formato e as referências, mas essas verificações não garantem que o conteúdo seja verdadeiro. Por isso, o modo está identificado como experimental.”

**Se houver erro ou resposta incoerente:**

> “Nesta execução, a geração não produziu uma resposta utilizável. Esta é uma limitação real do modelo, também registrada na avaliação. Vou mostrar agora o teste completo, que permite analisar o comportamento além desta pergunta isolada.”

Não afirmar que a pergunta foi respondida corretamente se o conteúdo exibido não sustentar essa afirmação.

### 5. Explicar o pipeline e o treinamento — 2:40 a 3:25

**Ações, nesta ordem:**

1. Abrir `RELATORIO.md` na seção **Arquitetura e pipeline dos documentos** e mostrar o diagrama.
2. Abrir `notebooks/02_treinamento_local.ipynb` e mostrar as saídas do histórico e da validação.
3. Apontar a existência de `modelos/adaptador/adapter_model.safetensors`.

**Fala recomendada:**

> “As fontes são organizadas em notas, transformadas em vetores e recuperadas pela busca. No experimento, comparamos o mesmo modelo sem contexto, com RAG simples e com RAG mais LoRA. O treinamento foi executado em CPU, com conjuntos separados de treino, validação e teste. O adaptador e o histórico estão salvos. A perda de validação acompanha o treinamento, mas sua redução, sozinha, não prova melhora factual.”

### 6. Apresentar as métricas sem exagerar o resultado — 3:25 a 4:25

**Ações, nesta ordem:**

1. Abrir **Resultados** e mostrar o placar revisado. Usar a tabela do relatório se precisar de melhor legibilidade.
2. Apontar as três linhas: sem contexto, RAG simples e RAG + LoRA.
3. Mostrar no relatório os valores de recall e a justificativa do limiar.

**Fala recomendada:**

> “O teste tem sessenta perguntas: quarenta respondíveis e vinte cuja resposta não consta na base. Na revisão semântica assistida por IA, o acerto total foi zero por cento sem contexto, quarenta e seis vírgula sessenta e sete por cento com RAG e vinte por cento com LoRA mais RAG. Nas quarenta perguntas respondíveis, o RAG acertou vinte e o LoRA apenas uma. Portanto, a melhora do LoRA sobre o modelo sem contexto veio principalmente das recusas corretas; ele não superou o RAG em conteúdo factual.”

> “A busca teve recall de noventa por cento no primeiro resultado e cem por cento nos três primeiros, nas perguntas respondíveis do teste. O limiar de zero vírgula oitenta e cinco foi escolhido na validação, equilibrando recuperação e rejeição. Recuperar o trecho correto não garante que a LLM o utilize corretamente.”

### 7. Mostrar os cinco erros reais — 4:25 a 5:30

**Ação:** abrir **Cinco erros reais, causas prováveis e correções** em `RELATORIO.md`. Percorrer os cinco exemplos na ordem abaixo, mostrando pergunta, saída real e proposta. Dedicar mais tempo aos dois primeiros.

| Ordem | Ação na tela | Fala recomendada |
| --- | --- | --- |
| 1 | Destacar a troca de minutos por horas no erro de conversão. | “O modelo diz dividir horas por sessenta, quando deveria dividir minutos. O corretor por palavras-chave marcou isso como acerto; a revisão semântica identificou o erro.” |
| 2 | Mostrar a confusão entre potência e energia e a fonte citada. | “Aqui o modelo confunde potência com consumo em kWh, mesmo tendo recebido o trecho correto. Uma referência existente não garante suporte à afirmação.” |
| 3 | Mostrar o JSON que diz `respondido` com texto ‘Não consta’. | “Neste caso, o texto recusa, mas o status e a fonte são contraditórios. A proposta é verificar também a consistência entre esses campos.” |
| 4 | Mostrar o RAG repetindo a pergunta sobre o Inmetro. | “Aqui o modelo repete a pergunta e não entrega o JSON. A proposta é testar extração e geração restrita, medindo conteúdo e formato separadamente.” |
| 5 | Mostrar a pergunta sobre a tarifa da casa. | “A busca encontra assuntos relacionados, mas não a tarifa pessoal. O modelo deveria reconhecer essa ausência. A proposta é ampliar exemplos difíceis de recusa na validação.” |

**Fala de transição:**

> “Essas são propostas de correção, não melhorias já comprovadas. Um próximo ciclo deve usar uma avaliação independente, sem ajustar o modelo pelas respostas deste teste.”

### 8. Mostrar a integração e os arquivos de entrega — 5:30 a 6:10

**Ações, nesta ordem:**

1. Na documentação da API, mostrar `POST /ingerir-consumo`, `POST /simular`, `POST /perguntar` e `POST /consultar-base`.
2. Mostrar as pastas `notebooks`, `base` e `avaliacao`, além do `README.md`.
3. Abrir brevemente `notebooks/03_avaliacao_e_integracao.ipynb` e mostrar as saídas de integração. Identificar como históricas caso não tenham sido reexecutadas.

**Fala recomendada:**

> “A interface usa esta API local para ingestão, simulação e consultas. O repositório inclui os notebooks com saídas, a base com fontes, o conjunto de teste, os placares e as instruções de reprodução. As perguntas não são gravadas pela API e a inferência usa modelos locais. Essas medidas reduzem a exposição de dados, mas não representam certificação de conformidade ou uma implantação pronta para produção.”

### 9. Concluir com o que foi comprovado — 6:10 a 6:40

**Ação:** voltar ao placar revisado ou à conclusão técnica do relatório.

**Fala recomendada:**

> “Concluímos o treinamento local e a integração ao protótipo. A solução com contexto apresentou mais acertos que o modelo sem contexto, mas a especialização LoRA não superou o RAG simples em fatos. Também não tratamos o indicador automático como prova definitiva de menor alucinação. O próximo passo é melhorar a fidelidade às fontes e medir afirmações sem suporte em um novo teste. Por isso, o produto prioriza a consulta documental e mantém a geração como experimental.”

Encerrar a gravação depois de manter a tela final visível por alguns segundos.

## Publicação e envio

1. Assistir ao vídeo completo e conferir áudio, legibilidade, correspondência entre falas e resultados e ausência de dados pessoais.
2. Disponibilizar o vídeo e conferir a permissão de acesso.
3. Publicar o conteúdo de `Projeto_IA` como raiz do repositório público. Preservar `.gitignore` e `.gitattributes`.
4. Incluir adaptador, notebooks com saídas, relatório, base, teste, placares, código e documentação. Não incluir `.venv`, `runtime`, aulas, documentos originais baixados ou pesos completos dos modelos.
5. Confirmar no GitHub que as saídas dos notebooks aparecem e que o relatório e as fontes abrem.
6. Acrescentar os links reais do repositório e do vídeo em `RELATORIO.md` e `README.md`, depois da última geração automática dos documentos.
7. Enviar o link do repositório no Teams da disciplina até **19/11 às 23h55**, conforme o enunciado. Conferir a permissão de visualização do vídeo.

Nenhuma publicação, gravação ou submissão foi feita automaticamente.
