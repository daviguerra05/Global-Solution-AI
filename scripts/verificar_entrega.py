"""Confere a integridade da entrega sem repetir treinamento ou alterar avaliações."""
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from energia_clara.config import ROOT, BASE_MODEL, SYSTEM, read_json, read_jsonl, write_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--somente-artefatos",action="store_true",help="Confere arquivos sem certificar execução dos testes funcionais.")
    args=parser.parse_args()
    manifest=read_json(ROOT/"avaliacao/manifesto_dados.json")
    history=read_json(ROOT/"avaliacao/historico_treino.json")
    environment=read_json(ROOT/"avaliacao/ambiente.json")
    assert digest(ROOT/"avaliacao/teste.jsonl")==manifest["teste_sha256"]==history["teste_sha256"]
    assert digest(ROOT/"avaliacao/treino.jsonl")==history["treino_sha256"]
    adapter=digest(ROOT/"modelos/adaptador/adapter_model.safetensors")
    assert adapter==history["adaptador_sha256"]==read_json(ROOT/"modelos/adaptador/proveniencia.json")["adaptador_sha256"]
    assert history["revisao"]==read_json(ROOT/"modelos/revisoes.json")[BASE_MODEL]["revision"]
    assert hashlib.sha256(SYSTEM.encode()).hexdigest()==environment["sistema_prompt_sha256"]
    for filename,key in [("evaluation.py.txt","corretor_sha256"),("treinar_lora.py.txt","treinador_sha256")]:
        assert digest(ROOT/"avaliacao/protocolo_executado"/filename)==environment[key]
    outputs={}
    summaries=read_json(ROOT/"avaliacao/placar_revisado.json")
    for summary in summaries:
        mode=summary["configuracao"]
        path=ROOT/"avaliacao"/f"resultados_{mode}.jsonl"
        assert digest(path)==summary["saida_sha256"]
        outputs[mode]=read_jsonl(path)
        assert len(outputs[mode])==manifest["teste"]
        assert len({r["id"] for r in outputs[mode]})==manifest["teste"]
        assert {r["id"] for r in outputs[mode]}=={r["id"] for r in read_jsonl(ROOT/"avaliacao/teste.jsonl")}
    assert len(outputs)==3
    for b,c in zip(outputs["rag"],outputs["lora_rag"]):
        assert b["id"]==c["id"] and b["trechos"]==c["trechos"]
    annotations=read_json(ROOT/"avaliacao/revisao_semantica.json")["decisoes"]
    assert len(annotations)==3*manifest["teste"]
    assert {(r["configuracao"],r["id"]) for r in annotations}=={(m,r["id"]) for m,rows in outputs.items() for r in rows}
    cases=read_json(ROOT/"avaliacao/cinco_erros.json")
    assert len(cases)==5
    for case in cases:
        original=next(r for r in outputs[case["configuracao"]] if r["id"]==case["id"])
        assert case["saida_bruta"]==original["saida_bruta"]
    notebooks=[]
    for row in read_json(ROOT/"avaliacao/notebooks_executados.json"):
        path=ROOT/"notebooks"/row["notebook"]
        nb=json.loads(path.read_text(encoding="utf-8"))
        cells=[c for c in nb["cells"] if c["cell_type"]=="code"]
        assert row["executado"] and all(c["execution_count"] is not None for c in cells)
        assert len(cells)==row["celulas_codigo"]
        assert all(o["output_type"]!="error" for c in cells for o in c["outputs"])
        notebooks.append({"arquivo":row["notebook"],"celulas_executadas":len(cells),"sha256":digest(path)})
    assert len(notebooks)==3
    suite=ET.parse(ROOT/"avaliacao/testes.xml").getroot().find("testsuite")
    tests_ok=(int(suite.attrib["tests"])>0 and suite.attrib["errors"]==suite.attrib["failures"]==suite.attrib.get("skipped","0")=="0")
    demo=read_json(ROOT/"avaliacao/demonstracao_api.json")
    assert demo["ingestao_registros"]==8 and demo["simulacao"]["consumo_total_kwh"]==229.84
    assert demo["geracao_experimental"]["modelo_chamado"] is True
    assert demo["consulta_base"]["modelo_chamado"] is False
    for filename in ["README.md","RELATORIO.md"]:
        text=(ROOT/filename).read_text(encoding="utf-8")
        assert "@@" not in text and "revisão" in text.lower()
    assert (ROOT/"relatorio/capturas/painel.jpg").stat().st_size>1000
    result={"verificado_em_utc":datetime.now(timezone.utc).isoformat(),"resultado":"Artefatos íntegros; não certifica qualidade factual da geração." if tests_ok else "Artefatos íntegros; validação funcional pendente: consulte avaliacao/testes.xml e docs/AUDITORIA_ENTREGA.md.",
            "validacao_funcional_aprovada":tests_ok,"testes_aprovados":int(suite.attrib["tests"]) if tests_ok else 0,"notebooks":notebooks,
            "saidas_por_configuracao":{m:len(r) for m,r in outputs.items()},"erros_documentados":len(cases),
            "contextos_b_c_identicos":True,"adapter_sha256":adapter,"teste_sha256":manifest["teste_sha256"]}
    write_json(ROOT/"avaliacao/verificacao_entrega.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not tests_ok and not args.somente_artefatos:
        raise SystemExit("Entrega ainda não aprovada: a execução atual dos testes falhou ou está incompleta.")


if __name__=="__main__": main()
