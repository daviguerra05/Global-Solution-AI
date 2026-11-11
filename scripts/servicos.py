"""Inicia/encerra somente os dois processos locais pertencentes a este projeto."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from energia_clara.config import ROOT, read_json, write_json

STATE=ROOT/"runtime"/"servicos.json"


def check_api_dependencies():
    """Detecta falhas de importação antes de abrir uma interface sem API."""
    flags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
    result=subprocess.run([sys.executable,"-c","import api.main"],cwd=ROOT,
                          env={**os.environ,"PYTHONUTF8":"1"},capture_output=True,
                          text=True,encoding="utf-8",errors="replace",timeout=60,
                          creationflags=flags)
    if result.returncode:
        runtime=ROOT/"runtime"
        runtime.mkdir(exist_ok=True)
        (runtime/"diagnostico_api.log").write_text(result.stderr,encoding="utf-8")
        if "_pydantic_core" in result.stderr and "DLL load failed" in result.stderr:
            raise RuntimeError(
                "A API não iniciou: o Windows não conseguiu carregar pydantic_core.\n"
                "Se o diagnóstico informa Controle de Aplicativo, a biblioteca está bloqueada pela política do Windows.\n"
                "Reabrir o atalho não resolve esse bloqueio. Solicite ao administrador a análise/liberação da biblioteca oficial,\n"
                "ou execute o projeto em um computador onde as dependências sejam permitidas.\n"
                "Não é necessário desativar as proteções do Windows. Diagnóstico: runtime/diagnostico_api.log")
        raise RuntimeError("A API não conseguiu carregar suas dependências. Consulte runtime/diagnostico_api.log.")


def owned(row):
    import psutil
    try:
        p=psutil.Process(int(row["pid"]))
        args=p.cmdline()
        return (abs(p.create_time()-row["create_time"])<0.1 and Path(p.cwd()).resolve()==ROOT and
                any(x in args for x in ["uvicorn","streamlit"]) and
                any(x in args for x in ["api.main:app","app.py"]))
    except (psutil.Error,ValueError,KeyError): return False


def stop():
    import psutil
    for name,row in read_json(STATE,{}).items():
        if not owned(row):
            print(name+": nenhum processo deste projeto a encerrar."); continue
        p=psutil.Process(row["pid"]); p.terminate()
        try: p.wait(timeout=5)
        except psutil.TimeoutExpired:
            if owned(row): p.kill()
        print(name+": encerrado.")
    write_json(STATE,{})


def start():
    import psutil
    import requests
    check_api_dependencies()
    state=read_json(STATE,{})
    runtime=ROOT/"runtime"; runtime.mkdir(exist_ok=True)
    env={**os.environ,"PYTHONUTF8":"1","HF_HUB_OFFLINE":"1"}
    commands={"api":["-m","uvicorn","api.main:app","--host","127.0.0.1","--port","8000"],
              "interface":["-m","streamlit","run","app.py","--server.port","8501"]}
    for name,args in commands.items():
        if name in state and owned(state[name]): continue
        url="http://127.0.0.1:8000/saude" if name=="api" else "http://127.0.0.1:8501/_stcore/health"
        try:
            if requests.get(url,timeout=1).ok:
                raise RuntimeError(f"A porta de {name} já está ocupada por um serviço não gerenciado. Encerre a execução anterior antes de abrir este atalho.")
        except requests.RequestException: pass
        log=(runtime/(name+".log")).open("a",encoding="utf-8")
        flags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
        child=subprocess.Popen([sys.executable,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                               creationflags=flags)
        log.close()
        state[name]={"pid":child.pid,"create_time":psutil.Process(child.pid).create_time()}
        write_json(STATE,state)
        print("Iniciando "+name+"...",flush=True)
    for _ in range(60):
        try:
            if requests.get("http://127.0.0.1:8000/saude",timeout=1).ok and requests.get("http://127.0.0.1:8501/_stcore/health",timeout=1).ok:
                print("Interface: http://127.0.0.1:8501\nAPI: http://127.0.0.1:8000/docs",flush=True)
                return
        except requests.RequestException: pass
        if any(not owned(row) for row in state.values()): raise RuntimeError("Um serviço não iniciou. Consulte runtime/api.log e runtime/interface.log.")
        time.sleep(0.5)
    raise RuntimeError("Os serviços ainda não responderam. Consulte os arquivos de log em runtime/.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("acao",choices=["iniciar","parar"])
    args=parser.parse_args()
    try: start() if args.acao=="iniciar" else stop()
    except (RuntimeError,subprocess.TimeoutExpired) as exc: print(str(exc)); sys.exit(1)
