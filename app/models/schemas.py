"""
Schemas Pydantic para validação de dados da API
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EmailClassification(str, Enum):
    """Tipos de classificação de email"""

    PRODUCTIVE = "productive"
    UNPRODUCTIVE = "unproductive"


class EmailAnalysisRequest(BaseModel):
    """Request para análise de email"""

    content: str = Field(
        ..., min_length=10, max_length=10000, description="Conteúdo do email"
    )
    file_name: Optional[str] = Field(
        None, description="Nome do arquivo (se enviado via upload)"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("O conteúdo do email não pode estar vazio")
        return v.strip()


class EmailAnalysisResponse(BaseModel):
    """Response da análise de email"""

    id: str = Field(..., description="ID único da análise")
    classification: EmailClassification = Field(
        ..., description="Classificação do email"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Nível de confiança da classificação"
    )
    suggested_response: str = Field(..., description="Resposta sugerida")
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp da análise"
    )
    file_name: Optional[str] = Field(None, description="Nome do arquivo analisado")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmailHistory(BaseModel):
    """Histórico de emails analisados"""

    id: str
    content: str = Field(
        ..., max_length=500, description="Conteúdo truncado para histórico"
    )
    classification: EmailClassification
    confidence: float
    suggested_response: str
    analysis_timestamp: datetime
    file_name: Optional[str] = None


class StatsResponse(BaseModel):
    """Estatísticas do sistema"""

    total_processed: int = Field(..., ge=0, description="Total de emails processados")
    productive_count: int = Field(..., ge=0, description="Emails produtivos")
    unproductive_count: int = Field(..., ge=0, description="Emails improdutivos")
    average_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confiança média"
    )


class HealthResponse(BaseModel):
    """Response do health check"""

    status: str = "healthy"
    app_name: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseModel):
    """Response padrão para erros"""

    error: str = Field(..., description="Mensagem de erro")
    detail: Optional[str] = Field(None, description="Detalhes adicionais do erro")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
