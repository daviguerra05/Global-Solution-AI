"""Interface do MVP. As operações do produto usam a API local por HTTP."""
from pathlib import Path
import os
import io
import html
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT=Path(__file__).resolve().parent
API=os.environ.get("ENERGIA_API_URL","http://127.0.0.1:8000")
st.set_page_config(page_title="Energia Clara · Sua casa, mais consciente",page_icon="🌿",layout="wide")
st.markdown('''<style>
.block-container{padding-top:4rem;max-width:1280px}h1,h2,h3{letter-spacing:-.04em}h1{font-size:2.6rem!important}
[data-testid="stSidebar"]{background:#183D30}[data-testid="stSidebar"] *{color:#F0F6E9!important}
[data-testid="stSidebar"] hr{border-color:#3E6653} [data-testid="stMetric"]{background:white;border:1px solid #DFE7DC;border-radius:16px;padding:20px}
[data-testid="stMetricLabel"]{color:#698073;font-size:.86rem}[data-testid="stMetricValue"]{font-size:2rem;font-weight:650}
.hero{background:linear-gradient(115deg,#1A503B,#133D2E);color:#F3F8E9;padding:34px 38px;border-radius:22px;margin:6px 0 28px;position:relative;overflow:hidden}
.hero h2{color:#F3F8E9;font-size:2rem;margin:8px 0 10px;line-height:1.2}.hero p{max-width:650px;color:#D4E6C9;margin:0;font-size:1rem;line-height:1.7}
.eyebrow{font-size:.72rem;letter-spacing:.15em;font-weight:650;text-transform:uppercase;color:#B8D883}
.pill{display:inline-block;border:1px solid #52734D;border-radius:50px;padding:5px 12px;color:#DBEDCA;font-size:.72rem;margin-bottom:8px}
.subtle{color:#6D8175;font-size:.92rem}.note{padding:18px 22px;border-radius:14px;background:#E8EFDF;border:1px solid #D9E6CC;color:#395D3D;margin:16px 0;line-height:1.6}
.brand{font-size:1.6rem;font-weight:700;letter-spacing:-.04em;margin:12px 0 0}.brand-sub{color:#BCD1BB!important;font-size:.8rem;margin-bottom:34px}
.source-note{border-left:3px solid #91B45F;padding-left:16px;margin:14px 0 22px}.footer{margin-top:36px;border-top:1px solid #DCE5D7;padding-top:16px;color:#7B8C7E;font-size:.75rem}
div.stButton>button[kind="primary"]{border-radius:10px}div[data-testid="stExpander"]{border-radius:12px;background:#fff}
</style>''',unsafe_allow_html=True)


def api(method,path,**kwargs):
    try:
        response=requests.request(method,API+path,timeout=kwargs.pop("timeout",8),**kwargs)
        if response.ok: return response.json(),None
        detail=response.json().get("detail","Não foi possível concluir a operação.")
        if isinstance(detail,list): detail="Confira os campos informados e os limites da simulação."
        return None,str(detail)
    except requests.RequestException:
        return None,"A interface está aberta, mas não conseguiu acessar a API local. Execute Iniciar_Energia_Clara.bat e confira a mensagem na janela. Se houver bloqueio do Windows, reiniciar o atalho não resolve: consulte runtime/diagnostico_api.log e docs/AUDITORIA_ENTREGA.md."


@st.cache_data(ttl=5)
def health(): return api("GET","/saude",timeout=2)[0]


def money(value): return "R$ "+f"{value:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def number(value,digits=1):
    if abs(value)<0.5*10**(-digits): value=0
    return f"{value:,.{digits}f}".replace(",","X").replace(".",",").replace("X",".")


def base_records():
    return pd.read_csv(ROOT/"dados"/"consumo_exemplo.csv").to_dict("records")


if "aparelhos" not in st.session_state: st.session_state.aparelhos=base_records()
if "tarifa" not in st.session_state: st.session_state.tarifa=0.95
if "chat" not in st.session_state: st.session_state.chat=[]

with st.sidebar:
    st.markdown('<div class="brand">◒ energia clara</div><div class="brand-sub">Sua casa, mais consciente.</div>',unsafe_allow_html=True)
    page=st.radio("Navegação",["Visão geral","Simular consumo","Assistente","Base de conhecimento","Resultados"],label_visibility="collapsed")
    st.divider()
    status=health()
    st.caption("● Serviço local disponível" if status else "○ Serviço local aguardando início")
    st.caption("Dados de demonstração. Nenhuma conexão com sua concessionária.")
    st.markdown("<br><br>",unsafe_allow_html=True)
    st.caption("GLOBAL SOLUTION · 2026")
    st.caption("Energia e inteligência artificial para escolhas mais conscientes.")


def simulation(records=None,tariff=None):
    return api("POST","/simular",json={"aparelhos":records if records is not None else st.session_state.aparelhos,
                                         "tarifa_kwh":st.session_state.tarifa if tariff is None else tariff})


def consumption_chart(result):
    df=pd.DataFrame(result["aparelhos"]).sort_values("consumo_kwh")
    fig=px.bar(df,x="consumo_kwh",y="aparelho",orientation="h",text="consumo_kwh",
               color_discrete_sequence=["#237B59"],labels={"consumo_kwh":"Consumo estimado · kWh/mês","aparelho":""})
    fig.update_traces(texttemplate="%{x:.1f}",textposition="outside",marker_line_width=0,cliponaxis=False)
    fig.update_layout(height=360,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=0,r=35,t=10,b=0),font=dict(color="#315747"),xaxis=dict(showgrid=True,gridcolor="#DFE8DA",rangemode="tozero"))
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


if page=="Visão geral":
    st.markdown("<span class='eyebrow' style='color:#69836A'>PAINEL DA SUA CASA</span>",unsafe_allow_html=True)
    st.title("Pequenos hábitos. Energia bem usada.")
    st.markdown("<p class='subtle'>Entenda para onde vai a energia e descubra o que pode mudar na sua rotina.</p>",unsafe_allow_html=True)
    st.markdown('<div class="hero"><span class="pill">CASA FICTÍCIA · SIMULAÇÃO EDITÁVEL</span><h2>Economizar começa<br>por entender o consumo.</h2><p>Veja o impacto dos seus aparelhos, experimente novos hábitos e consulte orientações com fontes públicas. Tudo neste computador.</p></div>',unsafe_allow_html=True)
    result,error=simulation()
    if error: st.info(error)
    else:
        total=result["consumo_total_kwh"]
        biggest=result["aparelhos"][0]
        a,b,c=st.columns(3)
        a.metric("Consumo mensal estimado",number(total)+" kWh")
        b.metric("Parcela de energia simulada",money(result["custo_energia_estimado"]))
        c.metric("Maior participação",biggest["aparelho"],number(100*biggest["consumo_kwh"]/total if total else 0)+"% do cenário",delta_color="off")
        left,right=st.columns([1.7,1],gap="large")
        with left:
            st.subheader("Cada aparelho conta")
            consumption_chart(result)
        with right:
            st.subheader("Seu próximo passo")
            st.markdown('<div class="note"><b>Comece pelo maior consumo.</b><br>Na simulação, reduzir o tempo de uso dos aparelhos com maior participação pode ter mais impacto. Teste uma mudança antes de decidir.</div>',unsafe_allow_html=True)
            st.write("Use **Simular consumo** para importar dados e experimentar outro cenário.")
            st.write("No **Assistente**, pergunte sobre hábitos, etiquetas e uso eficiente dos equipamentos.")
            st.caption("Tarifa fictícia: "+money(st.session_state.tarifa)+"/kWh. A estimativa não representa o total de uma conta de luz.")

elif page=="Simular consumo":
    st.title("E se a rotina mudar?")
    st.write("Carregue um exemplo ou importe um CSV. Ajuste o uso dos aparelhos e compare as estimativas.")
    with st.expander("Importar dados de consumo",expanded=True):
        a,b=st.columns([2,1])
        with a:
            upload=st.file_uploader("Arquivo CSV com equipamentos e hábitos de uso",type=["csv"],help="Até 50 equipamentos e 100 KB. Use dados fictícios, sem nomes, endereços ou dados da conta.")
            if upload is not None and st.button("Validar e usar arquivo"):
                data,error=api("POST","/ingerir-consumo",files={"arquivo":("consumo.csv",upload.getvalue(),"text/csv")})
                if error: st.error(error)
                else:
                    st.session_state.aparelhos=data["dados"]
                    st.success(f"{data['registros']} equipamentos validados. Dados mantidos apenas nesta sessão.")
        with b:
            st.download_button("Baixar CSV de exemplo",(ROOT/"dados"/"consumo_exemplo.csv").read_bytes(),"consumo_exemplo.csv","text/csv")
            if st.button("Restaurar casa fictícia"):
                st.session_state.aparelhos=base_records(); st.session_state.tarifa=0.95; st.rerun()
        st.caption("Ingestão: arquivo → validação de campos e limites → cálculo local → comparação. Não há coleta de medidores reais.")
    before,error=simulation()
    if error: st.info(error)
    else:
        with st.form("form_simulacao"):
            frame=st.data_editor(pd.DataFrame(st.session_state.aparelhos),num_rows="dynamic",hide_index=True,width="stretch",
                column_config={"aparelho":st.column_config.TextColumn("Equipamento",required=True),
                "potencia_w":st.column_config.NumberColumn("Potência · W",min_value=1,max_value=30000,required=True),
                "horas_dia":st.column_config.NumberColumn("Horas/dia",min_value=0,max_value=24,step=0.1,required=True),
                "dias_mes":st.column_config.NumberColumn("Dias/mês",min_value=0,max_value=31,required=True),
                "quantidade":st.column_config.NumberColumn("Quantidade",min_value=1,max_value=100,step=1,required=True),
                "fator_uso":st.column_config.NumberColumn("Fator de uso",min_value=0.01,max_value=1,step=0.05,required=True)})
            tariff=st.number_input("Tarifa fictícia para simulação · R$/kWh",min_value=0.0,max_value=10.0,value=float(st.session_state.tarifa),step=0.05)
            st.caption("O fator de uso é uma hipótese editável: 1 = potência constante durante as horas informadas. Em aparelhos que ciclam, a potência nominal × 24h não é medição real. Consulte o consumo da etiqueta para uma referência.")
            submitted=st.form_submit_button("Comparar cenário",type="primary")
        if submitted:
            try:
                records=frame.to_dict("records")
                after,error=simulation(records,tariff)
                if error: st.error(error)
                else: st.session_state.comparacao_cenario={"antes":before,"depois":after,"dados":records,"tarifa":tariff}
            except (ValueError,TypeError): st.error("Preencha todos os campos com valores válidos.")
        if "comparacao_cenario" in st.session_state:
            scenario=st.session_state.comparacao_cenario; old=scenario["antes"]; new=scenario["depois"]
            st.subheader("O impacto da sua mudança")
            delta=old["consumo_total_kwh"]-new["consumo_total_kwh"]
            a,b,c=st.columns(3)
            a.metric("Novo consumo estimado",number(new["consumo_total_kwh"])+" kWh",number(-delta)+" kWh/mês",delta_color="inverse")
            b.metric("Nova parcela de energia",money(new["custo_energia_estimado"]))
            c.metric("Diferença estimada",money(old["custo_energia_estimado"]-new["custo_energia_estimado"])+"/mês")
            if scenario["tarifa"]!=old["tarifa_simulada_kwh"]: st.info("Você também mudou a tarifa hipotética. A diferença de custo combina os efeitos da tarifa e dos hábitos.")
            if st.button("Usar este cenário no painel"):
                st.session_state.aparelhos=scenario["dados"]; st.session_state.tarifa=scenario["tarifa"]; del st.session_state.comparacao_cenario; st.rerun()
            consumption_chart(new)
        st.caption("Cálculo por equipamento: W × horas/dia × dias × quantidade × fator de uso ÷ 1000. Custo estimado = kWh × tarifa fictícia. Tributos e outros componentes da fatura não estão incluídos.")

elif page=="Assistente":
    st.title("Uma orientação, com fonte.")
    st.write("Consulte orientações com fontes públicas. A geração de texto pela LLM também está disponível para explorar o experimento acadêmico.")
    names={"Orientações da base · recomendado":"base","LLM especializada + fontes · experimental":"lora_rag","LLM com fontes · experimental":"rag","LLM sem contexto · experimental":"sem_contexto"}
    choice=st.selectbox("Forma de consulta",list(names),help="Os três modos fazem parte do experimento acadêmico. Sem contexto é apenas referência de comparação.")
    mode=names[choice]
    if mode!="base": st.info("Geração experimental: o modelo pequeno ainda apresenta erros de conteúdo. Compare a resposta com as notas e fontes. O modo recomendado exibe as orientações da base diretamente.")
    st.caption("Exemplos: “Que posição do chuveiro pode economizar energia?” · “A Tarifa Branca sempre compensa?” · “Qual é a tarifa da minha casa hoje?”")
    for item in st.session_state.chat:
        with st.chat_message(item["role"]):
            st.write(item["text"])
            for source in item.get("evidencias",[]):
                with st.expander(source["id"]+" · "+source["titulo"],expanded=item.get("modo")=="base"):
                    st.write(source["texto"])
                    st.markdown(f"[{source['entidade']} — {source['secao']}]({source['url']})")
    question=st.chat_input("O que você quer entender sobre a energia da sua casa?",max_chars=800)
    if question:
        st.session_state.chat.append({"role":"user","text":question})
        with st.chat_message("user"): st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Consultando o assistente local… A primeira resposta pode demorar um pouco."):
                payload={"pergunta":question}
                if mode!="base": payload["configuracao"]=mode
                result,error=api("POST","/consultar-base" if mode=="base" else "/perguntar",json=payload,timeout=180)
            if error: st.error(error)
            else:
                st.write(result["resposta"])
                for source in result.get("evidencias",[]):
                    with st.expander(source["id"]+" · "+source["titulo"],expanded=mode=="base"):
                        st.write(source["texto"])
                        st.markdown(f"[{source['entidade']} — {source['secao']}]({source['url']})")
                st.session_state.chat.append({"role":"assistant","text":result["resposta"],"evidencias":result.get("evidencias",[]),"modo":mode})
                st.caption("Consulta concluída em "+number(result["tempo_s"])+" s. Suas perguntas não são gravadas pela API.")
    if st.session_state.chat and st.button("Limpar conversa desta sessão"):
        st.session_state.chat=[]; st.rerun()
    st.caption("A base é uma fotografia das fontes consultadas em 06/11/2026. Não contém tarifas ao vivo, dados da sua conta nem diagnósticos de instalações elétricas.")

elif page=="Base de conhecimento":
    st.title("De onde vêm as orientações?")
    st.write("Notas breves escritas para este projeto, fundamentadas em fontes públicas. Os documentos originais permanecem nos sites dos autores.")
    sources,error=api("GET","/fontes")
    chunks,err2=api("GET","/trechos")
    if error or err2: st.info(error or err2)
    else:
        a,b,c=st.columns(3)
        a.metric("Notas com fonte",len(chunks)); b.metric("Páginas de referência",len(sources)); c.metric("Consulta das fontes","06 nov 2026")
        entities=["Todas"]+sorted({s["entidade"] for s in sources})
        entity=st.selectbox("Filtrar instituição",entities)
        for source in sources:
            if entity!="Todas" and source["entidade"]!=entity: continue
            selected=[c for c in chunks if c["fonte_id"]==source["id"]]
            with st.expander(f"{source['entidade']} · {source['titulo']} · {len(selected)} notas"):
                st.markdown(f"[Abrir publicação original]({source['url']})")
                st.caption(source["licenca_original"])
                for chunk in selected:
                    st.markdown("**"+chunk["id"]+" · "+chunk["titulo"]+"**")
                    st.write(chunk["texto"])

elif page=="Resultados":
    st.title("O que mudou com a especialização?")
    st.write("Resultados reais do mesmo teste nas três configurações. Consulte o relatório para os critérios, erros e limites da avaliação.")
    data,error=api("GET","/resultados")
    if error: st.info(error)
    else:
        score=pd.DataFrame(data["placar"])
        labels={"sem_contexto":"Sem contexto","rag":"RAG simples","lora_rag":"RAG + LoRA"}
        score["Modelo"]=score["configuracao"].map(labels)
        a,b,c=st.columns(3)
        a.metric("Perguntas do teste",data["dados"]["teste"])
        b.metric("Exemplos de treino",data["dados"]["treino"])
        c.metric("Épocas executadas",len(data["treinamento"]["epocas"]))
        reviewed=pd.DataFrame(data.get("revisao") or [])
        if not reviewed.empty:
            reviewed["Modelo"]=reviewed["configuracao"].map(labels)
            plotted=reviewed.melt(id_vars="Modelo",value_vars=["acerto_total_revisado_pct","acerto_completo_revisado_pct","acerto_factual_revisado_pct"],var_name="Métrica",value_name="Percentual")
            plotted["Métrica"]=plotted["Métrica"].map({"acerto_total_revisado_pct":"Acerto total revisado","acerto_completo_revisado_pct":"Acerto completo revisado","acerto_factual_revisado_pct":"Acerto factual nas respondíveis"})
            st.info("A revisão semântica encontrou falsos positivos e negativos no corretor por palavras. O gráfico usa a revisão assistida por IA, sem alegar avaliação humana independente. LoRA melhorou o formato, mas piorou o conteúdo em relação ao RAG simples.")
        else:
            plotted=score.melt(id_vars="Modelo",value_vars=["acerto_conteudo_pct","acerto_completo_pct","alucinacao_operacional_pct"],var_name="Métrica",value_name="Percentual")
        fig=px.bar(plotted,x="Modelo",y="Percentual",color="Métrica",barmode="group",range_y=[0,105],
                   color_discrete_sequence=["#297D59","#A1C766","#C87961"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend_title_text="",margin=dict(t=15,l=0,r=0,b=0))
        st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
        columns={"Modelo":"Modelo","recall_1":"Recall@1","recall_3":"Recall@3","json_modelo_valido_pct":"JSON da LLM · %","latencia_media_s":"Latência média · s"}
        st.dataframe(score[list(columns)].rename(columns=columns),hide_index=True,width="stretch")
        if not reviewed.empty:
            st.dataframe(reviewed[["Modelo","acertos_fatuais","recusas_corretas"]].rename(columns={"acertos_fatuais":"Fatos corretos · de 40","recusas_corretas":"Recusas corretas · de 20"}),hide_index=True,width="stretch")
        with st.expander("Corretor automático inicial e seus limites"):
            st.dataframe(score,hide_index=True,width="stretch")
            st.caption("O indicador automático de erro factual não deve ser confundido com uma taxa semântica comprovada de alucinação. O placar original foi preservado para auditoria.")
        st.info("As 40 perguntas respondíveis são quatro formulações de 10 fatos; não são 40 fatos independentes. Há também 20 perguntas sem resposta na base. O corretor é operacional e tem limites semânticos documentados.")
        st.caption("JSON da LLM mede apenas chamadas ao modelo. A API também valida o formato e pode recusar ou devolver erro. Os efeitos dessas verificações não são atribuídos ao treinamento.")
        with st.expander("Treinamento e calibração"):
            st.write("Seleção do checkpoint pela perda na validação. Limiar escolhido antes do teste.")
            st.json({"epocas":data["treinamento"]["epocas"],"melhor_epoca":data["treinamento"]["melhor_epoca"],"calibracao":data["calibracao"]})

st.markdown('<div class="footer">ENERGIA CLARA · Demonstração acadêmica local · Dados fictícios na simulação · Orientações educativas com fontes</div>',unsafe_allow_html=True)
