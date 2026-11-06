from threading import Lock
from energia_clara.config import ROOT, read_json
from energia_clara.llm import Generator
from energia_clara.retrieval import Retriever
from energia_clara.evaluation import serve_output
import time


class BusyError(RuntimeError): pass


class AssistantService:
    def __init__(self):
        self.retriever=None
        self.generators={}
        self.lock=Lock()

    def search(self,question):
        if self.retriever is None: self.retriever=Retriever()
        return self.retriever.search(question)

    def evidence(self,question):
        """Consulta documental: mostra notas relacionadas, sem sintetizar fatos pela LLM."""
        if not self.lock.acquire(timeout=0.1): raise BusyError("O assistente está ocupado.")
        try:
            started=time.perf_counter()
            if self.retriever is None: self.retriever=Retriever()
            context=self.retriever.search(question,threshold=self.retriever.threshold)
            return {"status":"fontes_encontradas" if context else "nao_consta",
                    "resposta":"Encontrei estas orientações relacionadas na base. Elas não determinam valores ou condições da sua casa." if context else "Não consta na base de conhecimento.",
                    "fontes":[c["id"] for c in context],"evidencias":context,"origem":"consulta_documental",
                    "modelo_chamado":False,"tempo_s":round(time.perf_counter()-started,3)}
        finally: self.lock.release()

    def answer(self,question,mode):
        if not self.lock.acquire(timeout=0.1): raise BusyError("O assistente está respondendo outra pergunta.")
        try:
            started=time.perf_counter(); context=[]
            if mode!="sem_contexto":
                if self.retriever is None: self.retriever=Retriever()
                context=self.retriever.search(question,threshold=self.retriever.threshold)
                if not context:
                    return {"status":"nao_consta","resposta":"Não consta na base de conhecimento.","fontes":[],
                            "configuracao":mode,"origem":"limiar_busca","modelo_chamado":False,
                            "tempo_s":round(time.perf_counter()-started,3),"evidencias":[]}
            key="adaptado" if mode=="lora_rag" else "original"
            if key not in self.generators: self.generators[key]=Generator(adapted=key=="adaptado")
            output=self.generators[key].generate(question,context)
            served,valid,error=serve_output(output["bruto"],context,grounded=mode!="sem_contexto")
            lookup={c["id"]:c for c in context}
            return {**served,"configuracao":mode,"origem":"modelo","modelo_chamado":True,"json_modelo_valido":valid,
                    "erro_verificacao":error,"tempo_s":round(time.perf_counter()-started,3),
                    "evidencias":[lookup[i] for i in served["fontes"]]}
        finally:
            self.lock.release()
