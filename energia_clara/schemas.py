from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, FiniteFloat
from energia_clara.config import MAX_QUESTION_CHARS


class ModelAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["respondido", "nao_consta"]
    resposta: str = Field(min_length=1, max_length=1200)
    fontes: list[str] = Field(max_length=3)

    @field_validator("fontes")
    @classmethod
    def unique_sources(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Referências duplicadas.")
        return value


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pergunta: str = Field(min_length=3, max_length=MAX_QUESTION_CHARS)
    configuracao: Literal["sem_contexto", "rag", "lora_rag"] = "lora_rag"

    @field_validator("pergunta")
    @classmethod
    def trim_question(cls, value):
        value=value.strip()
        if len(value)<3 or "\x00" in value:
            raise ValueError("Informe uma pergunta válida.")
        return value


class Appliance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aparelho: str = Field(min_length=1,max_length=60)
    potencia_w: FiniteFloat = Field(gt=0, le=30000)
    horas_dia: FiniteFloat = Field(ge=0, le=24)
    dias_mes: FiniteFloat = Field(ge=0, le=31)
    quantidade: int = Field(ge=1, le=100)
    fator_uso: FiniteFloat = Field(gt=0, le=1)


class Simulation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aparelhos: list[Appliance] = Field(min_length=1,max_length=50)
    tarifa_kwh: FiniteFloat = Field(ge=0,le=10)
