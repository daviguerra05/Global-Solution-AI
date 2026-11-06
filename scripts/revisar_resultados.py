"""Anota a revisão assistida das saídas, preservando o placar automático original.

Critério: fato essencial correto na resposta; não creditar eco da pergunta, tautologia
ou operação/unidade errada. Contrato JSON e citação são dimensões separadas.
Esta revisão foi feita depois do teste e não alterou dados, pesos ou prompts.
"""
from energia_clara.config import ROOT,read_jsonl,write_json
import hashlib

# Decisões da inspeção semântica registrada: não são extraídas das respostas esperadas pelo programa.
FACTUAL_OK={
 "sem_contexto":set(),
 "rag":set('T-E012-3 T-E012-1 T-E002-4 T-E014-2 T-E018-2 T-E014-1 T-E013-1 T-E018-4 T-E013-4 T-E014-4 T-E015-2 T-E011-2 T-E015-3 T-E019-4 T-E019-1 T-E011-4 T-E013-2 T-E001-3 T-E011-3 T-E019-2'.split()),
 "lora_rag":{"T-E012-1"},
}
REVIEW_NOTES={
 ("sem_contexto","T-E019-3"):"Repete a pergunta. A palavra ensaboamento do próprio enunciado causou falso positivo automático.",
 ("sem_contexto","T-E019-1"):"Repete a pergunta. A palavra reduz do próprio enunciado causou falso positivo automático.",
 ("rag","T-E003-3"):"Atribui 1000 kWh à potência e define potência como quantidade de energia, confundindo unidades.",
 ("rag","T-E003-4"):"Confunde potência e energia; a presença das palavras não prova a relação correta.",
 ("lora_rag","T-E002-4"):"Diz dividir o tempo em horas por 60. O correto é dividir minutos por 60.",
 ("lora_rag","T-E003-3"):"Mistura potência com kWh antes de mencionar W; resposta ambígua e incoerente, sem definição confiável.",
 ("lora_rag","T-E003-4"):"Afirma que potência é uma estimativa em kWh, relação incorreta.",
 ("lora_rag","T-E019-3"):"Mistura fechamento da água com ciclos e roupas; não é uma orientação coerente e fiel à pergunta.",
 ("lora_rag","T-E019-4"):"Reformula a pergunta sem fornecer um hábito concreto de redução do tempo.",
 ("lora_rag","T-E019-2"):"Mistura banho, espera e roupas; a presença de palavras não torna a resposta adequada.",
 ("lora_rag","T-E012-1"):"Apesar do ruído inicial, informa corretamente consumo em kWh por mês e cita E012.",
 ("lora_rag","T-NC-19"):"O texto recusa, mas o status diz respondido e cita fonte. Acerto de conteúdo de recusa, falha no contrato semântico.",
}

EXPECTED_SHA={"sem_contexto":"2d0502844df3c7a23996c3e6e75f7a4580d6495692de10a31bd7885ad4218e09",
              "rag":"1688e5bda733ad5dfcab84c8555035260da08786c32128c82dbfb4b68062a25f",
              "lora_rag":"4f512919197d6e7a882b47661779fe10799e9a74a1cb66787f049721e8456a52"}


def main():
    reviews=[]; summaries=[]
    for mode in FACTUAL_OK:
        path=ROOT/"avaliacao"/f"resultados_{mode}.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED_SHA[mode]:
            raise SystemExit("Esta anotação pertence às saídas publicadas. Uma nova execução exige nova revisão semântica, sem reutilizar decisões antigas.")
        rows=read_jsonl(path); factual=refusal=complete=0
        for r in rows:
            known=r["tipo"]!="nao_consta"
            if known:
                ok=r["id"] in FACTUAL_OK[mode]
            else:
                # Oito recusas por busca e duas recusas explícitas da LLM; um texto de recusa com status incoerente.
                ok=r["origem"]=="limiar_busca" or (mode=="lora_rag" and r["id"] in ["T-NC-06","T-NC-14","T-NC-19"])
            factual+=int(known and ok); refusal+=int(not known and ok)
            served=r["resposta_pipeline"]
            usable=bool(ok and served["status"]!="erro" and
                         (served["status"]=="nao_consta" if not known else
                          (mode=="sem_contexto" or bool(set(r["trechos_relevantes"])&set(served["fontes"])))))
            complete+=int(usable)
            default=("Fato essencial presente no texto, independentemente da falha de formato/citação." if known and ok else
                     "Eco, informação incorreta/irrelevante ou resposta incompleta em relação ao fato exigido." if known else
                     "Recusa apropriada." if ok else "Não reconhece explicitamente que a informação solicitada está ausente.")
            reviews.append({"configuracao":mode,"id":r["id"],"correto_revisao":ok,"acerto_completo_revisao":usable,
                            "nota":REVIEW_NOTES.get((mode,r["id"]),default)})
        n_known=sum(r["tipo"]!="nao_consta" for r in rows)
        n_unknown=len(rows)-n_known
        summaries.append({"configuracao":mode,"acertos_fatuais":factual,"respondiveis":n_known,
                          "recusas_corretas":refusal,"nao_consta":n_unknown,"acerto_total_revisado_pct":round(100*(factual+refusal)/len(rows),2),
                          "acerto_factual_revisado_pct":round(100*factual/n_known,2),"acerto_completo_revisado_pct":round(100*complete/len(rows),2),
                          "saida_sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    write_json(ROOT/"avaliacao"/"revisao_semantica.json",{"metodo":"Revisão assistida por IA das saídas contra os fatos e a pergunta; não é avaliação humana independente. Pós-teste, sem alterar a execução.",
              "criterio":"Presença do fato essencial correto; eco, tautologia, ambiguidade de unidade/operação e mistura incoerente não recebem crédito.","decisoes":reviews})
    write_json(ROOT/"avaliacao"/"placar_revisado.json",summaries)
    print(summaries)


if __name__=="__main__": main()
