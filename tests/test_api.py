from fastapi.testclient import TestClient
from api.main import app
from energia_clara.config import ROOT
from energia_clara.consumption import parse_csv

client=TestClient(app)


def test_request_limit_checks_actual_bytes_without_trusting_header():
    for headers in [{"content-length":"1"}, {"transfer-encoding":"chunked"}]:
        response=client.post("/simular",content=iter([b"x"*80_000,b"x"*80_000]),headers=headers)
        assert response.status_code==413
    assert client.post("/simular",content=b"{}",headers={"content-length":"-1"}).status_code==400


def test_changed_corpus_returns_actionable_error(monkeypatch):
    from types import SimpleNamespace
    from threading import Lock
    import api.main as mod
    def changed(question):
        raise ValueError("A base mudou")
    monkeypatch.setattr(mod,"_assistant",SimpleNamespace(lock=Lock(),search=changed))
    assert client.get("/buscar",params={"pergunta":"Como economizar?"}).status_code==503


def test_simulation_is_integrated_over_http():
    records=parse_csv((ROOT/"dados"/"consumo_exemplo.csv").read_bytes())
    r=client.post("/simular",json={"aparelhos":records,"tarifa_kwh":0.95})
    assert r.status_code==200
    assert r.json()["consumo_total_kwh"]==229.84


def test_ingestion_validates_without_persistence():
    r=client.post("/ingerir-consumo",files={"arquivo":("casa.csv",(ROOT/"dados"/"consumo_exemplo.csv").read_bytes(),"text/csv")})
    assert r.status_code==200
    assert r.json()["registros"]==8 and r.json()["persistido"] is False


def test_invalid_upload_and_invalid_question_are_rejected_before_inference():
    assert client.post("/ingerir-consumo",files={"arquivo":("x.csv",b"cpf,nome\n123,Ana\n","text/csv")}).status_code==422
    assert client.post("/perguntar",json={"pergunta":"a","configuracao":"lora_rag"}).status_code==422
    assert client.post("/perguntar",json={"pergunta":"x"*801}).status_code==422
    assert client.post("/perguntar",json={"pergunta":"Como economizar?","configuracao":"inventado"}).status_code==422


def test_public_sources_and_health_do_not_load_llm():
    import api.main as mod
    assert client.get("/saude").json()["persistencia_perguntas"] is False
    assert len(client.get("/fontes").json())==11
    assert len(client.get("/trechos").json())==30
    assert mod._assistant is None


def test_documental_mode_returns_literal_notes_without_loading_generator(monkeypatch):
    from types import SimpleNamespace
    import api.main as mod
    import energia_clara.service as service_module
    note={"id":"E001","titulo":"Cálculo","texto":"Consumo = W × horas ÷ 1000.","url":"https://www.cemig.com.br/"}
    service=service_module.AssistantService()
    service.retriever=SimpleNamespace(search=lambda *a,**k:[note],threshold=0.85)
    monkeypatch.setattr(service_module,"Generator",lambda *a,**k: (_ for _ in ()).throw(AssertionError("Consulta documental não deve carregar a LLM")))
    monkeypatch.setattr(mod,"_assistant",service)
    result=client.post("/consultar-base",json={"pergunta":"Como estimar consumo?"})
    assert result.status_code==200
    assert result.json()["modelo_chamado"] is False
    assert result.json()["evidencias"][0]["texto"]==note["texto"]
