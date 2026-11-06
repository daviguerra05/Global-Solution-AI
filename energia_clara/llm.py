import json
import time
from energia_clara.config import MODEL_DIR, ADAPTER_DIR, SYSTEM, THREADS, MAX_NEW_TOKENS, MAX_INPUT_TOKENS
from energia_clara.retrieval import context_text
from energia_clara.schemas import ModelAnswer


def user_message(question, chunks=None):
    if chunks:
        return "CONTEXTO:\n" + context_text(chunks) + "\n\nPERGUNTA: " + question
    return "PERGUNTA: " + question


def messages(question, chunks=None):
    return [{"role":"system","content":SYSTEM},{"role":"user","content":user_message(question,chunks)}]


def parse_answer(raw):
    """Não conserta texto ou extrai um JSON escondido em prosa: mede o contrato real."""
    try:
        value=json.loads(raw)
        return ModelAnswer.model_validate(value), ""
    except Exception as exc:
        return None, type(exc).__name__


class Generator:
    def __init__(self, adapted=False):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        torch.set_num_threads(THREADS)
        if not (MODEL_DIR/"config.json").exists():
            raise FileNotFoundError("Modelo local ausente. Execute python -m scripts.baixar_recursos.")
        self.tokenizer=AutoTokenizer.from_pretrained(MODEL_DIR,local_files_only=True)
        self.tokenizer.pad_token=self.tokenizer.eos_token
        self.model=AutoModelForCausalLM.from_pretrained(MODEL_DIR,local_files_only=True,torch_dtype=torch.float32,attn_implementation="sdpa")
        if adapted:
            if not (ADAPTER_DIR/"adapter_config.json").exists():
                raise FileNotFoundError("Adaptador ainda não treinado. Execute python -m scripts.treinar_lora.")
            from peft import PeftModel
            self.model=PeftModel.from_pretrained(self.model,ADAPTER_DIR,local_files_only=True).merge_and_unload()
        self.model.eval()
        self.model.config.use_cache=True

    def generate(self,question,chunks=None):
        import torch
        text=self.tokenizer.apply_chat_template(messages(question,chunks),tokenize=False,add_generation_prompt=True)
        enc=self.tokenizer(text,return_tensors="pt",add_special_tokens=False)
        if enc["input_ids"].shape[1]>MAX_INPUT_TOKENS:
            raise ValueError("Pergunta e contexto excedem o limite de entrada. Reduza a pergunta.")
        started=time.perf_counter()
        with torch.inference_mode():
            out=self.model.generate(**enc,max_new_tokens=MAX_NEW_TOKENS,do_sample=False,
                                    pad_token_id=self.tokenizer.pad_token_id,eos_token_id=self.tokenizer.eos_token_id)
        new=out[0,enc["input_ids"].shape[1]:]
        return {"bruto":self.tokenizer.decode(new,skip_special_tokens=True).strip(),
                "tokens_entrada":int(enc["input_ids"].shape[1]),"tokens_saida":int(len(new)),"geracao_s":time.perf_counter()-started}
