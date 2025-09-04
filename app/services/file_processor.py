"""
Serviço para processamento de arquivos
"""
import PyPDF2
import io
import logging
from typing import Tuple
from fastapi import UploadFile, HTTPException

from ..core.config import settings

logger = logging.getLogger(__name__)


class FileProcessorService:
    """Serviço para processar uploads de arquivos"""
    
    def __init__(self):
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = settings.allowed_file_types
    
    def validate_file(self, file: UploadFile) -> None:
        """Valida arquivo enviado"""
        # Verificar tamanho do arquivo
        if hasattr(file, 'size') and file.size and file.size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Tamanho máximo permitido: {self.max_file_size / (1024*1024):.1f}MB"
            )
        
        # Verificar extensão
        if file.filename:
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in self.allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de arquivo não suportado. Tipos permitidos: {', '.join(self.allowed_extensions)}"
                )
    
    async def extract_text_from_file(self, file: UploadFile) -> Tuple[str, str]:
        """Extrai texto do arquivo enviado"""
        try:
            self.validate_file(file)
            
            file_content = await file.read()
            file_extension = file.filename.split('.')[-1].lower() if file.filename else 'txt'
            
            if file_extension == 'txt':
                # Processar arquivo TXT
                try:
                    text = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    # Tentar outras codificações
                    try:
                        text = file_content.decode('latin-1')
                    except UnicodeDecodeError:
                        text = file_content.decode('utf-8', errors='ignore')
                return text, file.filename or 'arquivo.txt'
            elif file_extension == 'pdf':
                # Processar arquivo PDF
                text = self._extract_text_from_pdf(file_content)
                return text, file.filename or 'arquivo.pdf'
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de arquivo não suportado: {file_extension}"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Erro interno ao processar arquivo"
            )
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extrai texto de arquivo PDF"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_content = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())
            # Juntar todo o texto
            full_text = '\n'.join(text_content)
            # Limpar e normalizar o texto
            full_text = full_text.replace('\x00', '')
            full_text = ' '.join(full_text.split())
            if not full_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Não foi possível extrair texto do PDF. Verifique se o arquivo não está protegido ou corrompido."
                )
            
            return full_text
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Erro ao processar PDF. Verifique se o arquivo não está corrompido ou protegido."
            )
    
    def truncate_text_for_analysis(self, text: str) -> str:
        """Trunca texto para análise respeitando o limite"""
        max_length = settings.max_content_length
        
        if len(text) <= max_length:
            return text
        
        # Truncar no limite mas tentar cortar em uma palavra completa
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # Se o último espaço está em uma posição razoável
            truncated = truncated[:last_space]
        
        return truncated + "..."


# Instância global do serviço
file_processor = FileProcessorService()
