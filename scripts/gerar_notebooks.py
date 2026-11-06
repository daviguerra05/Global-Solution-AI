"""Cria e executa notebooks auditáveis; não fabrica outputs ou reexecuta o treino ao abrir."""
from energia_clara.config import ROOT,write_json
import argparse
import os
import sys

SETUP='''from pathlib import Path
import sys, json, hashlib
ROOT=Path.cwd()
if not (ROOT/'energia_clara').exists(): ROOT=ROOT.parent
assert (ROOT/'energia_clara').exists()
sys.path.insert(0,str(ROOT))
from energia_clara.config import read_json,read_jsonl
import pandas as pd
from IPython.display import display,Markdown
print('Python:',sys.version.split()[0])
'''


def main():
    import nbformat as nbf
    parser=argparse.ArgumentParser(); parser.add_argument("--executar",action="store_true")
    args=parser.parse_args()
    out=ROOT/"notebooks"; out.mkdir(exist_ok=True)
    notebooks=[
        ("01_base_e_busca",[
            ("md","# 1. Base de conhecimento e recuperação\n\nEvidências da execução real: fontes, notas, partições e calibração. O teste não é usado para escolher o limiar."),
            ("code",SETUP),
            ("code","""manifest=read_json(ROOT/'avaliacao/manifesto_dados.json')
assert hashlib.sha256((ROOT/'avaliacao/teste.jsonl').read_bytes()).hexdigest()==manifest['teste_sha256']
display(pd.DataFrame([manifest]))
sources=read_json(ROOT/'base/fontes.json')
chunks=read_jsonl(ROOT/'base/trechos.jsonl')
display(pd.DataFrame([{'fonte':s['id'],'instituição':s['entidade'],'formato':s['formato'],'trechos':sum(c['fonte_id']==s['id'] for c in chunks),'url':s['url']} for s in sources]))
display(pd.DataFrame(chunks)[['id','titulo','texto','fonte_id','particao_qa']])"""),
            ("code","""calibration=read_json(ROOT/'avaliacao/calibracao.json')
print('Limiar escolhido apenas na validação:',calibration['limiar'])
print('Recall@3 da validação:',calibration['recall_3'])
print('Rejeição correta na validação:',calibration['rejeicao_correta'])
display(pd.DataFrame(calibration['curva']).sort_values(['equilibrio','recall_3'],ascending=False).head(12))
display(pd.DataFrame([{'pergunta':q['pergunta'],'tipo':q['tipo'],'gold':q['trechos_relevantes'],'recuperados':q['recuperados']} for q in calibration['detalhes']]))"""),
            ("md","O índice é local e exato, com vetores normalizados do E5. Recall é medido nas respondíveis; recusa é medida separadamente. As 40 formulações do teste pertencem a 10 grupos de fatos e não são independentes.")
        ]),
        ("02_treinamento_local",[
            ("md","# 2. Treinamento LoRA executado em CPU\n\nO treino longo foi executado por `python -m scripts.experimento`, que chama o laço real em `scripts/treinar_lora.py`. Este notebook verifica e apresenta o histórico salvo. Abrir ou executar este notebook não repete o treino silenciosamente."),
            ("code",SETUP),
            ("code","""history=read_json(ROOT/'avaliacao/historico_treino.json')
adapter=ROOT/'modelos/adaptador/adapter_model.safetensors'
assert hashlib.sha256(adapter.read_bytes()).hexdigest()==history['adaptador_sha256']
assert history['mascara_prompt_verificada']
assert not history['pilot']
print('Modelo:',history['modelo'])
print('Parâmetros treináveis:',history['parametros_treinaveis'])
print('Máscara do prompt e EOS verificados:',history['mascara_prompt_verificada'])
print('Melhor época pela validação:',history['melhor_epoca'])
print('Duração real em minutos:',round(history['duracao_s']/60,2))
print('RAM de pico amostrada do processo, GB:',round(history['ram_pico_gb'],2))
display(pd.DataFrame([history['config']]))
display(pd.DataFrame(history['epocas']))
display(pd.DataFrame(history['passos']).iloc[[0,1,2,-3,-2,-1]])"""),
            ("code","""import plotly.graph_objects as go
epochs=history['epocas']
fig=go.Figure()
fig.add_scatter(x=[0]+[x['epoca'] for x in epochs],y=[history['loss_validacao_inicial']]+[x['loss_validacao'] for x in epochs],mode='lines+markers',name='Validação')
fig.add_scatter(x=[x['epoca'] for x in epochs],y=[x['loss_treino'] for x in epochs],mode='lines+markers',name='Treino')
fig.update_layout(title='Perda por época — seleção pelo menor valor de validação',xaxis_title='Época',yaxis_title='Cross-entropy')
display(fig)"""),
            ("md","A perda de treino caiu enquanto a validação piorou após a primeira época. O checkpoint da primeira época foi recarregado; não foi escolhido pelo teste. A revisão semântica da geração está no próximo notebook. A cópia exata do treinador usado inicialmente foi preservada em `avaliacao/protocolo_executado/`; a versão distribuída evita uma consulta remota opcional do PEFT no salvamento.")
        ]),
        ("03_avaliacao_e_integracao",[
            ("md","# 3. Avaliação, erros e integração real\n\nOs três sistemas receberam o mesmo teste. Preservamos o corretor automático e uma revisão semântica assistida separada, que expôs falsos positivos e negativos. A revisão não é avaliação humana independente. As células de integração abaixo chamam a API local de verdade; inicie os serviços antes de executá-las."),
            ("code",SETUP),
            ("code","""score=read_json(ROOT/'avaliacao/placar.json')
review=read_json(ROOT/'avaliacao/placar_revisado.json')
for row in review:
    path=ROOT/'avaliacao'/('resultados_'+row['configuracao']+'.jsonl')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['saida_sha256']
display(Markdown('## Placar revisado'))
display(pd.DataFrame(review).drop(columns=['saida_sha256']))
display(Markdown('## Placar automático original — não confundir com acurácia semântica'))
display(pd.DataFrame(score))
assert read_json(ROOT/'avaliacao/conclusao_execucao.json')['contextos_b_c_identicos']
print('Contextos de B e C idênticos: verificado na execução.')"""),
            ("code","""errors=read_json(ROOT/'avaliacao/cinco_erros.json')
for i,e in enumerate(errors,1):
    display(Markdown(f\"### Erro {i}: {e['categoria']} — {e['id']}\"))
    print('Pergunta:',e['pergunta'])
    print('Esperado:',e['resposta_esperada'])
    print('Saída real:',e['saida_bruta'] or e['resposta_pipeline'])
    print('Causa provável:',e['causa_provavel'])
    print('Correção proposta:',e['correcao_proposta'])"""),
            ("code","""import requests
session=requests.Session(); session.trust_env=False
API='http://127.0.0.1:8000'
health=session.get(API+'/saude',timeout=10); health.raise_for_status()
print('API real:',health.json())
with (ROOT/'dados/consumo_exemplo.csv').open('rb') as f:
    uploaded=session.post(API+'/ingerir-consumo',files={'arquivo':('consumo.csv',f,'text/csv')},timeout=10)
uploaded.raise_for_status()
assert uploaded.json()['registros']==8
sim=session.post(API+'/simular',json={'aparelhos':uploaded.json()['dados'],'tarifa_kwh':0.95},timeout=10)
sim.raise_for_status()
assert sim.json()['consumo_total_kwh']==229.84
print('Simulação via API:',sim.json())
source=session.post(API+'/consultar-base',json={'pergunta':'Como economizar energia com o chuveiro?'},timeout=180)
source.raise_for_status()
print('Consulta documental via API:',source.json())
experiment=session.post(API+'/perguntar',json={'pergunta':'Aderir à Tarifa Branca sempre deixa a conta mais barata?','configuracao':'lora_rag'},timeout=180)
experiment.raise_for_status()
print('Geração LoRA via API:',experiment.json())
evidence={'saude':health.json(),'ingestao_registros':uploaded.json()['registros'],'simulacao':sim.json(),'consulta_base':source.json(),'geracao_experimental':experiment.json(),
          'nota':'A pergunta da Tarifa Branca é da família de treino; demonstra integração, não generalização. Não compõe o placar final.'}
from energia_clara.config import write_json
write_json(ROOT/'avaliacao/demonstracao_api.json',evidence)"""),
            ("md","## Interpretação\n\nLoRA melhorou JSON e parte das recusas, mas não sustentou ganho factual frente ao RAG simples. O produto prioriza apresentar as notas com fontes diretamente. Essa consulta documental não foi creditada como geração ou como resultado do treinamento. O objetivo de uso livre em produção requer novo ciclo de dados e validação.")
        ])
    ]
    kernelroot=ROOT/"runtime"/"jupyter"
    spec=kernelroot/"kernels"/"energia-clara"
    spec.mkdir(parents=True,exist_ok=True)
    write_json(spec/"kernel.json",{"argv":[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"],"display_name":"Energia Clara (.venv)","language":"python"})
    os.environ["JUPYTER_PATH"]=str(kernelroot)
    os.environ["JUPYTER_RUNTIME_DIR"]=str(ROOT/"runtime"/"jupyter_runtime")
    os.environ["IPYTHONDIR"]=str(ROOT/"runtime"/"ipython")
    manifest=[]
    for name,cells in notebooks:
        nb=nbf.v4.new_notebook(cells=[nbf.v4.new_markdown_cell(s) if kind=="md" else nbf.v4.new_code_cell(s) for kind,s in cells])
        nb.metadata["kernelspec"]={"name":"energia-clara","display_name":"Energia Clara (.venv)","language":"python"}
        if args.executar:
            from nbclient import NotebookClient
            print("Executando:",name,flush=True)
            NotebookClient(nb,timeout=240,kernel_name="energia-clara",resources={"metadata":{"path":str(ROOT)}}).execute()
        dest=out/(name+".ipynb")
        nbf.write(nb,dest)
        manifest.append({"notebook":dest.name,"executado":args.executar,"celulas_codigo":sum(c.cell_type=="code" for c in nb.cells),
                         "celulas_com_saida":sum(bool(c.get("outputs")) for c in nb.cells if c.cell_type=="code")})
    write_json(ROOT/"avaliacao"/"notebooks_executados.json",manifest)
    print(manifest,flush=True)


if __name__=="__main__": main()
