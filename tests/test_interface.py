from types import SimpleNamespace
from energia_clara.config import ROOT
from energia_clara.schemas import Simulation
from energia_clara.consumption import simulate


def test_scenario_submission_updates_metrics_without_widget_state_conflict(monkeypatch):
    import requests
    from streamlit.testing.v1 import AppTest
    def local_api(method,url,**kwargs):
        if url.endswith("/saude"): result={"status":"ok"}
        elif url.endswith("/simular"): result=simulate(Simulation.model_validate(kwargs["json"]))
        else: raise AssertionError(url)
        return SimpleNamespace(ok=True,json=lambda:result)
    monkeypatch.setattr(requests,"request",local_api)
    at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=15).run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Simular consumo").run()
    at.number_input[0].set_value(0.90)
    next(b for b in at.button if b.label=="Comparar cenário").click().run()
    assert not at.exception
    assert at.session_state["comparacao_cenario"]["depois"]["custo_energia_estimado"]==206.86
    assert any(m.value=="R$ 206,86" for m in at.metric)
