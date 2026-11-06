"""Única etapa que requer internet. Não envia perguntas ou dados domésticos."""
from energia_clara.config import ROOT, MODEL_DIR, ENCODER_DIR, BASE_MODEL, EMBEDDING_MODEL, write_json, read_json
import argparse
import hashlib
import time
from datetime import datetime, timezone


def main():
    import os
    os.environ["HF_HUB_OFFLINE"]="0"
    import requests
    from huggingface_hub import HfApi, snapshot_download
    parser = argparse.ArgumentParser()
    parser.add_argument("--apenas-modelos", action="store_true")
    parser.add_argument("--apenas-fontes", action="store_true")
    parser.add_argument("--fonte", default=None)
    args = parser.parse_args()
    locked = read_json(ROOT / "modelos" / "revisoes.json", {})
    if not args.apenas_fontes:
        for repo, folder in [(BASE_MODEL, MODEL_DIR), (EMBEDDING_MODEL, ENCODER_DIR)]:
            print("Obtendo modelo:", repo, flush=True)
            revision = locked.get(repo, {}).get("revision") or HfApi().model_info(repo,token=False).sha
            snapshot_download(repo, revision=revision, local_dir=folder,
                              token=False,
                              allow_patterns=["*.json", "*.safetensors", "vocab.txt", "vocab.json", "merges.txt", "modules.json", "1_Pooling/*", "README.md"],
                              max_workers=2)
            files = {str(p.relative_to(folder)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in folder.rglob("*") if p.is_file() and ".cache" not in p.parts}
            locked[repo] = {"revision": revision, "arquivos_sha256": files}
            write_json(ROOT / "modelos" / "revisoes.json", locked)
            print("Modelo salvo:", folder, flush=True)
    if not args.apenas_modelos:
        sources = read_json(ROOT / "base" / "fontes.json", [])
        rows = []
        folder = ROOT / "base" / "originais"
        folder.mkdir(parents=True, exist_ok=True)
        for source in sources:
            if args.fonte and source["id"] != args.fonte:
                rows.extend(r for r in read_json(ROOT / "base" / "auditoria_download.json", []) if r["id"] == source["id"])
                continue
            row = {"id": source["id"], "url": source["url"], "consultado_em": datetime.now(timezone.utc).isoformat()}
            try:
                r = requests.get(source["url"], timeout=45, headers={"User-Agent": "EnergiaClara-EstudoAcademico/1.0"})
                r.raise_for_status()
                suffix = ".pdf" if "application/pdf" in r.headers.get("Content-Type", "") else ".html"
                dest = folder / (source["id"] + suffix)
                dest.write_bytes(r.content)
                row.update(status_http=r.status_code, sha256=hashlib.sha256(r.content).hexdigest(), bytes=len(r.content))
                print("Fonte arquivada:", source["id"], len(r.content), flush=True)
            except requests.RequestException as exc:
                row.update(erro=type(exc).__name__, verificacao="Fonte consultada via navegador de pesquisa; snapshot HTTP indisponível.")
                print("Snapshot indisponível:", source["id"], type(exc).__name__, flush=True)
            rows.append(row)
        write_json(ROOT / "base" / "auditoria_download.json", rows)


if __name__ == "__main__":
    main()
