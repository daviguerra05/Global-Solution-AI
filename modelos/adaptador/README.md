---
base_model: HuggingFaceTB/SmolLM2-135M-Instruct
library_name: peft
pipeline_tag: text-generation
license: apache-2.0
language:
- pt
tags:
- lora
- energy
- academic
---

# Energia Clara — adaptador LoRA acadêmico

Adaptador treinado pela Equipe Energia Clara para responder a perguntas educativas sobre uso consciente de energia residencial, usando contexto recuperado e saída JSON. O artefato é um experimento local; a avaliação encontrou baixa qualidade factual e não recomenda geração livre para usuários finais. O produto prioriza a exibição literal de notas com fontes.

## Modelo e treinamento

- Base: [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), revisão `12fd25f77366fa6b3b4b768ec3050bf629380bac`.
- Treino: 200 exemplos sintéticos autorais, sendo 140 respondíveis e 60 recusas; 20 exemplos de validação. Perguntas e grupos factuais disjuntos do teste.
- LoRA: rank 8, alpha 16, dropout 0,05, sete tipos de projeção, 2.442.240 parâmetros treináveis.
- Execução: CPU, float32, seis threads, lote 2, acumulação 2 e learning rate 0,0003.
- Três épocas executadas, seleção da primeira pela perda de validação; parada após duas épocas sem melhora.
- A perda supervisiona somente resposta e EOS, com prompt e padding mascarados.
- Treinamento real de aproximadamente 24 minutos neste computador. Histórico e curvas estão em [avaliacao/historico_treino.json](../../avaliacao/historico_treino.json) e nos [notebooks](../../notebooks/).

## Resultado e limitações

No teste congelado de 60 perguntas, a revisão semântica assistida por IA encontrou um fato correto entre 40 perguntas respondíveis e 11 recusas apropriadas entre 20 perguntas sem resposta. O RAG simples com o modelo original acertou 20 fatos, portanto LoRA **piorou o conteúdo factual**. A conformidade JSON foi de 94,23% nas 52 chamadas à LLM; as oito recusas por busca não são geração do modelo.

As 40 perguntas respondíveis representam quatro formulações de dez fatos, sem independência entre as paráfrases. A revisão foi assistida por IA, não humana independente. O corretor automático inicial errou em ambos os sentidos e foi preservado para auditoria. Consulte o [relatório](../../RELATORIO.md) para critérios, denominadores, saídas reais e cinco falhas analisadas.

O modelo original tem foco em inglês; o conjunto é pequeno, em português e de domínio restrito. São observados erros de unidade, incoerência e citações que não sustentam as afirmações. Não usar para tarifas atuais, promessas de economia, diagnóstico elétrico ou decisões sobre instalações.

## Uso local e proveniência

Siga o [README principal](../../README.md) para instalar as versões verificadas e obter os pesos originais. A aplicação carrega primeiro o modelo base local, depois este adaptador com PEFT. O adaptador não contém o modelo completo nem o encoder E5.

O SHA-256 de `adapter_model.safetensors` é `a1fbd1ead71c928c332c36e5ce57b01a9398b67be52a8e347a634a2eb55b043f`. [proveniencia.json](proveniencia.json) registra a execução; [modelos/revisoes.json](../revisoes.json) fixa os recursos originais. As notas, os dados e suas fontes/licenças estão em [base](../../base/).

Adaptador sob [Apache-2.0](LICENSE), preservando a licença do modelo original. Código próprio sob MIT; notas e perguntas autorais sob CC BY 4.0. As licenças dos documentos de referência permanecem com os autores e os originais não são redistribuídos.
