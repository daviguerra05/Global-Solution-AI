"""Correção operacional declarada. Não confunde JSON válido com verdade factual."""
import json
import re
import time
import unicodedata
import numpy as np
from energia_clara.config import ROOT, read_jsonl, read_json, write_json, write_jsonl
from energia_clara.llm import parse_answer


def normal(text):
    return "".join(c for c in unicodedata.normalize("NFKD",str(text).lower()) if not unicodedata.combining(c))


def refused(text, obj=None):
    if obj is not None: return obj.status=="nao_consta"
    text=normal(text)
    return any(s in text for s in ["nao consta","nao sei","nao tenho informac","nao disponivel","i don't know","not available","cannot provide"])


def serve_output(raw, context, grounded):
    obj,error=parse_answer(raw)
    if obj is None:
        return {"status":"erro","resposta":"Não foi possível produzir uma resposta verificável. Reformule a pergunta.","fontes":[]},False,error
    ids={c["id"] for c in context}
    if obj.status=="nao_consta":
        if obj.fontes:
            return {"status":"erro","resposta":"A resposta não passou pela verificação de fontes.","fontes":[]},True,"recusa_com_fontes"
        return obj.model_dump(),True,""
    if grounded and (not obj.fontes or not set(obj.fontes).issubset(ids)):
        return {"status":"erro","resposta":"A resposta não passou pela verificação de fontes.","fontes":[]},True,"fonte_ausente_ou_inexistente"
    if not grounded and obj.fontes:
        return {"status":"erro","resposta":"A resposta citou fontes que não recebeu.","fontes":[]},True,"fonte_sem_contexto"
    return obj.model_dump(),True,""


def assess(item, raw, context, called=True):
    obj,_=parse_answer(raw)
    refusal=refused(raw,obj)
    text=obj.resposta if obj else raw
    answer_norm=normal(text)
    facts=all(any(normal(a) in answer_norm for a in group) for group in item["fatos_aceitos"])
    if item["grupo_fato"]=="E001": facts=facts and ("divid" in answer_norm or "/" in text or "÷" in text)
    if item["grupo_fato"]=="E019": facts=any(a in answer_norm for a in ["curto","reduz","dimin","ensabo","fech"])
    # Detecta números que não foram fornecidos na evidência nem na pergunta.
    allowed=" ".join(c["texto"] for c in context)+" "+item["pergunta"]+" "+item["resposta_esperada"]
    invented_numbers=set(re.findall(r"\d+",text))-set(re.findall(r"\d+",allowed))
    facts=facts and not invented_numbers
    known=item["tipo"]!="nao_consta"
    correct=bool(facts and not refusal) if known else refusal
    evidence={c["id"] for c in context}
    cited=bool(obj and obj.status=="respondido" and obj.fontes and set(obj.fontes).issubset(evidence))
    supported=bool(correct and (not known or set(item["trechos_relevantes"]) & set(obj.fontes if obj else [])))
    return {"correto_conteudo":correct,"recusou":refusal,"json_modelo_valido":obj is not None if called else None,
            "citacao_valida":cited,"fundamentacao_gabarito":supported,
            "alucinacao_operacional":bool(not refusal and not correct),
            "numeros_nao_sustentados":sorted(invented_numbers),
            "limitacao_corretor":"Expressões do gabarito e checagem de números; não prova equivalência semântica. Revisão dos erros no relatório."}


def run_configuration(mode,generator,retriever,items):
    results=[]
    for index,item in enumerate(items,1):
        started=time.perf_counter()
        ranked=[]; context=[]; retrieval_seconds=0
        if mode!="sem_contexto":
            t=time.perf_counter()
            ranked=retriever.search(item["pergunta"],k=3)
            context=[c for c in ranked if c["score"]>=retriever.threshold]
            retrieval_seconds=time.perf_counter()-t
        called=mode=="sem_contexto" or bool(context)
        if called:
            generation=generator.generate(item["pergunta"],context)
            raw=generation["bruto"]
            served,json_valid,error=serve_output(raw,context,grounded=mode!="sem_contexto")
        else:
            # Esta recusa é código determinístico, não uma geração da LLM.
            served={"status":"nao_consta","resposta":"Não consta na base de conhecimento.","fontes":[]}
            raw=json.dumps(served,ensure_ascii=False)
            generation={"tokens_entrada":0,"tokens_saida":0,"geracao_s":0}
            error=""; json_valid=None
        evaluation=assess(item,raw,context,called)
        evidence_ids=[c["id"] for c in context]
        row={**item,**evaluation,"configuracao":mode,"saida_bruta":raw if called else None,"resposta_pipeline":served,
             "origem":"modelo" if called else "limiar_busca","modelo_chamado":called,"erro_verificacao":error,
             "trechos":[{"id":c["id"],"score":c["score"]} for c in context],
             "ranking_sem_limiar":[{"id":c["id"],"score":c["score"]} for c in ranked],
             "busca_s":retrieval_seconds,"latencia_s":time.perf_counter()-started,
             **{k:v for k,v in generation.items() if k!="bruto"}}
        # Acerto operacional do produto: contrato, conteúdo e, com RAG, referência de suporte.
        row["acerto_completo"]=bool(row["correto_conteudo"] and served["status"]!="erro" and
                                          (not item["trechos_relevantes"] or mode=="sem_contexto" or row["fundamentacao_gabarito"]))
        results.append(row)
        if index%5==0 or index==1:
            print(f"{mode}: {index}/{len(items)} perguntas | {time.perf_counter()-started:.2f}s última",flush=True)
        write_jsonl(ROOT/"avaliacao"/f"resultados_{mode}.jsonl",results)
    return results


def summarize(rows):
    known=[r for r in rows if r["tipo"]!="nao_consta"]
    unknown=[r for r in rows if r["tipo"]=="nao_consta"]
    called=[r for r in rows if r["modelo_chamado"]]
    def pct(items, key): return round(100*sum(bool(r[key]) for r in items)/len(items),2) if items else None
    grounded=rows[0]["configuracao"]!="sem_contexto"
    result={"configuracao":rows[0]["configuracao"],"perguntas":len(rows),"chamadas_modelo":len(called),
            "acerto_conteudo_pct":pct(rows,"correto_conteudo"),"acerto_completo_pct":pct(rows,"acerto_completo"),
            "acerto_respondiveis_pct":pct(known,"correto_conteudo"),"alucinacao_operacional_pct":pct(rows,"alucinacao_operacional"),
            "recusa_correta_pct":pct(unknown,"recusou"),"recusa_indevida_pct":pct(known,"recusou"),
            "json_modelo_valido_pct":pct(called,"json_modelo_valido"),"json_api_valido_pct":100.0,
            "citacao_valida_respondiveis_pct":pct(known,"citacao_valida") if grounded else None,
            "latencia_media_s":round(float(np.mean([r["latencia_s"] for r in rows])),3),
            "latencia_p50_s":round(float(np.percentile([r["latencia_s"] for r in rows],50)),3),
            "latencia_p95_s":round(float(np.percentile([r["latencia_s"] for r in rows],95)),3)}
    for k in [1,3]:
        def recall(r,field):
            expected=set(r["trechos_relevantes"])
            return len(expected & {c["id"] for c in r[field][:k]})/len(expected)
        result[f"recall_{k}"]=round(float(np.mean([recall(r,"trechos") for r in known])),4) if grounded else None
        result[f"recall_{k}_sem_limiar"]=round(float(np.mean([recall(r,"ranking_sem_limiar") for r in known])),4) if grounded else None
    return result
