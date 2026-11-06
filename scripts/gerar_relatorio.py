"""Gera tabelas, gráficos e documentação exclusivamente a partir dos resultados reais."""
import csv
import json
from pathlib import Path
from energia_clara.config import ROOT,read_json,read_jsonl,write_json

LABELS={"sem_contexto":"A — Sem contexto","rag":"B — RAG simples","lora_rag":"C — RAG + LoRA"}
TEAM=[("Davi Passanha de Sousa Guerra","RM551605"),("Cauã Gonçalves de Jesus","RM97648"),
      ("Luan Silveira Macea","RM98290"),("Rui Amorim Siqueira","RM98436"),("Luigi Ferrara Sinno","RM98047")]


def table(headers,rows):
    def cell(v): return "—" if v is None else str(v).replace("|","/").replace("\n"," ")
    return "\n".join(["| "+" | ".join(headers)+" |","| "+" | ".join(["---"]*len(headers))+" |"]+
                      ["| "+" | ".join(cell(x) for x in row)+" |" for row in rows])


def diagnose(row):
    if row["origem"]=="limiar_busca":
        return ("Recusa indevida pela busca","O melhor resultado ficou abaixo do limiar escolhido na validação.","Acrescentar consultas positivas difíceis à validação e comparar limiar com margem entre resultados; medir em novo teste independente.")
    if not row["json_modelo_valido"]:
        return ("Saída fora do contrato JSON","A geração livre não manteve o esquema esperado; a API devolveu erro verificável.","Testar decodificação restrita por esquema e medir sua contribuição separadamente do LoRA; preservar a taxa bruta de falhas de formato.")
    if row["erro_verificacao"]:
        return ("Citação não verificável","O texto gerado citou uma referência ausente ou não respeitou o contrato de fontes.","Ampliar exemplos de cópia de identificadores a partir do contexto e manter a verificação de fontes; testar identificadores inéditos.")
    if row["tipo"]=="nao_consta":
        return ("Resposta sem informação disponível","A pergunta exige informação ausente da base, mas o modelo tentou responder.","Ampliar negativos difíceis e testar se o retriever rejeita perguntas semelhantes a temas válidos, sem usar o teste atual para calibrar.")
    if row["recusou"]:
        return ("Recusa indevida do modelo","Há uma referência de resposta na base, mas a geração optou por recusar.","Treinar distinção entre contexto útil e insuficiente, com diversidade de perguntas e fontes na validação.")
    if not row["correto_conteudo"]:
        return ("Conteúdo divergente do gabarito","O modelo não preservou os fatos exigidos ou acrescentou número sem sustentação.","Inspecionar cobertura e posição do trecho correto e ampliar exemplos de extração fundamentada; revisar também possíveis falsos negativos do corretor.")
    return ("Fundamentação incompleta","O conteúdo atende ao gabarito, mas a resposta não citou a referência necessária.","Validar a relação entre afirmação e trecho citado, além da existência do identificador.")


def main():
    score=read_json(ROOT/"avaliacao"/"placar.json")
    if not score: raise SystemExit("Execute o experimento antes de gerar o relatório.")
    history=read_json(ROOT/"avaliacao"/"historico_treino.json")
    environment=read_json(ROOT/"avaliacao"/"ambiente.json")
    calibration=read_json(ROOT/"avaliacao"/"calibracao.json")
    manifest=read_json(ROOT/"avaliacao"/"manifesto_dados.json")
    sources=read_json(ROOT/"base"/"fontes.json")
    chunks=read_jsonl(ROOT/"base"/"trechos.jsonl")
    rows={m:read_jsonl(ROOT/"avaliacao"/f"resultados_{m}.jsonl") for m in LABELS}
    flat=[r for items in rows.values() for r in items]
    cases=[]; seen=set()
    selectors=[
        lambda r:r["configuracao"]=="lora_rag" and not r["acerto_completo"],
        lambda r:r["configuracao"]=="sem_contexto" and r["tipo"]=="nao_consta" and not r["correto_conteudo"],
        lambda r:r["configuracao"]=="rag" and r["tipo"]!="nao_consta" and not r["correto_conteudo"],
        lambda r:r["origem"]=="limiar_busca" and r["tipo"]!="nao_consta",
        lambda r:r["configuracao"]=="lora_rag" and bool(r["erro_verificacao"]),
    ]
    for select in selectors:
        item=next((r for r in flat if select(r) and (r["configuracao"],r["id"]) not in seen),None)
        if item:
            kind,cause,fix=diagnose(item)
            cases.append({**item,"categoria":kind,"causa_provavel":cause,"correcao_proposta":fix})
            seen.add((item["configuracao"],item["id"]))
    for item in flat:
        if len(cases)>=5: break
        if item["acerto_completo"] or (item["configuracao"],item["id"]) in seen: continue
        kind,cause,fix=diagnose(item)
        cases.append({**item,"categoria":kind,"causa_provavel":cause,"correcao_proposta":fix})
        seen.add((item["configuracao"],item["id"]))
    if len(cases)<5: raise RuntimeError("Há menos de cinco erros reais; não fabricar exemplos.")
    write_json(ROOT/"avaliacao"/"cinco_erros.json",cases)
    with (ROOT/"avaliacao"/"placar.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(score[0])); writer.writeheader(); writer.writerows(score)
    metrics=[("acerto_conteudo_pct","Acerto de conteúdo · %"),("acerto_completo_pct","Acerto completo · %"),
             ("acerto_respondiveis_pct","Acerto nas respondíveis · %"),("alucinacao_operacional_pct","Erro factual ao responder · %"),
             ("recusa_correta_pct","Recusa correta · %"),("recusa_indevida_pct","Recusa indevida · %"),
             ("json_modelo_valido_pct","JSON bruto conforme contrato · %"),("citacao_valida_respondiveis_pct","Citação válida nas respondíveis · %"),
             ("recall_1","Recall@1 com limiar"),("recall_3","Recall@3 com limiar"),
             ("recall_1_sem_limiar","Recall@1 sem limiar"),("recall_3_sem_limiar","Recall@3 sem limiar"),
             ("chamadas_modelo","Chamadas à LLM"),("latencia_media_s","Latência média · s"),("latencia_p95_s","Latência p95 · s")]
    score_table=table(["Métrica"]+[LABELS[r["configuracao"]] for r in score],[[name]+[r[key] for r in score] for key,name in metrics])
    short_table=table(["Configuração","Acerto de conteúdo","Acerto completo","Erro factual ao responder"],
                      [[LABELS[r["configuracao"]],str(r["acerto_conteudo_pct"])+"%",str(r["acerto_completo_pct"])+"%",str(r["alucinacao_operacional_pct"])+"%"] for r in score])
    epoch_table=table(["Época","Loss de treino","Loss de validação"],[[r["epoca"],round(r["loss_treino"],4),round(r["loss_validacao"],4)] for r in history["epocas"]])
    source_table=table(["Fonte","Instituição","Formato","Notas","Licença do original"],
        [["["+s["titulo"]+"]("+s["url"]+")",s["entidade"],s["formato"],sum(c["fonte_id"]==s["id"] for c in chunks),s["licenca_original"]] for s in sources])
    team_table=table(["Integrante","RM"],TEAM)
    review=read_json(ROOT/"avaliacao"/"placar_revisado.json")
    if not review: raise SystemExit("Registre a revisão semântica antes de fechar o relatório.")
    import hashlib
    if any(r["saida_sha256"]!=hashlib.sha256((ROOT/"avaliacao"/f"resultados_{r['configuracao']}.jsonl").read_bytes()).hexdigest() for r in review):
        raise SystemExit("As saídas mudaram. Refaça a revisão semântica.")
    review_table=table(["Configuração","Fatos corretos / 40","Recusas corretas / 20","Acerto total revisado","Acerto completo revisado"],
        [[LABELS[r["configuracao"]],r["acertos_fatuais"],r["recusas_corretas"],str(r["acerto_total_revisado_pct"])+"%",str(r["acerto_completo_revisado_pct"])+"%"] for r in review])
    semantic_conclusion=("A revisão não confirmou o ganho factual sugerido pelo corretor automático. O RAG simples preservou mais fatos essenciais do que LoRA, mas falhou no contrato JSON. "
        "LoRA melhorou o formato e parte das recusas, ao custo de conteúdo incoerente em fatos não usados no treino. O treinamento e a comparação foram realizados; "
        "a especialização não atingiu qualidade factual adequada para uso livre. Por isso, o MVP recomenda consulta documental direta, que apresenta as notas e fontes sem paráfrase da LLM. "
        "Os três modos de geração continuam disponíveis como experimento. Essa decisão de produto é posterior à avaliação e não foi contabilizada como desempenho da LLM.")
    conclusions="Os resultados de conteúdo do corretor automático inicial são preservados somente para auditoria. A interpretação factual usa a revisão semântica e deve respeitar seus limites."
    case_text=[]
    for i,r in enumerate(cases,1):
        original=r["saida_bruta"] if r["modelo_chamado"] else json.dumps(r["resposta_pipeline"],ensure_ascii=False)
        case_text.append(f"### Erro {i} — {r['categoria']}\n\n**Registro:** `{r['id']}` · {LABELS[r['configuracao']]} · origem `{r['origem']}`.\n\n"
                         f"**Pergunta:** {r['pergunta']}\n\n**Esperado:** {r['resposta_esperada']}\n\n**Saída real:**\n\n````text\n{original}\n````\n\n"
                         f"**Causa provável:** {r['causa_provavel']}\n\n**Correção proposta:** {r['correcao_proposta']}\n\n"
                         f"**Trechos recuperados:** {', '.join(x['id'] for x in r['trechos']) or 'nenhum'}. O registro completo está em `avaliacao/cinco_erros.json`.\n")
    report='''# Energia Clara — Relatório técnico da atividade de IA

Assistente de uso consciente de energia residencial com LLM local, RAG, especialização LoRA e integração em um MVP Streamlit. O treinamento e as avaliações foram executados neste computador, em CPU. O relatório usa os artefatos reais da execução, sem números ilustrativos apresentados como medições.

## Integrantes

@@EQUIPE@@

## Problema e ficha técnica

Moradores precisam entender hábitos de consumo e interpretar orientações de eficiência sem receber tarifas ou promessas de economia inventadas. O Energia Clara permite simular aparelhos fictícios e consultar recomendações com fontes. Seu recorte é residencial, com orientações gerais para o Brasil. Não se conecta a medidores, faturas pessoais ou concessionárias.

| Campo | Implementação |
| --- | --- |
| Tarefa da IA | Resposta curta a perguntas sobre energia residencial, com fonte e recusa quando faltar informação |
| Modelo gerador | HuggingFaceTB/SmolLM2-135M-Instruct, mesma revisão em A, B e C |
| Especialização | LoRA supervisionado na resposta, com exemplos de contexto suficiente e insuficiente |
| Busca | intfloat/multilingual-e5-small; produto interno exato de vetores normalizados; top-3 |
| Base | 30 notas autorais fundamentadas em 11 páginas públicas; identificador e seção por nota |
| Entrada do MVP | CSV sintético, editor de equipamentos e perguntas de texto |
| Saída | Consumo estimado por código e resposta da IA em JSON com status, resposta e fontes |
| Integração | Streamlit → API FastAPI por HTTP local; a interface não chama a LLM diretamente |
| Execução | CPU neste computador; modelos obtidos previamente e inferência local |
| Limites | Sem tarifas ao vivo, diagnósticos elétricos, medição real ou promessa de desconto |

O cálculo de consumo é determinístico: potência × horas × dias × quantidade × fator de uso ÷ 1000. A LLM não faz essa conta. A tarifa é fictícia ou informada pelo usuário e o resultado exclui os demais componentes da fatura. O fator de uso é uma hipótese editável; não equivale a uma medição ou valor certificado do equipamento.

## Arquitetura e pipeline dos documentos

```mermaid
flowchart LR
    S[Fontes públicas] --> C[Curadoria factual e notas com fonte]
    C --> E[Encoder E5 multilíngue]
    E --> I[Índice vetorial local]
    P[Pergunta] --> B[Busca top-3]
    I --> B
    B --> L{Score passa no limiar?}
    L -->|Não| N[Não consta pela busca]
    L -->|Sim| M[SmolLM2 original ou com LoRA]
    L -->|Sim, consulta documental| O[Exibição literal das notas e fontes]
    M --> V[Validação de JSON e referências]
    V --> API[API local]
    N --> API
    O --> API
    API --> UI[Streamlit]
    CSV[CSV fictício] --> D[Validação e cálculo determinístico]
    D --> API
    T[Treino supervisionado separado] --> A[Adaptador LoRA]
    A --> M
```

A configuração A recebe a pergunta e o contrato de resposta, sem documentos. B recebe os trechos filtrados, com o modelo original. C recebe os mesmos trechos de B e o modelo com o adaptador recarregado. Geração gulosa, mesmo orçamento de saída e mesma revisão do modelo. A não é obrigada a citar documentos que não recebeu.

Os trechos são notas curadas, não páginas inteiras cortadas automaticamente. Cada unidade mantém título, fonte, URL, seção, data e grupo factual. O tamanho foi conferido com o tokenizador do encoder, respeitando seu limite de 512 tokens. O manifesto do índice registra o hash do corpus; mudança na base exige reindexação e nova calibração.

## Base de conhecimento e licenças

@@FONTES@@

As notas são sínteses autorais de fatos e recomendações. Os documentos originais não são publicados neste repositório. O uso de informações públicas não significa que todo texto original tenha licença aberta: o inventário distingue os casos. Os links CC BY-ND foram verificados nos portais governamentais. Veja `base/LICENCA.md`, `base/fontes.csv` e `base/auditoria_download.json`.

## Dados e prevenção de vazamento

| Conjunto | Quantidade | Uso |
| --- | --- | --- |
| Treino | 200: 140 respondíveis + 60 recusas | Ajuste dos pesos LoRA |
| Validação | 20: 12 respondíveis + 8 sem resposta | Limiar, acompanhamento e seleção do checkpoint |
| Teste | 60: 40 respondíveis + 20 sem resposta | Comparação final A/B/C |

As 40 perguntas respondíveis do teste são quatro formulações de **10 fatos**, portanto são correlacionadas. Elas não representam 40 unidades factuais independentes. Perguntas e grupos de fatos são disjuntos entre as partições. Os dados de treino não contêm as perguntas de teste. Os contextos de treinamento usam fatos do conjunto de treino; o RAG pode consultar toda a base no teste, como uma consulta documental deve permitir.

Os testes foram preparados antes do treinamento. O manifesto e o hash identificam o conjunto congelado. Não houve ajuste dos hiperparâmetros ou do limiar a partir das saídas de teste. As falhas selecionadas no relatório são diagnósticos posteriores, não exemplos adicionados ao treino da avaliação publicada.

Hash SHA-256 do teste: `@@HASH_TESTE@@`.

## Recuperação e limiar

O limiar foi escolhido **somente na validação**, maximizando a média de recall@3 nas perguntas respondíveis e rejeição das perguntas sem resposta. Em empate, priorizou-se recall, rejeição e depois menor limiar. O limiar não é uma probabilidade de acerto e não deve ser transportado automaticamente a outra base ou encoder.

@@CALIBRACAO@@

Recall@k é a média, nas perguntas respondíveis, da fração de referências relevantes recuperadas nos primeiros k resultados. Como há uma referência por pergunta, equivale a encontrar essa referência no top-k. Perguntas sem resposta são avaliadas por rejeição/recusa, sem atribuir recall artificial. A tabela de desempenho mostra recall antes e depois do limiar.

## Treinamento real em CPU

@@TREINO@@

@@EPOCAS@@

A perda é calculada somente sobre os tokens da resposta e o token de encerramento. Prompt e padding têm label -100. A máscara foi verificada antes do treino. AdamW atualiza apenas os parâmetros LoRA; os pesos originais ficam congelados. A perda de validação é ponderada pelos tokens supervisionados. O melhor checkpoint treinado é salvo e recarregado antes de avaliar C. Parada antecipada: duas épocas sem melhora.

O piloto executou três lotes e foi descartado: seus pesos não foram usados no treinamento final. A redução da perda de treino não é apresentada como prova de melhoria factual; as avaliações de geração são separadas.

Na execução inicial, o PEFT tentou uma consulta opcional ao Hub ao salvar o adaptador; a consulta foi bloqueada e o salvamento local prosseguiu. A versão distribuída desativa essa consulta (`save_embedding_layers=False`, pois embeddings não são treinados) e usa modo offline por padrão. Os textos exatos do protocolo executado foram preservados em `avaliacao/protocolo_executado/`, com hashes no ambiente. Essa correção de salvamento não altera a matemática do treinamento nem as saídas avaliadas.

## Desempenho nas três configurações

### Revisão semântica assistida das saídas

@@REVISAO@@

Esta revisão assistida por IA foi feita após a execução; não é avaliação humana independente. Foram considerados o fato essencial, a operação/unidade e a adequação à pergunta. Eco da pergunta e mistura incoerente não receberam crédito. Há uma decisão por saída, assinaturas dos arquivos e justificativas em `avaliacao/revisao_semantica.json`. Dados, respostas, pesos e prompts não foram alterados.

O corretor automático produziu falsos positivos e negativos: creditou ecos com palavras da pergunta e confundiu conceitos com as palavras certas; também rejeitou conteúdo correto do RAG por números em referências inventadas. Em T-E002-4, LoRA dizia dividir horas por 60, não minutos. A presença de “dividir” e “60” não é prova de acerto. A revisão não pode ser reutilizada automaticamente em uma nova execução.

### Placar automático original, preservado para auditoria

@@PLACAR@@

**Critérios e denominadores:**

- Acerto de conteúdo: grupos de expressões do gabarito, recusa e verificação de números. É um corretor operacional, não uma prova geral de equivalência semântica.
- Erro factual ao responder (`alucinacao_operacional_pct`): tentativa de resposta que não atende ao gabarito ou responde a algo que não consta. É um **indicador operacional**, sujeito a falsos positivos/negativos; não é uma auditoria semântica exaustiva de alucinações.
- Acerto completo: conteúdo correto, contrato aceito e, quando aplicável, referência de suporte do gabarito. Um erro de formato não é automaticamente um erro factual, mas pode impedir a resposta utilizável do produto.
- Recusa correta usa as 20 perguntas sem resposta; recusa indevida usa as 40 respondíveis. Isso evita premiar um sistema que recusa tudo.
- JSON bruto conforme contrato usa apenas chamadas efetivamente feitas à LLM. A recusa por limiar é código e não conta como JSON gerado pelo modelo.
- A API sempre serializa sua resposta como JSON e pode emitir status `erro`. Essa garantia técnica não é atribuída ao treinamento nem contada como acerto de conteúdo.
- Citação válida verifica IDs e contexto recuperado. A sustentação pelo gabarito é medida separadamente. A API não executa um verificador semântico completo de cada afirmação.
- Latências são as observadas neste equipamento e protocolo, não um benchmark geral de capacidade de atendimento. A primeira consulta pode envolver carga adicional de recursos.

As saídas brutas, decisões do limiar, validações da API, referências e tempos por pergunta estão nos três arquivos `avaliacao/resultados_*.jsonl`. O protocolo confirma que os contextos de B e C foram idênticos. Gráficos completos: [comparação](relatorio/graficos/placar.html) e [aprendizado](relatorio/graficos/aprendizado.html), ambos independentes de CDN.

## Interpretação dos resultados

@@CONCLUSAO_SEMANTICA@@

@@CONCLUSAO@@

O tamanho reduzido do modelo e seu foco original em inglês limitam o uso em português. O dataset é pequeno e autoral, com variações de formulação correlacionadas. Não há estimativa de significância estatística ou validade externa. A melhoria observada, se houver, está restrita a esse protocolo; um sistema real exigiria uma amostra maior e avaliação humana independente.

Os documentos entram no contexto para fornecer os fatos; o treinamento procura melhorar o comportamento de resposta, o formato e o uso das evidências. Não se conclui que o modelo memorizou corretamente todo o domínio, nem que LoRA elimina alucinações.

## Cinco erros reais, causas prováveis e correções

Os exemplos abaixo foram retirados dos arquivos de execução. Não foram fabricados. As causas são hipóteses técnicas de diagnóstico; as correções são propostas, não melhorias já comprovadas. A revisão semântica desses casos complementa o corretor automático.

@@ERROS@@

## Integração do produto

O Streamlit importa um CSV fictício, envia-o à API para validação, edita hipóteses de consumo, pede cálculo e exibe a comparação. O modo recomendado usa `POST /consultar-base` para mostrar notas relacionadas diretamente, sem paráfrase da LLM. Os três modos experimentais usam `POST /perguntar`, com sua limitação factual explícita. As fontes são apresentadas com seus links. A demonstração funciona localmente; não houve implantação pública.

| Rota | Função |
| --- | --- |
| GET /saude | Disponibilidade do serviço e dos recursos locais |
| POST /ingerir-consumo | Validar CSV, sem persistir os dados |
| POST /simular | Estimativa determinística de consumo e custo da energia |
| POST /perguntar | Inferência experimental em A, B ou C, com verificação de formato e fonte |
| POST /consultar-base | Consulta documental recomendada, sem texto sintetizado pela LLM |
| GET /fontes e /trechos | Inspeção da base e da proveniência |
| GET /buscar | Inspeção da recuperação local |
| GET /resultados | Placar e evidências do treinamento |

## Segurança, explicabilidade e proteção de dados

- O exemplo doméstico e as perguntas de avaliação são sintéticos. Não foram usados CPF, endereço, número de instalação ou faturas reais. Nomes e RMs da equipe constam por exigência acadêmica e foram fornecidos para o relatório.
- A API não grava perguntas ou CSVs importados. O CSV validado fica na sessão do Streamlit; a conversa também fica na sessão e pode ser limpa. Logs operacionais registram rotas/status, sem corpo das perguntas.
- Recursos remotos são obtidos em etapa própria de preparação. A inferência usa arquivos locais e modo offline; nenhum serviço de geração externo recebe as perguntas.
- Entrada limitada, validação numérica com rejeição de NaN/infinito, CSV de até 100 KB/50 equipamentos e pergunta de até 800 caracteres. Os serviços escutam em 127.0.0.1 e não incluem autenticação para uso público.
- O contexto é tratado como informação, sem execução de comandos ou código gerado. A busca pode recusar por limiar; a API valida esquema e existência dos IDs citados.
- Explicabilidade: mostrar o trecho e sua publicação de origem. Não se apresenta uma cadeia interna de raciocínio como prova da decisão.
- Para o requisito de LGPD, a finalidade, minimização, retenção e acesso são documentados neste recorte. Executar localmente não basta, por si só, para certificar conformidade. A ampliação do MVP para dados reais exigiria definir responsáveis e revisar o fluxo de tratamento e os controles conforme o contexto.

Referência para detalhamento das medidas: [guia da ANPD](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte). Os controles acima são os do protótipo, sem alegação de certificação jurídica ou segurança de produção.

## Ambiente e reprodução

@@AMBIENTE@@

Veja [README.md](README.md) para instalar, iniciar, treinar e executar notebooks. O modelo original e o encoder ficam fora do Git; revisões e hashes estão em `modelos/revisoes.json`. O adaptador treinado é incluído. `requirements.lock.txt` registra as dependências transitivas utilizadas. Os 23 testes cobrem cálculos, dados inválidos, ingestão/API, integridade das partições e submissão de cenário pela interface.

As bibliotecas emitiram avisos de descontinuação no adaptador de testes, sem falha de execução. Os testes não são uma validação de verdade factual da LLM; essa avaliação está nos resultados, no gabarito e nos casos revisados.

## Entrega e links

Este relatório, os notebooks com saídas, código, base, testes e adaptador estão no repositório Git local. A publicação no GitHub e o vídeo serão feitos pelo aluno, conforme o escopo confirmado. Por isso não foram inventados links externos. Após publicar, o próprio endereço deste repositório identifica a entrega; o link do vídeo pode ser acrescentado pelo aluno.

Base metodológica: aulas fornecidas da disciplina, especialmente baseline, avaliação separada, LoRA, RAG e inspeção de falhas. Referências técnicas: [SmolLM2](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), [E5](https://huggingface.co/intfloat/multilingual-e5-small), [PEFT](https://huggingface.co/docs/peft/index) e [Streamlit](https://docs.streamlit.io/).
'''
    training_text=(f"Parâmetros LoRA treináveis: **{history['parametros_treinaveis']:,}**; parâmetros totais com adaptador: {history['parametros_totais']:,}. "
                   f"Rank {history['config']['rank']}, alpha {history['config']['alpha']}, dropout {history['config']['dropout']}, learning rate {history['config']['learning_rate']}, "
                   f"lote {history['config']['lote']}, acumulação {history['config']['acumulacao']}, float32, {history['config']['threads']} threads. "
                   f"Executadas {len(history['epocas'])} épocas; melhor época: **{history['melhor_epoca']}**. Loss inicial de validação: {history['loss_validacao_inicial']:.4f}. "
                   f"Duração: {history['duracao_s']/60:.1f} minutos; RAM de pico do processo amostrada: {history['ram_pico_gb']:.2f} GB. "
                   f"Adaptador: {history['adaptador_bytes']/1024**2:.2f} MiB. O valor de RAM é uma amostra por lote, não a memória total do sistema nem uma garantia de pico absoluto.")
    fields={"REVISAO":review_table,"CONCLUSAO_SEMANTICA":semantic_conclusion,"EQUIPE":team_table,"FONTES":source_table,"HASH_TESTE":manifest["teste_sha256"],"TREINO":training_text,"EPOCAS":epoch_table,
            "CALIBRACAO":f"Limiar escolhido: **{calibration['limiar']}**. Na validação: recall@3 **{calibration['recall_3']:.0%}**, rejeição correta **{calibration['rejeicao_correta']:.0%}**. Curva e casos em `avaliacao/calibracao.json`.",
            "PLACAR":score_table,"CONCLUSAO":conclusions,"ERROS":"\n".join(case_text),
            "AMBIENTE":table(["Campo","Valor"],[[k,v] for k,v in environment.items() if k in ["python","sistema","torch","transformers","peft","cpu","ram_total_gb","threads","device","max_new_tokens","modelo"]])}
    for key,value in fields.items(): report=report.replace("@@"+key+"@@",value)
    (ROOT/"RELATORIO.md").write_text(report,encoding="utf-8")
    write_json(ROOT/"avaliacao"/"resumo_publico.json",{"interpretacao":semantic_conclusion,"resumo_automatico_com_limitacoes":conclusions,"melhor_epoca":history["melhor_epoca"],"teste_sha256":manifest["teste_sha256"]})
    make_charts(score,history,calibration)
    readme=README.replace("@@RESUMO@@",review_table).replace("@@CONCLUSAO@@",semantic_conclusion).replace("@@EQUIPE@@",team_table)
    (ROOT/"README.md").write_text(readme,encoding="utf-8")
    print("Relatório, README, CSV, gráficos e cinco erros reais gerados.")


def make_charts(score,history,calibration):
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    out=ROOT/"relatorio"/"graficos"; out.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(read_json(ROOT/"avaliacao"/"placar_revisado.json"))
    df["Configuração"]=df["configuracao"].map(LABELS)
    data=df.melt(id_vars="Configuração",value_vars=["acerto_total_revisado_pct","acerto_completo_revisado_pct","acerto_factual_revisado_pct"],var_name="Métrica",value_name="%")
    data["Métrica"]=data["Métrica"].map({"acerto_total_revisado_pct":"Acerto total revisado","acerto_completo_revisado_pct":"Acerto completo revisado","acerto_factual_revisado_pct":"Acerto factual nas respondíveis"})
    fig=px.bar(data,x="Configuração",y="%",color="Métrica",barmode="group",range_y=[0,105],color_discrete_sequence=["#237A58","#A3C768","#BD745C"],title="Energia Clara — revisão semântica assistida de 60 perguntas")
    fig.write_html(out/"placar.html",include_plotlyjs=True,full_html=True)
    epochs=history["epocas"]
    fig=go.Figure()
    fig.add_scatter(x=[0]+[e["epoca"] for e in epochs],y=[history["loss_validacao_inicial"]]+[e["loss_validacao"] for e in epochs],name="Validação",mode="lines+markers")
    fig.add_scatter(x=[e["epoca"] for e in epochs],y=[e["loss_treino"] for e in epochs],name="Treino",mode="lines+markers")
    fig.update_layout(title="Perda média ponderada pelos tokens supervisionados",xaxis_title="Época",yaxis_title="Cross-entropy")
    fig.write_html(out/"aprendizado.html",include_plotlyjs=True,full_html=True)


README=r'''# Energia Clara

**Assistente local de uso consciente de energia residencial.** MVP em Streamlit, API FastAPI, simulação de consumo por CSV e comparação real de SmolLM2 sem contexto, RAG simples e RAG + LoRA. Treinamento feito em CPU neste computador.

![Painel da casa fictícia](relatorio/capturas/painel.jpg)

## Abrir a demonstração

Neste computador, dê dois cliques em **`Iniciar_Energia_Clara.bat`**. A interface abre em [127.0.0.1:8501](http://127.0.0.1:8501). Para encerrar os dois serviços gerenciados por esse atalho, use **`Parar_Energia_Clara.bat`**.

- **Visão geral:** consumo estimado e participação dos aparelhos da casa fictícia.
- **Simular consumo:** importar CSV, editar hábitos e comparar cenários.
- **Assistente:** consulta documental recomendada; três modos de geração identificados como experimentais.
- **Base de conhecimento:** 30 notas e 11 publicações com proveniência/licença.
- **Resultados:** placar real, curva de validação e evidências do treino.

O CSV de exemplo é `dados/consumo_exemplo.csv`. As potências, tempos, tarifa e fatores são hipóteses fictícias e editáveis. O cálculo estima a parcela de energia, não o total da fatura. Não envie dados pessoais ou contas reais para a demonstração.

## Resultados reais

@@RESUMO@@

@@CONCLUSAO@@

**Limite da medida:** a tabela acima usa revisão semântica assistida por IA, sem alegar revisão humana independente. O corretor automático inicial teve falsos positivos/negativos e foi preservado para auditoria. Seu indicador operacional não deve ser tratado como uma taxa comprovada de alucinação. Há 40 perguntas respondíveis de 10 grupos factuais correlacionados e 20 sem resposta na base. Formato, recuperação, recusa e fundamentação são medidos separadamente.

Leia o [relatório completo](RELATORIO.md), o [placar detalhado](avaliacao/placar.csv) e os [cinco erros reais](avaliacao/cinco_erros.json).

## Preparar em outro computador

Ambiente testado: Windows, Python 3.14.7, CPU e 16 GB de RAM. Os comandos são executados na pasta deste repositório. Internet é necessária para instalar bibliotecas e baixar os modelos; depois, a inferência é local.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m scripts.baixar_recursos --apenas-modelos
.\.venv\Scripts\python.exe -m scripts.servicos iniciar
```

O modelo original e o encoder foram excluídos do Git. `modelos/revisoes.json` fixa as revisões e os hashes; o comando de download reaproveita essas revisões. O adaptador treinado está em `modelos/adaptador/`. Não é necessário treinar novamente para usar a demonstração distribuída.

Os modelos somam aproximadamente 0,75 GB em pesos, além de tokenizadores, bibliotecas e cache. Reserve alguns GB de disco. Em CPU, a primeira pergunta carrega recursos e pode demorar mais. O uso de memória e o tempo efetivamente medidos estão no relatório.

O ambiente já criado nesta máquina reutiliza PyTorch e algumas bibliotecas previamente disponíveis via `--system-site-packages`, sem alterar a instalação global. O roteiro acima cria um ambiente novo e usa o arquivo de versões exportado das dependências efetivamente utilizadas.

## Reproduzir o experimento

```powershell
.\.venv\Scripts\python.exe -m scripts.preparar_dados
.\.venv\Scripts\python.exe -m scripts.baixar_recursos
.\.venv\Scripts\python.exe -m scripts.treinar_lora --piloto
.\.venv\Scripts\python.exe -m scripts.experimento
.\.venv\Scripts\python.exe -m scripts.gerar_relatorio
.\.venv\Scripts\python.exe -m scripts.gerar_notebooks --executar
.\.venv\Scripts\python.exe -m pytest -q
```

`experimento` se recusa a sobrescrever uma avaliação C já existente. Para um novo experimento completo, **copie a pasta do projeto sem os três `avaliacao/resultados_*.jsonl`, `historico_treino.json`, `placar.json` e o adaptador**, ou arquive esses arquivos deliberadamente. O roteiro acima descreve uma reprodução limpa; o repositório entregue já contém os resultados. `--continuar` retoma etapas completas/incompletas do mesmo protocolo; não serve para comparar dados ou modelos alterados. Não troque o teste para melhorar o placar publicado.

Os notebooks leem os artefatos reais, verificam suas assinaturas e exibem as saídas; o treinamento longo é feito pelo script próprio, não repetido silenciosamente ao abrir um notebook. O notebook de integração também faz chamadas reais à API local. Os gráficos HTML são autocontidos e não precisam de CDN.

A conferência final foi registrada em [avaliacao/verificacao_entrega.json](avaliacao/verificacao_entrega.json), com os três notebooks executados, 60 saídas por configuração, cinco erros reais e 23 testes aprovados. Para repetir a checagem dos artefatos sem treinar, execute `.\.venv\Scripts\python.exe -m scripts.verificar_entrega`. O Git preserva os bytes originais para não invalidar os hashes por conversão de quebras de linha.

A revisão semântica distribuída se aplica somente às saídas publicadas, conferidas por hash. Em uma nova execução, é necessário revisar as novas saídas antes de gerar uma nova conclusão; o programa recusa reutilizar a anotação antiga.

O modo offline é o padrão de execução. Apenas `scripts.baixar_recursos` habilita a etapa de obtenção pública. Os snapshots originais ficam fora do Git por direitos/licenças; o corpus distribuído contém notas autorais atribuídas.

## API

Documentação interativa: [127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

```json
{"pergunta":"Qual posição do chuveiro ajuda a economizar?","configuracao":"lora_rag"}
```

Envie o JSON a `POST /perguntar`. Configurações aceitas: `sem_contexto`, `rag`, `lora_rag`. A resposta contém `status`, `resposta`, `fontes`, evidências, origem da decisão e tempo. `status=erro` identifica falha de formato/fonte; não é uma resposta factual validada. `POST /simular` e `POST /ingerir-consumo` são usados pela própria interface.

O modo recomendado recebe `{"pergunta":"Como economizar energia com o chuveiro?"}` em `POST /consultar-base`. Ele retorna notas literais e suas fontes, com `modelo_chamado=false`. A similaridade pode trazer notas apenas relacionadas; verifique sua pertinência. Isso não substitui nem é contabilizado como geração da LLM treinada.

Serviços limitados ao computador local, sem autenticação pública. O código não é uma implantação de produção e não consulta tarifas atuais. Os limites, medidas de proteção de dados e avaliação estão no relatório.

## Organização

```text
api/               API do produto
energia_clara/     busca, geração, contratos, cálculo e avaliação
scripts/           preparação, download, treino, avaliação e documentação
base/              notas, fontes, licenças e índice local
dados/             consumo fictício de exemplo
avaliacao/         treino/validação/teste, saídas brutas, placar e erros
modelos/           revisões e adaptador LoRA treinado
notebooks/         notebooks executados com saídas
relatorio/         gráficos e capturas da demonstração
tests/             verificações funcionais e de integridade
```

## Equipe

@@EQUIPE@@

## Publicação e vídeo

Foi preparado somente um **repositório Git local**, sem remoto e sem publicação. O aluno fará o envio manual ao seu GitHub público e gravará o vídeo posteriormente. Não há links externos inventados. O material original das aulas, o ambiente virtual, caches, snapshots das páginas e pesos completos dos modelos não entram no Git.

Código próprio sob [MIT](LICENSE); notas e perguntas sob [CC BY 4.0](base/LICENCA.md); adaptador derivado de SmolLM2 sob [Apache-2.0](modelos/adaptador/LICENCA.md). Os direitos dos documentos de referência são preservados. A base metodológica são as aulas fornecidas da disciplina.
'''


if __name__=="__main__": main()
