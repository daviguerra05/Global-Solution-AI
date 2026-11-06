"""Fine-tuning local real, em CPU: máscara da resposta, AdamW e validação por época."""
from energia_clara.config import ROOT, MODEL_DIR, ADAPTER_DIR, BASE_MODEL, SEED, THREADS, read_jsonl, write_json, read_json
from energia_clara.llm import messages
import argparse
import hashlib
import json
import math
import random
import time

CONFIG = {"epocas":4,"lote":2,"acumulacao":2,"learning_rate":0.0003,"rank":8,"alpha":16,
          "dropout":0.05,"max_seq":640,"seed":SEED,"threads":THREADS,"dtype":"float32","device":"cpu"}


def make_examples(items, chunks, seed):
    rng=random.Random(seed)
    train_chunks=[c for c in chunks if c["particao_qa"]=="treino"]
    lookup={c["id"]:c for c in chunks}
    out=[]
    for item in items:
        gold=item.get("trechos_relevantes",[])
        target=[lookup[i] for i in gold]
        distractors=[c for c in train_chunks if c["id"] not in gold]
        context=target+rng.sample(distractors,min(2 if not target else 1,len(distractors)))
        rng.shuffle(context)
        answer=item.get("resposta") or {"status":"nao_consta" if item["tipo"]=="nao_consta" else "respondido",
                   "resposta":item["resposta_esperada"],"fontes":gold}
        out.append({"id":item["id"],"messages":messages(item["pergunta"],context),"resposta":answer,"contexto_ids":[c["id"] for c in context]})
    return out


def train(pilot=False):
    import torch
    import psutil
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType
    torch.set_num_threads(THREADS)
    torch.manual_seed(SEED)
    random.seed(SEED)
    started=time.perf_counter()
    print("Preparando treino LoRA em CPU...",flush=True)
    chunks=read_jsonl(ROOT/"base"/"trechos.jsonl")
    raw_train=read_jsonl(ROOT/"avaliacao"/"treino.jsonl")
    raw_val=read_jsonl(ROOT/"avaliacao"/"validacao.jsonl")
    train_examples=make_examples(raw_train,chunks,SEED)
    val_examples=make_examples(raw_val,chunks,SEED+1)
    tok=AutoTokenizer.from_pretrained(MODEL_DIR,local_files_only=True)
    tok.pad_token=tok.eos_token

    def tokenize(item):
        prompt=tok.apply_chat_template(item["messages"],tokenize=False,add_generation_prompt=True)
        p=tok(prompt,add_special_tokens=False)["input_ids"]
        a=tok(json.dumps(item["resposta"],ensure_ascii=False,separators=(",",":")),add_special_tokens=False)["input_ids"]+[tok.eos_token_id]
        if len(p)+len(a)>CONFIG["max_seq"]:
            raise ValueError(f'Exemplo {item["id"]} excede max_seq: {len(p)+len(a)}')
        return {"ids":p+a,"labels":[-100]*len(p)+a,"n_prompt":len(p),"n_resposta":len(a)}

    train_data=[tokenize(x) for x in train_examples]
    val_data=[tokenize(x) for x in val_examples]
    assert all(all(v==-100 for v in x["labels"][:x["n_prompt"]]) and x["labels"][-1]==tok.eos_token_id for x in train_data)
    model=AutoModelForCausalLM.from_pretrained(MODEL_DIR,local_files_only=True,torch_dtype=torch.float32,attn_implementation="sdpa")
    model.config._name_or_path=BASE_MODEL
    model.config.use_cache=False
    model=get_peft_model(model,LoraConfig(r=CONFIG["rank"],lora_alpha=CONFIG["alpha"],lora_dropout=CONFIG["dropout"],
                          bias="none",task_type=TaskType.CAUSAL_LM,target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]))
    model.peft_config["default"].base_model_name_or_path=BASE_MODEL
    trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
    total=sum(p.numel() for p in model.parameters())
    print(f"Parâmetros treináveis: {trainable:,}/{total:,} ({trainable/total:.2%})",flush=True)
    def batch(examples):
        n=max(len(x["ids"]) for x in examples)
        return {"input_ids":torch.tensor([x["ids"]+[tok.pad_token_id]*(n-len(x["ids"])) for x in examples]),
                "attention_mask":torch.tensor([[1]*len(x["ids"])+[0]*(n-len(x["ids"])) for x in examples]),
                "labels":torch.tensor([x["labels"]+[-100]*(n-len(x["labels"])) for x in examples])}
    def validation():
        model.eval()
        loss_sum=tokens=0
        with torch.no_grad():
            for i in range(0,len(val_data),CONFIG["lote"]):
                b=batch(val_data[i:i+CONFIG["lote"]])
                loss=model(**b).loss
                n=int((b["labels"][:,1:]!=-100).sum())
                loss_sum+=float(loss)*n; tokens+=n
        return loss_sum/tokens
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=CONFIG["learning_rate"],weight_decay=0.01)
    batches=math.ceil(len(train_data)/CONFIG["lote"])
    updates=math.ceil(batches/CONFIG["acumulacao"])*CONFIG["epocas"]
    warmup=max(1,round(updates*0.05))
    schedule=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda s:min((s+1)/warmup,max(0.1,(updates-s)/max(1,updates-warmup))))
    history={"config":CONFIG,"modelo":BASE_MODEL,"revisao":read_json(ROOT/"modelos"/"revisoes.json",{}).get(BASE_MODEL,{}).get("revision"),
             "parametros_treinaveis":trainable,"parametros_totais":total,"treino":len(train_data),"validacao":len(val_data),
             "max_tokens_exemplo":max(len(x["ids"]) for x in train_data+val_data),"mascara_prompt_verificada":True,
             "treino_sha256":hashlib.sha256((ROOT/"avaliacao"/"treino.jsonl").read_bytes()).hexdigest(),
             "teste_sha256":read_json(ROOT/"avaliacao"/"manifesto_dados.json")["teste_sha256"],
             "passos":[],"epocas":[],"pilot":pilot}
    if not pilot:
        initial=validation()
        history["loss_validacao_inicial"]=initial
        print(f"Loss inicial de validação: {initial:.4f}",flush=True)
    best=float("inf"); patience=0; step=0; peak=0
    rng=random.Random(SEED)
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(1,CONFIG["epocas"]+1):
        order=list(train_data); rng.shuffle(order)
        model.train(); sum_loss=0.; count_tokens=0
        for i in range(batches):
            b=batch(order[i*CONFIG["lote"]:(i+1)*CONFIG["lote"]])
            t0=time.perf_counter()
            loss=model(**b).loss
            if not torch.isfinite(loss): raise RuntimeError("Loss não finita.")
            n=int((b["labels"][:,1:]!=-100).sum())
            (loss/CONFIG["acumulacao"]).backward()
            if (i+1)%CONFIG["acumulacao"]==0 or i+1==batches:
                torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
                optimizer.step(); schedule.step(); optimizer.zero_grad(set_to_none=True)
            step+=1
            sum_loss+=float(loss.detach())*n; count_tokens+=n
            rss=psutil.Process().memory_info().rss/1024**3; peak=max(peak,rss)
            row={"epoca":epoch,"lote":i+1,"passo":step,"loss":float(loss.detach()),"segundos":time.perf_counter()-t0,"ram_processo_gb":rss}
            history["passos"].append(row)
            if step<=3 or step%10==0:
                print(f"Época {epoch}/{CONFIG['epocas']} | lote {i+1}/{batches} | loss {row['loss']:.4f} | {row['segundos']:.2f}s | RAM {rss:.2f}GB",flush=True)
            if pilot and step==3:
                history.update(duracao_s=time.perf_counter()-started,ram_pico_gb=peak,
                               estimativa_treino_s=sum(x["segundos"] for x in history["passos"])/step*batches*CONFIG["epocas"])
                write_json(ROOT/"avaliacao"/"piloto_cpu.json",history)
                print("Piloto concluído. Estimativa de treino:",round(history["estimativa_treino_s"]/60,1),"minutos",flush=True)
                return history
        v=validation(); row={"epoca":epoch,"loss_treino":sum_loss/count_tokens,"loss_validacao":v}
        history["epocas"].append(row)
        if v<best:
            best=v; patience=0
            ADAPTER_DIR.mkdir(parents=True,exist_ok=True)
            model.save_pretrained(ADAPTER_DIR,safe_serialization=True,save_embedding_layers=False)
            history.update(melhor_epoca=epoch,melhor_loss_validacao=v)
        else: patience+=1
        history.update(duracao_s=time.perf_counter()-started,ram_pico_gb=peak)
        write_json(ROOT/"avaliacao"/"historico_treino.json",history)
        print(f"Fim da época {epoch}: treino={row['loss_treino']:.4f} | validação={v:.4f} | melhor={best:.4f}",flush=True)
        if patience>=2:
            print("Parada antecipada: validação sem melhora em duas épocas.",flush=True); break
    history["adaptador_sha256"]=hashlib.sha256((ADAPTER_DIR/"adapter_model.safetensors").read_bytes()).hexdigest()
    history["adaptador_bytes"]=(ADAPTER_DIR/"adapter_model.safetensors").stat().st_size
    history["duracao_s"]=time.perf_counter()-started
    write_json(ROOT/"avaliacao"/"historico_treino.json",history)
    write_json(ADAPTER_DIR/"proveniencia.json",{k:v for k,v in history.items() if k not in ["passos","epocas"]})
    return history


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--piloto",action="store_true")
    train(p.parse_args().piloto)
