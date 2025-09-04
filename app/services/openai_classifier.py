"""
Serviço de classificação de emails usando OpenAI GPT
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any
import json

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None
from ..models.schemas import EmailClassification, EmailAnalysisResponse
from ..core.config import settings

logger = logging.getLogger(__name__)


class OpenAIEmailClassifierService:
    """Serviço para classificação de emails usando OpenAI GPT"""
    
    def __init__(self):
        """Inicializa o cliente OpenAI"""
        self.client = None
        self.is_available = False
        
        if settings.openai_api_key and OpenAI is not None:
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
                self.is_available = True
                logger.info("Cliente OpenAI inicializado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente OpenAI: {e}")
                self.is_available = False
        else:
            logger.warning("OpenAI indisponível ou API key não configurada. Usando fallback.")
    
    def get_system_prompt(self) -> str:
        """Retorna o prompt do sistema para classificação de emails"""
        return """Você é um assistente especializado em classificar emails corporativos.

Sua tarefa é analisar emails e classificá-los em duas categorias:

1. **PRODUTIVO**: Emails que requerem uma ação, resposta ou decisão específica:
   - Solicitações de trabalho, projetos ou tarefas
   - Perguntas que precisam de resposta
   - Reuniões que precisam ser agendadas
   - Problemas que precisam ser resolvidos
   - Decisões que precisam ser tomadas
   - Prazos e deadlines
   - Requestos de aprovação ou autorização

2. **IMPRODUTIVO**: Emails informativos que não requerem ação imediata:
   - Mensagens de cortesia (obrigado, parabéns)
   - Comunicados informativos gerais
   - Newsletters e boletins
   - Mensagens sociais (aniversários, eventos)
   - Confirmações automáticas do sistema
   - FYI (apenas para conhecimento)

Retorne sua resposta no formato JSON seguindo exatamente esta estrutura:
{
    "classification": "productive" ou "unproductive",
    "confidence": número entre 0.5 e 1.0,
    "reasoning": "breve explicação da classificação",
    "suggested_response": "resposta sugerida apropriada em português"
}

Seja preciso e considere o contexto corporativo brasileiro."""

    def get_user_prompt(self, content: str) -> str:
        """Monta o prompt do usuário com o conteúdo do email"""
        return f"""Analise o seguinte email e classifique-o:

EMAIL:
{content}

Classifique este email como "productive" ou "unproductive" e forneça uma resposta sugerida adequada."""

    async def classify_with_openai(self, content: str) -> Dict[str, Any]:
        """Classifica o email usando OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": self.get_user_prompt(content)}
                ],
                temperature=0.1,  # Baixa temperatura para mais consistência
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Validar estrutura da resposta
            required_keys = ["classification", "confidence", "reasoning", "suggested_response"]
            if not all(key in result for key in required_keys):
                raise ValueError("Resposta da OpenAI não contém todas as chaves necessárias")
            
            # Validar classificação
            if result["classification"] not in ["productive", "unproductive"]:
                raise ValueError("Classificação inválida da OpenAI")
            
            # Validar confiança
            confidence = float(result["confidence"])
            if not (0.5 <= confidence <= 1.0):
                confidence = max(0.5, min(1.0, confidence))
            
            result["confidence"] = confidence
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON da OpenAI: {e}")
            raise Exception("Resposta inválida da OpenAI")
        except Exception as e:
            logger.error(f"Erro na chamada da OpenAI: {e}")
            raise Exception(f"Erro da API OpenAI: {str(e)}")

    def generate_fallback_response(self, content: str) -> Dict[str, Any]:
        """Gera resposta de fallback quando OpenAI não está disponível"""
        # Classificação simples baseada em palavras-chave
        content_lower = content.lower()
        
        productive_indicators = [
            'solicito', 'preciso', 'pode', 'poderia', 'quando', 'prazo', 
            'deadline', 'urgente', 'importante', 'reunião', 'meeting',
            'projeto', 'tarefa', 'problema', 'erro', 'bug', 'aprovação'
        ]
        
        unproductive_indicators = [
            'obrigado', 'obrigada', 'parabéns', 'felicitações',
            'informação', 'comunicado', 'fyi', 'newsletter', 'boletim'
        ]
        
        productive_score = sum(1 for word in productive_indicators if word in content_lower)
        unproductive_score = sum(1 for word in unproductive_indicators if word in content_lower)
        
        # Adicionar peso para perguntas
        if '?' in content:
            productive_score += 2
        
        if productive_score > unproductive_score:
            classification = "productive"
            confidence = min(0.85, 0.6 + (productive_score - unproductive_score) * 0.05)
            suggested_response = "Obrigado pelo seu email. Recebi sua solicitação e retornarei em breve com as informações necessárias."
            reasoning = "Email contém elementos que sugerem necessidade de ação ou resposta"
        else:
            classification = "unproductive"
            confidence = min(0.85, 0.6 + (unproductive_score - productive_score) * 0.05)
            suggested_response = "Obrigado pelo seu email. Recebi a informação e fico à disposição se precisar de algo mais."
            reasoning = "Email parece ser informativo ou de cortesia"
        
        return {
            "classification": classification,
            "confidence": max(0.5, confidence),
            "reasoning": reasoning,
            "suggested_response": suggested_response
        }

    async def classify_email(self, content: str, file_name: str = None) -> EmailAnalysisResponse:
        """Classifica um email usando OpenAI ou fallback"""
        try:
            analysis_id = str(uuid.uuid4())
            
            # Tentar usar OpenAI se disponível
            if self.is_available and settings.use_openai:
                try:
                    result = await self.classify_with_openai(content)
                    logger.info(f"Classificação OpenAI: {result['classification']} (confiança: {result['confidence']})")
                except Exception as e:
                    logger.warning(f"Erro na OpenAI, usando fallback: {e}")
                    result = self.generate_fallback_response(content)
            else:
                logger.info("Usando classificador local (OpenAI não disponível)")
                result = self.generate_fallback_response(content)
            
            # Converter para formato do schema
            classification = EmailClassification.PRODUCTIVE if result["classification"] == "productive" else EmailClassification.UNPRODUCTIVE
            
            return EmailAnalysisResponse(
                id=analysis_id,
                classification=classification,
                confidence=round(result["confidence"], 2),
                suggested_response=result["suggested_response"],
                analysis_timestamp=datetime.now(),
                file_name=file_name
            )
            
        except Exception as e:
            logger.error(f"Erro fatal na classificação: {e}")
            # Resposta de emergência
            return EmailAnalysisResponse(
                id=str(uuid.uuid4()),
                classification=EmailClassification.UNPRODUCTIVE,
                confidence=0.5,
                suggested_response="Obrigado pelo seu email. Analisaremos o conteúdo e retornaremos em breve.",
                analysis_timestamp=datetime.now(),
                file_name=file_name
            )


# Instância global do serviço
openai_classifier = OpenAIEmailClassifierService()
