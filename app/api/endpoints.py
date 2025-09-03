"""
Endpoints da API FastAPI
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    EmailAnalysisRequest, 
    EmailAnalysisResponse, 
    EmailHistory, 
    StatsResponse, 
    HealthResponse,
    ErrorResponse,
    EmailClassification
)
from app.services.ai_classifier import email_classifier
from app.services.openai_classifier import openai_classifier
from app.services.file_processor import file_processor
from app.services.data_storage import data_storage
from app.core.config import settings

logger = logging.getLogger(__name__)

# Router principal
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check do sistema"""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version
    )


@router.post("/analyze", response_model=EmailAnalysisResponse)
async def analyze_email(request: EmailAnalysisRequest):
    """Analisa conteúdo de email via texto direto"""
    try:
        logger.info(f"Analisando email via texto direto - {len(request.content)} caracteres")
        
        # Classificar email usando OpenAI ou fallback
        if settings.use_openai and settings.openai_api_key:
            analysis = await openai_classifier.classify_email(
                content=request.content,
                file_name=request.file_name
            )
        else:
            analysis = email_classifier.classify_email(
                content=request.content,
                file_name=request.file_name
            )
        
        # Armazenar resultado
        data_storage.store_analysis(analysis, request.content)
        
        logger.info(f"Análise concluída - ID: {analysis.id}, Classificação: {analysis.classification}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Erro na análise de email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno na análise do email"
        )


@router.post("/analyze/file", response_model=EmailAnalysisResponse)
async def analyze_email_file(file: UploadFile = File(...)):
    """Analisa email a partir de arquivo enviado"""
    try:
        logger.info(f"Analisando email via arquivo: {file.filename}")
        
        # Extrair texto do arquivo
        content, filename = await file_processor.extract_text_from_file(file)
        
        # Truncar se necessário
        content = file_processor.truncate_text_for_analysis(content)
        
        logger.info(f"Texto extraído do arquivo - {len(content)} caracteres")
        
        # Classificar email usando OpenAI ou fallback
        if settings.use_openai and settings.openai_api_key:
            analysis = await openai_classifier.classify_email(
                content=content,
                file_name=filename
            )
        else:
            analysis = email_classifier.classify_email(
                content=content,
                file_name=filename
            )
        
        # Armazenar resultado
        data_storage.store_analysis(analysis, content)
        
        logger.info(f"Análise de arquivo concluída - ID: {analysis.id}, Classificação: {analysis.classification}")
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na análise de arquivo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno na análise do arquivo"
        )


@router.get("/analysis/{analysis_id}", response_model=EmailAnalysisResponse)
async def get_analysis(analysis_id: str):
    """Recupera uma análise específica por ID"""
    try:
        analysis = data_storage.get_analysis(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada"
            )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao recuperar análise {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao recuperar análise"
        )


@router.get("/history", response_model=List[EmailHistory])
async def get_history(
    limit: int = 50,
    classification: Optional[EmailClassification] = None
):
    """Recupera histórico de análises"""
    try:
        if classification:
            # Filtrar por classificação
            history = data_storage.get_analysis_by_classification(classification)
            # Aplicar limite
            history = history[-limit:] if len(history) > limit else history
            history.reverse()  # Mais recentes primeiro
        else:
            # Recuperar todos
            history = data_storage.get_history(limit)
        
        logger.info(f"Histórico recuperado - {len(history)} itens")
        return history
        
    except Exception as e:
        logger.error(f"Erro ao recuperar histórico: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao recuperar histórico"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Recupera estatísticas do sistema"""
    try:
        stats = data_storage.get_stats()
        logger.info(f"Estatísticas recuperadas - Total: {stats.total_processed}")
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao recuperar estatísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao recuperar estatísticas"
        )


@router.delete("/history")
async def clear_history():
    """Limpa todo o histórico e estatísticas"""
    try:
        success = data_storage.clear_history()
        
        if success:
            logger.info("Histórico limpo com sucesso")
            return {"message": "Histórico limpo com sucesso"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao limpar histórico"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao limpar histórico: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao limpar histórico"
        )


@router.get("/")
async def root():
    """Endpoint raiz da API"""
    return {
        "message": f"Bem-vindo ao {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }
