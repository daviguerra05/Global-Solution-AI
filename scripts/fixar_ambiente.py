"""Exporta somente dependências transitivas do projeto, sem pacotes pessoais alheios."""
from pathlib import Path
from importlib import metadata
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from energia_clara.config import ROOT,write_json


def main():
    names=[Requirement(x.strip()).name for x in (ROOT/"requirements.txt").read_text().splitlines() if x.strip() and not x.startswith("#")]
    pending=names+["torch","setuptools"]
    versions={}
    while pending:
        name=canonicalize_name(pending.pop())
        if name in versions: continue
        dist=metadata.distribution(name)
        versions[name]=dist.version
        for spec in dist.requires or []:
            req=Requirement(spec)
            if req.marker is None or req.marker.evaluate({"extra":""}): pending.append(req.name)
    lines=["# Ambiente efetivamente verificado no Windows / Python 3.14.7.",
           "# Instale primeiro torch==2.13.0 pelo índice CPU, conforme README.md."]
    lines += [f"{name}=={version}" for name,version in sorted(versions.items())]
    (ROOT/"requirements.lock.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    write_json(ROOT/"avaliacao"/"dependencias.json",versions)
    # A licença Apache do adaptador é preservada junto ao artefato derivado.
    dist=metadata.distribution("peft")
    candidates=[dist.locate_file(f) for f in dist.files or [] if str(f).replace("\\","/").endswith("licenses/LICENSE")]
    if candidates:
        target=ROOT/"modelos"/"adaptador"/"LICENSE"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(Path(candidates[0]).read_bytes())
    print(f"{len(versions)} dependências fixadas.")


if __name__=="__main__": main()
