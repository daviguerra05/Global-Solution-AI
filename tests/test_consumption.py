import math
import pytest
from pydantic import ValidationError
from energia_clara.config import ROOT
from energia_clara.schemas import Simulation
from energia_clara.consumption import parse_csv,simulate,COLUMNS


def sample(): return parse_csv((ROOT/"dados"/"consumo_exemplo.csv").read_bytes())


def test_example_has_auditable_total():
    result=simulate(Simulation(aparelhos=sample(),tarifa_kwh=0.95))
    assert result["consumo_total_kwh"]==pytest.approx(229.84)
    assert result["custo_energia_estimado"]==218.35
    assert result["aparelhos"][0]["aparelho"]=="Chuveiro"


def test_reducing_shower_ten_minutes_has_exact_energy_effect():
    rows=sample()
    rows[0]["horas_dia"]=1/3
    result=simulate(Simulation(aparelhos=rows,tarifa_kwh=0.95))
    assert result["consumo_total_kwh"]==pytest.approx(202.34)


@pytest.mark.parametrize("field,value",[("potencia_w",-10),("horas_dia",25),("dias_mes",32),("fator_uso",0),("fator_uso",1.1),("quantidade",1.5),("quantidade",0),("horas_dia",float("nan")),("potencia_w",float("inf"))])
def test_invalid_values_never_become_estimates(field,value):
    rows=sample(); rows[0][field]=value
    with pytest.raises(ValidationError): Simulation(aparelhos=rows,tarifa_kwh=0.95)


def test_decimal_comma_and_semicolon_csv():
    text=";".join(COLUMNS)+"\nLâmpada;9;2,5;30;1;1\n"
    rows=parse_csv(text.encode())
    assert rows[0]["horas_dia"]==2.5


def test_csv_rejects_unexpected_columns_and_size():
    with pytest.raises(ValueError): parse_csv(b"nome,cpf\nx,123\n")
    with pytest.raises(ValueError): parse_csv(b"x"*100001)


def test_csv_rejects_duplicate_header():
    text=",".join(COLUMNS+["aparelho"])+"\nX,9,2,30,1,1,Y\n"
    with pytest.raises(ValueError): parse_csv(text.encode())
