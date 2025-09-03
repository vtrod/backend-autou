"""
Serviço de armazenamento de dados em memória
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from app.models.schemas import EmailAnalysisResponse, EmailHistory, StatsResponse, EmailClassification

logger = logging.getLogger(__name__)


class DataStorageService:
    """Serviço para armazenar dados em memória (pode ser expandido para banco de dados)"""
    
    def __init__(self):
        """Inicializa o armazenamento em memória"""
        self._analyses: Dict[str, EmailAnalysisResponse] = {}
        self._history: List[EmailHistory] = []
        self._stats = {
            'total_processed': 0,
            'productive_count': 0,
            'unproductive_count': 0,
            'total_confidence': 0.0
        }
    
    def store_analysis(self, analysis: EmailAnalysisResponse, content: str = "") -> None:
        """Armazena uma análise de email"""
        try:
            # Armazenar análise completa
            self._analyses[analysis.id] = analysis
            
            # Atualizar histórico (com conteúdo truncado)
            history_item = EmailHistory(
                id=analysis.id,
                content=self._truncate_content(content),
                classification=analysis.classification,
                confidence=analysis.confidence,
                suggested_response=analysis.suggested_response,
                analysis_timestamp=analysis.analysis_timestamp,
                file_name=analysis.file_name
            )
            
            self._history.append(history_item)
            
            # Manter apenas os últimos 100 itens no histórico
            if len(self._history) > 100:
                self._history = self._history[-100:]
            
            # Atualizar estatísticas
            self._update_stats(analysis)
            
            logger.info(f"Análise armazenada com sucesso: {analysis.id}")
            
        except Exception as e:
            logger.error(f"Erro ao armazenar análise {analysis.id}: {str(e)}")
    
    def get_analysis(self, analysis_id: str) -> Optional[EmailAnalysisResponse]:
        """Recupera uma análise específica por ID"""
        return self._analyses.get(analysis_id)
    
    def get_history(self, limit: int = 50) -> List[EmailHistory]:
        """Recupera o histórico de análises"""
        # Retorna em ordem reversa (mais recentes primeiro)
        return list(reversed(self._history[-limit:]))
    
    def get_stats(self) -> StatsResponse:
        """Recupera estatísticas do sistema"""
        average_confidence = 0.0
        if self._stats['total_processed'] > 0:
            average_confidence = self._stats['total_confidence'] / self._stats['total_processed']
        
        return StatsResponse(
            total_processed=self._stats['total_processed'],
            productive_count=self._stats['productive_count'],
            unproductive_count=self._stats['unproductive_count'],
            average_confidence=round(average_confidence, 2)
        )
    
    def clear_history(self) -> bool:
        """Limpa todo o histórico e estatísticas"""
        try:
            self._analyses.clear()
            self._history.clear()
            self._stats = {
                'total_processed': 0,
                'productive_count': 0,
                'unproductive_count': 0,
                'total_confidence': 0.0
            }
            logger.info("Histórico e estatísticas limpos com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar histórico: {str(e)}")
            return False
    
    def _update_stats(self, analysis: EmailAnalysisResponse) -> None:
        """Atualiza estatísticas com nova análise"""
        self._stats['total_processed'] += 1
        self._stats['total_confidence'] += analysis.confidence
        
        if analysis.classification == EmailClassification.PRODUCTIVE:
            self._stats['productive_count'] += 1
        else:
            self._stats['unproductive_count'] += 1
    
    def _truncate_content(self, content: str, max_length: int = 200) -> str:
        """Trunca conteúdo para exibição no histórico"""
        if len(content) <= max_length:
            return content
        
        # Truncar e adicionar reticências
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def get_analysis_by_classification(self, classification: EmailClassification) -> List[EmailHistory]:
        """Recupera análises filtradas por classificação"""
        return [
            item for item in self._history 
            if item.classification == classification
        ]
    
    def get_recent_analyses(self, hours: int = 24) -> List[EmailHistory]:
        """Recupera análises das últimas N horas"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            item for item in self._history 
            if item.analysis_timestamp >= cutoff_time
        ]


# Instância global do serviço
data_storage = DataStorageService()
