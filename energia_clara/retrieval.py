"""Busca vetorial local exata. O encoder E5 é diferente da LLM geradora."""
import hashlib
import numpy as np
from energia_clara.config import ROOT, ENCODER_DIR, TOP_K, read_jsonl, read_json, write_json


class Retriever:
    def __init__(self):
        self.chunks = read_jsonl(ROOT / "base" / "trechos.jsonl")
        self.encoder = None
        self.path = ROOT / "base" / "indice.npz"
        self.digest = hashlib.sha256((ROOT / "base" / "trechos.jsonl").read_bytes()).hexdigest()
        self.vectors = None
        if self.path.exists():
            with np.load(self.path, allow_pickle=False) as data:
                if str(data["corpus_sha256"]) == self.digest:
                    self.vectors = data["vetores"]

    def load_encoder(self):
        if self.encoder is None:
            import torch
            from sentence_transformers import SentenceTransformer
            from energia_clara.config import THREADS
            torch.set_num_threads(THREADS)
            if not (ENCODER_DIR / "config.json").exists():
                raise FileNotFoundError("Encoder ausente. Execute python -m scripts.baixar_recursos.")
            self.encoder = SentenceTransformer(str(ENCODER_DIR), device="cpu", local_files_only=True)
        return self.encoder

    def build(self):
        encoder = self.load_encoder()
        texts = ["passage: " + c["titulo"] + ". " + c["texto"] for c in self.chunks]
        lengths = [len(encoder.tokenizer(t)["input_ids"]) for t in texts]
        if max(lengths) > 512:
            raise ValueError("Trecho excede a janela do encoder E5.")
        self.vectors = encoder.encode(texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False).astype("float32")
        np.savez_compressed(self.path, vetores=self.vectors, corpus_sha256=np.array(self.digest))
        write_json(ROOT / "base" / "indice_manifesto.json", {"corpus_sha256":self.digest,"trechos":len(texts),
                   "dimensao":int(self.vectors.shape[1]),"max_tokens_encoder":max(lengths),"busca":"Produto interno exato entre vetores normalizados", "prefixos":["query: ","passage: "]})

    def search(self, question, k=TOP_K, threshold=None):
        if self.vectors is None:
            self.build()
        q = self.load_encoder().encode(["query: " + question], normalize_embeddings=True, show_progress_bar=False)[0]
        scores = self.vectors @ q
        ids = np.argsort(-scores, kind="stable")[:min(k, len(self.chunks))]
        return [{**self.chunks[int(i)], "score":float(scores[i])} for i in ids
                if threshold is None or float(scores[i]) >= threshold]

    @property
    def threshold(self):
        data = read_json(ROOT / "avaliacao" / "calibracao.json")
        if not data:
            raise FileNotFoundError("Busca não calibrada. Execute python -m scripts.calibrar_busca.")
        if data["corpus_sha256"] != self.digest:
            raise ValueError("A base mudou. Recalibre a busca antes de atender perguntas.")
        return float(data["limiar"])


def context_text(chunks):
    return "\n".join(f'[{c["id"]}] {c["titulo"]}: {c["texto"]}' for c in chunks)
