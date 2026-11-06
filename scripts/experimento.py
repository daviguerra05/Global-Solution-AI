"""Executa as comparações e o treinamento real, sem ajustar pelo teste final."""
import argparse
import gc
import hashlib
import platform
import time
from datetime import datetime, timezone
from energia_clara.config import ROOT, BASE_MODEL, SYSTEM, MAX_NEW_TOKENS, SEED, read_json, read_jsonl, write_json


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--continuar",action="store_true")
    args=parser.parse_args()
    from scripts.calibrar_busca import main as calibrate
    from scripts.treinar_lora import train
    from energia_clara.llm import Generator
    from energia_clara.retrieval import Retriever
    from energia_clara.evaluation import run_configuration,summarize
    import torch, psutil, transformers, peft
    started=time.perf_counter()
    items=read_jsonl(ROOT/"avaliacao"/"teste.jsonl")
    manifest=read_json(ROOT/"avaliacao"/"manifesto_dados.json")
    digest=hashlib.sha256((ROOT/"avaliacao"/"teste.jsonl").read_bytes()).hexdigest()
    assert digest==manifest["teste_sha256"],"O teste congelado foi alterado."
    if (ROOT/"avaliacao"/"resultados_lora_rag.jsonl").exists() and not args.continuar:
        raise SystemExit("Resultados já existem. Para nova execução, arquive-os; --continuar retoma etapas incompletas.")
    history=read_json(ROOT/"avaliacao"/"historico_treino.json",{})
    adapter=ROOT/"modelos"/"adaptador"/"adapter_model.safetensors"
    training_complete=(not history.get("pilot",True) and adapter.exists() and
                       history.get("adaptador_sha256")==hashlib.sha256(adapter.read_bytes()).hexdigest())
    if args.continuar and training_complete and (ROOT/"avaliacao"/"placar.json").exists() and all(
        (ROOT/"avaliacao"/f"resultados_{m}.jsonl").exists() and
        len(read_jsonl(ROOT/"avaliacao"/f"resultados_{m}.jsonl"))==len(items)
        for m in ["sem_contexto","rag","lora_rag"]):
        print("O experimento já está completo. Resultados e proveniência preservados.",flush=True)
        return
    print("Calibrando a busca apenas na validação...",flush=True)
    calibrate()
    retriever=Retriever()
    environment={
        "python":platform.python_version(),"sistema":platform.system(),"arquitetura":platform.machine(),
        "torch":torch.__version__,"transformers":transformers.__version__,"peft":peft.__version__,
        "cpu":"Intel Core i7-13620H (informado pelo usuário)","processadores_logicos":psutil.cpu_count(),
        "ram_total_gb":round(psutil.virtual_memory().total/1024**3,2),"cuda":torch.cuda.is_available(),
        "device":"cpu","threads":6,"modelo":BASE_MODEL,"max_new_tokens":MAX_NEW_TOKENS,"seed":SEED,
        "teste_sha256":digest,"sistema_prompt_sha256":hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "corpus_sha256":retriever.digest,"inicio_utc":datetime.now(timezone.utc).isoformat(),
        "corretor_sha256":hashlib.sha256((ROOT/"energia_clara"/"evaluation.py").read_bytes()).hexdigest(),
        "treinador_sha256":hashlib.sha256((ROOT/"scripts"/"treinar_lora.py").read_bytes()).hexdigest(),
        "protocolo":"A e B antes de treinar; hiperparâmetros e dados fixados previamente; C após recarregar o adaptador."}
    if not args.continuar or not (ROOT/"avaliacao"/"ambiente.json").exists():
        write_json(ROOT/"avaliacao"/"ambiente.json",environment)
    base=None
    for mode in ["sem_contexto","rag"]:
        dest=ROOT/"avaliacao"/f"resultados_{mode}.jsonl"
        existing=read_jsonl(dest) if dest.exists() else []
        if args.continuar and len(existing)==len(items):
            print("Etapa já concluída:",mode,flush=True); continue
        if base is None: base=Generator()
        print("Medindo configuração:",mode,flush=True)
        run_configuration(mode,base,retriever,items)
    del base; gc.collect()
    if not (args.continuar and training_complete):
        train()
    gc.collect()
    dest=ROOT/"avaliacao"/"resultados_lora_rag.jsonl"
    existing=read_jsonl(dest) if dest.exists() else []
    if not (args.continuar and len(existing)==len(items)):
        adapted=Generator(adapted=True)
        run_configuration("lora_rag",adapted,retriever,items)
        del adapted; gc.collect()
    all_rows={mode:read_jsonl(ROOT/"avaliacao"/f"resultados_{mode}.jsonl") for mode in ["sem_contexto","rag","lora_rag"]}
    for b,c in zip(all_rows["rag"],all_rows["lora_rag"]):
        assert b["id"]==c["id"] and [x["id"] for x in b["trechos"]]==[x["id"] for x in c["trechos"]],"Contextos de B e C divergiram."
    summaries=[summarize(rows) for rows in all_rows.values()]
    write_json(ROOT/"avaliacao"/"placar.json",summaries)
    write_json(ROOT/"avaliacao"/"conclusao_execucao.json",{"duracao_total_s":time.perf_counter()-started,
               "teste_sha256":digest,"contextos_b_c_identicos":True,"fim_utc":datetime.now(timezone.utc).isoformat()})
    print("Experimento concluído. Placar:",summaries,flush=True)


if __name__=="__main__": main()
