"""
Serviço de classificação de emails usando IA
"""
import re
import uuid
from typing import Tuple
from datetime import datetime
import logging

from app.models.schemas import EmailClassification, EmailAnalysisResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailClassifierService:
    """Serviço para classificação inteligente de emails"""
    
    def __init__(self):
        """Inicializa o classificador"""
        self.productive_keywords = {
            # Ações diretas
            'action': ['ação', 'fazer', 'implementar', 'desenvolver', 'criar', 'modificar', 'alterar', 'corrigir'],
            'urgency': ['urgente', 'importante', 'prioridade', 'deadline', 'prazo', 'imediato'],
            'request': ['solicito', 'preciso', 'necessário', 'requer', 'pedido', 'solicitação'],
            'meeting': ['reunião', 'meeting', 'encontro', 'agenda', 'agendamento', 'horário'],
            'decision': ['decisão', 'aprovar', 'autorizar', 'confirmar', 'validar', 'aceitar'],
            'problem': ['problema', 'erro', 'bug', 'falha', 'defeito', 'issue'],
            'question': ['pergunta', 'dúvida', 'questão', 'esclarecimento', 'como', 'quando', 'onde'],
            'response_needed': ['resposta', 'responder', 'retorno', 'feedback', 'confirmação']
        }
        
        self.unproductive_keywords = {
            'courtesy': ['obrigado', 'parabéns', 'felicitações', 'sucesso', 'gratidão'],
            'informational': ['informação', 'comunicado', 'aviso', 'notificação', 'atualização'],
            'social': ['aniversário', 'festa', 'evento social', 'confraternização'],
            'automated': ['automático', 'sistema', 'newsletter', 'boletim', 'relatório automático'],
            'fyi': ['para conhecimento', 'fyi', 'informativo', 'apenas informando']
        }
        
        # Padrões de email produtivo
        self.productive_patterns = [
            r'\b(quando|até quando|prazo|deadline)\b',
            r'\b(pode|poderia|consegue)\s+\w+',
            r'\?',  # Emails com perguntas
            r'\b(solicito|preciso|necessário)\b',
            r'\b(urgente|importante|prioridade)\b'
        ]
        
        # Padrões de email improdutivo
        self.unproductive_patterns = [
            r'\b(obrigad[oa]|agradec)\w*',
            r'\b(parabéns|felicitações)\b',
            r'\b(para conhecimento|fyi)\b',
            r'\b(newsletter|boletim)\b'
        ]
    
    def preprocess_text(self, text: str) -> str:
        """Pré-processa o texto do email"""
        # Remove caracteres especiais e normaliza
        text = re.sub(r'[^\w\s\?\!]', ' ', text.lower())
        # Remove espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def calculate_keyword_score(self, text: str) -> Tuple[float, float]:
        """Calcula pontuação baseada em palavras-chave"""
        productive_score = 0
        unproductive_score = 0
        
        # Pontuação para palavras produtivas
        for category, keywords in self.productive_keywords.items():
            for keyword in keywords:
                count = text.count(keyword)
                if category in ['urgency', 'action', 'request']:
                    productive_score += count * 3  # Peso maior
                else:
                    productive_score += count * 2
        
        # Pontuação para palavras improdutivas
        for category, keywords in self.unproductive_keywords.items():
            for keyword in keywords:
                count = text.count(keyword)
                if category in ['courtesy', 'automated']:
                    unproductive_score += count * 3  # Peso maior
                else:
                    unproductive_score += count * 2
        
        return productive_score, unproductive_score
    
    def calculate_pattern_score(self, text: str) -> Tuple[float, float]:
        """Calcula pontuação baseada em padrões regex"""
        productive_score = 0
        unproductive_score = 0
        
        # Padrões produtivos
        for pattern in self.productive_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            productive_score += matches * 2
        
        # Padrões improdutivos
        for pattern in self.unproductive_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            unproductive_score += matches * 2
        
        return productive_score, unproductive_score
    
    def analyze_structure(self, text: str) -> float:
        """Analisa a estrutura do email"""
        score = 0
        
        # Presença de perguntas aumenta a chance de ser produtivo
        question_marks = text.count('?')
        score += question_marks * 2
        
        # Emails muito curtos tendem a ser menos produtivos
        if len(text.split()) < 20:
            score -= 1
        
        # Emails muito longos podem ser mais informativos
        if len(text.split()) > 200:
            score += 1
        
        return score
    
    def classify_email(self, content: str, file_name: str = None) -> EmailAnalysisResponse:
        """Classifica um email e gera resposta sugerida"""
        try:
            # Pré-processamento
            processed_text = self.preprocess_text(content)
            
            # Cálculo de pontuações
            keyword_productive, keyword_unproductive = self.calculate_keyword_score(processed_text)
            pattern_productive, pattern_unproductive = self.calculate_pattern_score(processed_text)
            structure_score = self.analyze_structure(processed_text)
            
            # Pontuação total
            total_productive = keyword_productive + pattern_productive + structure_score
            total_unproductive = keyword_unproductive
            
            # Classificação
            if total_productive > total_unproductive:
                classification = EmailClassification.PRODUCTIVE
                confidence = min(0.95, 0.6 + (total_productive - total_unproductive) * 0.05)
            else:
                classification = EmailClassification.UNPRODUCTIVE
                confidence = min(0.95, 0.6 + (total_unproductive - total_productive) * 0.05)
            
            # Garantir confiança mínima
            confidence = max(0.5, confidence)
            
            # Gerar resposta sugerida
            suggested_response = self._generate_response(classification, content)
            
            # Criar resposta
            analysis_id = str(uuid.uuid4())
            
            return EmailAnalysisResponse(
                id=analysis_id,
                classification=classification,
                confidence=round(confidence, 2),
                suggested_response=suggested_response,
                analysis_timestamp=datetime.now(),
                file_name=file_name
            )
            
        except Exception as e:
            logger.error(f"Erro na classificação do email: {str(e)}")
            # Resposta padrão em caso de erro
            return EmailAnalysisResponse(
                id=str(uuid.uuid4()),
                classification=EmailClassification.UNPRODUCTIVE,
                confidence=0.5,
                suggested_response="Obrigado pelo seu email. Analisaremos o conteúdo e retornaremos em breve.",
                analysis_timestamp=datetime.now(),
                file_name=file_name
            )
    
    def _generate_response(self, classification: EmailClassification, content: str) -> str:
        """Gera resposta automática baseada na classificação"""
        content_lower = content.lower()
        
        if classification == EmailClassification.PRODUCTIVE:
            # Respostas para emails produtivos
            if any(word in content_lower for word in ['urgente', 'importante', 'prioridade']):
                return "Obrigado pelo seu email. Entendo a importância e urgência da solicitação. Vou priorizar esta demanda e retornar com uma resposta detalhada o mais breve possível."
            
            elif any(word in content_lower for word in ['reunião', 'meeting', 'agenda']):
                return "Obrigado pela solicitação de reunião. Vou verificar minha agenda e retornar com opções de horários que funcionem para ambos. Aguarde meu retorno em breve."
            
            elif any(word in content_lower for word in ['pergunta', 'dúvida', 'questão', '?']):
                return "Obrigado pela sua pergunta. Vou analisar os pontos levantados e retornar com uma resposta detalhada. Se precisar de esclarecimentos adicionais, por favor me informe."
            
            elif any(word in content_lower for word in ['problema', 'erro', 'bug', 'falha']):
                return "Obrigado por reportar esta questão. Vou investigar o problema imediatamente e trabalhar em uma solução. Manterei você informado sobre o progresso."
            
            else:
                return "Obrigado pelo seu email. Recebi sua solicitação e vou trabalhar nisso. Retornarei com uma resposta completa em breve."
        
        else:
            # Respostas para emails informativos/cortesia
            if any(word in content_lower for word in ['obrigado', 'obrigada', 'agradec']):
                return "De nada! Foi um prazer ajudar. Se precisar de mais alguma coisa, não hesite em entrar em contato."
            
            elif any(word in content_lower for word in ['parabéns', 'felicitações']):
                return "Muito obrigado pelas felicitações! Fico feliz em compartilhar esta conquista com você."
            
            elif any(word in content_lower for word in ['informação', 'comunicado', 'aviso']):
                return "Obrigado pela informação. Recebi o comunicado e tomarei as ações necessárias conforme apropriado."
            
            else:
                return "Obrigado pelo seu email. Recebi a informação e fico à disposição se precisar de algo mais."


# Instância global do serviço
email_classifier = EmailClassifierService()
