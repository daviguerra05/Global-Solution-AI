from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import JSONResponse
from energia_clara.config import ROOT, MODEL_DIR, ADAPTER_DIR, ENCODER_DIR, BASE_MODEL, read_json, read_jsonl
from energia_clara.schemas import Question, Simulation
from energia_clara.consumption import parse_csv, simulate

app=FastAPI(title="Energia Clara",version="1.0.0",description="Simulação residencial e IA local com fontes. Sem integração com concessionárias.")

# Carga da LLM é adiada até a primeira pergunta. Simulação e saúde não carregam os modelos.
_assistant=None


def assistant():
    global _assistant
    if _assistant is None:
        from energia_clara.service import AssistantService
        _assistant=AssistantService()
    return _assistant


@app.middleware("http")
async def body_limit(request:Request,call_next):
    try: size=int(request.headers.get("content-length","0"))
    except ValueError: return JSONResponse(status_code=400,content={"detail":"Tamanho de requisição inválido."})
    if size>150_000: return JSONResponse(status_code=413,content={"detail":"Requisição maior que 150 KB."})
    return await call_next(request)


@app.get("/saude")
def health():
    return {"status":"ok","modelo":BASE_MODEL,"modelo_local":(MODEL_DIR/"config.json").exists(),
            "encoder_local":(ENCODER_DIR/"config.json").exists(),"adaptador_treinado":(ADAPTER_DIR/"adapter_model.safetensors").exists(),
            "avaliacao_concluida":(ROOT/"avaliacao"/"placar.json").exists(),"persistencia_perguntas":False,"servico":"local"}


@app.post("/simular")
def simulation(body:Simulation): return simulate(body)


@app.post("/ingerir-consumo")
async def ingest(arquivo:UploadFile=File(...)):
    content=await arquivo.read(100_001)
    try: records=parse_csv(content)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc))
    return {"status":"validado","registros":len(records),"dados":records,"persistido":False}


@app.post("/perguntar")
def ask(body:Question):
    from energia_clara.service import BusyError
    try: return assistant().answer(body.pergunta,body.configuracao)
    except BusyError: raise HTTPException(status_code=503,detail="O assistente está ocupado. Aguarde a resposta atual.")
    except FileNotFoundError: raise HTTPException(status_code=503,detail="O modelo local ou o treinamento ainda não está disponível. Consulte as instruções de preparação.")
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc))
    except Exception: raise HTTPException(status_code=503,detail="O assistente local não conseguiu concluir a resposta.")


@app.post("/consultar-base")
def consult(body:Question):
    from energia_clara.service import BusyError
    try: return assistant().evidence(body.pergunta)
    except BusyError: raise HTTPException(status_code=503,detail="O assistente está ocupado. Aguarde a consulta atual.")
    except (FileNotFoundError,ValueError): raise HTTPException(status_code=503,detail="A base de conhecimento local precisa ser preparada.")


@app.get("/fontes")
def sources(): return read_json(ROOT/"base"/"fontes.json",[])


@app.get("/trechos")
def chunks(): return read_jsonl(ROOT/"base"/"trechos.jsonl")


@app.get("/buscar")
def search(pergunta:str=Query(min_length=3,max_length=800)):
    service=assistant()
    if not service.lock.acquire(timeout=0.1): raise HTTPException(status_code=503,detail="O serviço está ocupado.")
    try:
        rows=service.search(pergunta)
        return {"trechos":rows,"limiar":service.retriever.threshold}
    except FileNotFoundError: raise HTTPException(status_code=503,detail="Prepare o índice e o encoder antes da busca.")
    finally: service.lock.release()


@app.get("/resultados")
def results():
    score=read_json(ROOT/"avaliacao"/"placar.json")
    if score is None: raise HTTPException(status_code=404,detail="O experimento ainda não foi concluído.")
    return {"placar":score,"dados":read_json(ROOT/"avaliacao"/"manifesto_dados.json"),
            "revisao":read_json(ROOT/"avaliacao"/"placar_revisado.json"),
            "calibracao":{k:v for k,v in read_json(ROOT/"avaliacao"/"calibracao.json").items() if k not in ["detalhes","curva"]},
            "treinamento":{k:v for k,v in read_json(ROOT/"avaliacao"/"historico_treino.json").items() if k not in ["passos"]}}
