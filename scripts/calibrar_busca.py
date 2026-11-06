import hashlib
import numpy as np
from energia_clara.config import ROOT, TOP_K, read_jsonl, write_json
from energia_clara.retrieval import Retriever


def main():
    retriever=Retriever()
    if retriever.vectors is None:
        retriever.build()
    validation=read_jsonl(ROOT/"avaliacao"/"validacao.jsonl")
    rows=[]
    for item in validation:
        found=retriever.search(item["pergunta"],k=TOP_K)
        rows.append({**item,"recuperados":[{"id":x["id"],"score":x["score"]} for x in found]})
    curve=[]
    for t in np.round(np.arange(0.60,0.961,0.005),3):
        hit, reject=[],[]
        for item in rows:
            ids={r["id"] for r in item["recuperados"] if r["score"]>=t}
            if item["tipo"]=="nao_consta":
                reject.append(not ids)
            else:
                hit.append(len(ids&set(item["trechos_relevantes"]))/len(item["trechos_relevantes"]))
        curve.append(dict(limiar=float(t),recall_3=float(np.mean(hit)),rejeicao_correta=float(np.mean(reject)),
                          equilibrio=float((np.mean(hit)+np.mean(reject))/2)))
    # Empate: maior recall; persistindo, maior rejeição; depois menor limiar.
    best=max(curve,key=lambda x:(x["equilibrio"],x["recall_3"],x["rejeicao_correta"],-x["limiar"]))
    data={**best,"top_k":TOP_K,"corpus_sha256":retriever.digest,
          "validacao_sha256":hashlib.sha256((ROOT/"avaliacao"/"validacao.jsonl").read_bytes()).hexdigest(),
          "criterio":"Média de recall@3 nas respondíveis e rejeição nas não respondíveis, só na validação.",
          "curva":curve,"detalhes":rows}
    write_json(ROOT/"avaliacao"/"calibracao.json",data)
    print("Calibração:",best,flush=True)


if __name__=="__main__": main()
