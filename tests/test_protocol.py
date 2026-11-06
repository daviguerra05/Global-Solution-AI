import hashlib
from energia_clara.config import ROOT,read_jsonl,read_json


def test_frozen_test_and_fact_partitions():
    manifest=read_json(ROOT/"avaliacao"/"manifesto_dados.json")
    assert hashlib.sha256((ROOT/"avaliacao"/"teste.jsonl").read_bytes()).hexdigest()==manifest["teste_sha256"]
    parts=[read_jsonl(ROOT/"avaliacao"/(name+".jsonl")) for name in ["treino","validacao","teste"]]
    groups=[{x["grupo_fato"] for x in part if x["tipo"]!="nao_consta"} for part in parts]
    for i in range(3):
        for j in range(i+1,3):
            assert not groups[i]&groups[j]
            assert not {x["pergunta"].lower() for x in parts[i]}&{x["pergunta"].lower() for x in parts[j]}


def test_every_answerable_question_has_an_actual_evidence_note():
    ids={c["id"] for c in read_jsonl(ROOT/"base"/"trechos.jsonl")}
    for name in ["treino","validacao","teste"]:
        for item in read_jsonl(ROOT/"avaliacao"/(name+".jsonl")):
            assert set(item["trechos_relevantes"]).issubset(ids)
            assert bool(item["trechos_relevantes"])==(item["tipo"]!="nao_consta")


def test_calibration_matches_current_corpus_and_validation():
    c=read_json(ROOT/"avaliacao"/"calibracao.json")
    assert c["corpus_sha256"]==hashlib.sha256((ROOT/"base"/"trechos.jsonl").read_bytes()).hexdigest()
    assert c["validacao_sha256"]==hashlib.sha256((ROOT/"avaliacao"/"validacao.jsonl").read_bytes()).hexdigest()
