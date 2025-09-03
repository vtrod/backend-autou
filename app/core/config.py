"""
Configurações do aplicativo FastAPI
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Configurações básicas
    app_name: str = "AutoU Email Classifier API"
    app_version: str = "1.0.0"
    debug: bool = False
    # Configurações de servidor
    host: str = "0.0.0.0"
    port: int = 8000
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # Para produção, adicionamos uma função para permitir origins da Vercel
    allow_vercel_origins: bool = True

    # Configurações de IA
    model_name: str = "distilbert-base-uncased"
    max_content_length: int = 10000  # Máximo de caracteres por email
    confidence_threshold: float = 0.7

    # Configurações de arquivo
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = ["txt", "pdf"]

    # Configurações de banco de dados (para futuro uso)
    database_url: str = "sqlite:///./emails.db"

    # Configurações de logs
    log_level: str = "INFO"

    # Configurações da OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    use_openai: bool = True  # Flag para usar OpenAI ou classificador local

    class Config:
        env_file = ".env"
        case_sensitive = False
        protected_namespaces = ("settings_",)
        extra = "ignore"  # Ignora campos extras do .env


# Instância global das configurações
settings = Settings()
