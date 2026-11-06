"""Estimativas determinísticas e explícitas. Não calcula uma fatura real."""
import csv
import io
from decimal import Decimal, ROUND_HALF_UP
from energia_clara.schemas import Simulation, Appliance

COLUMNS=["aparelho","potencia_w","horas_dia","dias_mes","quantidade","fator_uso"]


def parse_csv(content):
    if len(content)>100_000: raise ValueError("O CSV deve ter até 100 KB.")
    try: text=content.decode("utf-8-sig")
    except UnicodeDecodeError: raise ValueError("Salve o CSV em UTF-8.")
    if "\x00" in text: raise ValueError("O arquivo contém caracteres inválidos.")
    try: dialect=csv.Sniffer().sniff(text[:8192],delimiters=",;")
    except csv.Error: raise ValueError("Use CSV separado por vírgula ou ponto e vírgula.")
    reader=csv.DictReader(io.StringIO(text),dialect=dialect)
    if set(reader.fieldnames or [])!=set(COLUMNS) or len(reader.fieldnames or [])!=len(COLUMNS):
        raise ValueError("As colunas devem ser: "+", ".join(COLUMNS))
    rows=[]
    for i,row in enumerate(reader,2):
        if len(rows)>=50: raise ValueError("Use no máximo 50 equipamentos.")
        if None in row or any(v is None for v in row.values()): raise ValueError(f"Confira o número de colunas na linha {i}.")
        try:
            item={"aparelho":row["aparelho"].strip(),"quantidade":int(row["quantidade"])}
            item.update({k:float(row[k].replace(",",".")) for k in COLUMNS if k not in ["aparelho","quantidade"]})
            rows.append(Appliance.model_validate(item).model_dump())
        except Exception:
            raise ValueError(f"Confira os números e limites na linha {i}. Potência positiva; horas até 24; dias até 31; fator entre 0 e 1.")
    if not rows: raise ValueError("Inclua pelo menos um equipamento.")
    return rows


def simulate(data:Simulation):
    rows=[]; total=Decimal("0"); rate=Decimal(str(data.tarifa_kwh))
    for a in data.aparelhos:
        kwh=Decimal(str(a.potencia_w))*Decimal(str(a.horas_dia))*Decimal(str(a.dias_mes))*a.quantidade*Decimal(str(a.fator_uso))/1000
        total+=kwh
        rows.append({**a.model_dump(),"consumo_kwh":float(kwh.quantize(Decimal("0.0001"))),
                     "custo_energia_estimado":float((kwh*rate).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))})
    rows.sort(key=lambda r:-r["consumo_kwh"])
    return {"aparelhos":rows,"consumo_total_kwh":float(total.quantize(Decimal("0.0001"))),
            "custo_energia_estimado":float((total*rate).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)),
            "tarifa_simulada_kwh":float(rate),"formula":"W × horas/dia × dias × quantidade × fator de uso ÷ 1000",
            "fonte_formula":"E001","natureza":"Estimativa educativa; valores fictícios ou informados pelo usuário, não medição.",
            "limites":"Não inclui tributos, iluminação pública, bandeiras ou tarifas por horário. Fator de uso é uma hipótese, não um coeficiente certificado."}
