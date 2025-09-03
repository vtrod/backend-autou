"""
Aplicação principal FastAPI - AutoU Email Classifier
"""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.api.endpoints import router
from app.models.schemas import ErrorResponse

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    logger.info(f"Modo debug: {settings.debug}")
    logger.info("Sistema de classificação de emails inicializado")
    
    yield
    
    # Shutdown
    logger.info("Encerrando aplicação")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## AutoU Email Classifier API
    
    Sistema inteligente de classificação de emails usando IA para determinar se um email é **produtivo** (requer ação) ou **improdutivo** (informativo/cortesia).
    
    ### Funcionalidades:
    
    * 📧 **Classificação de Emails**: Analisa conteúdo e classifica automaticamente
    * 🤖 **IA Integrada**: Algoritmo inteligente com análise de palavras-chave e padrões
    * 📁 **Upload de Arquivos**: Suporte para arquivos TXT e PDF
    * 💬 **Respostas Automáticas**: Gera sugestões de resposta contextualizadas
    * 📊 **Estatísticas**: Acompanhe métricas de classificação
    * 📈 **Histórico**: Mantenha registro de todas as análises
    
    ### Como usar:
    
    1. **Análise por Texto**: Use `/analyze` com conteúdo direto
    2. **Análise por Arquivo**: Use `/analyze/file` para upload
    3. **Consultar Histórico**: Use `/history` para ver análises anteriores
    4. **Verificar Estatísticas**: Use `/stats` para métricas do sistema
    
    Desenvolvido para o **Desafio AutoU** 🚀
    """,
    contact={
        "name": "Desenvolvedor AutoU",
        "email": "dev@autou.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    debug=settings.debug
)

# Configurar CORS
def get_allowed_origins():
    """Retorna lista de origins permitidas, incluindo Vercel em produção"""
    origins = settings.allowed_origins.copy()
    
    if settings.allow_vercel_origins:
        # Adicionar domínios comuns da Vercel
        vercel_patterns = [
            "https://autou-email-classifier.vercel.app",
            "https://autou-email-classifier-git-main.vercel.app",
            "https://autou-email-classifier-git-master.vercel.app"
        ]
        origins.extend(vercel_patterns)
        
        # Para desenvolvimento, permitir qualquer subdomínio .vercel.app
        # Em produção, você deve especificar domínios exatos por segurança
        if settings.debug:
            origins.append("https://*.vercel.app")
    
    return origins

def vercel_origin_check(origin: str) -> bool:
    """Verifica se origin é de um domínio Vercel válido"""
    if not origin:
        return False
    
    # Permitir localhost sempre
    if "localhost" in origin or "127.0.0.1" in origin:
        return True
    
    # Verificar se é um domínio .vercel.app
    if settings.allow_vercel_origins and origin.endswith(".vercel.app"):
        # Você pode adicionar validações mais específicas aqui se necessário
        return True
    
    return origin in settings.allowed_origins

# Aplicar CORS com validação customizada
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins() if not settings.allow_vercel_origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app$" if settings.allow_vercel_origins else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(router, prefix="/api/v1")

# Documentação customizada
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
        license_info=app.license_info
    )
    
    # Customizar schema
    openapi_schema["info"]["x-logo"] = {
        "url": "https://via.placeholder.com/120x120/007acc/ffffff?text=AutoU"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de todas as requisições"""
    start_time = __import__('time').time()
    
    # Log da requisição
    logger.info(f"Request: {request.method} {request.url}")
    
    # Processar requisição
    response = await call_next(request)
    
    # Log da resposta
    process_time = __import__('time').time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response


# Handler global de exceções
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para exceções HTTP"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=f"Erro {exc.status_code}"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para exceções gerais"""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Erro interno do servidor",
            detail="Ocorreu um erro inesperado. Tente novamente."
        ).dict()
    )


# Endpoint raiz
@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz da API"""
    return {
        "message": f"🚀 {settings.app_name} está funcionando!",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "api_base": "/api/v1"
    }


# Endpoint de informações da API
@app.get("/info", tags=["Info"])
async def api_info():
    """Informações detalhadas da API"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "max_file_size_mb": settings.max_file_size / (1024 * 1024),
        "allowed_file_types": settings.allowed_file_types,
        "max_content_length": settings.max_content_length,
        "confidence_threshold": settings.confidence_threshold,
        "endpoints": {
            "analyze_text": "/api/v1/analyze",
            "analyze_file": "/api/v1/analyze/file",
            "get_analysis": "/api/v1/analysis/{id}",
            "history": "/api/v1/history",
            "stats": "/api/v1/stats",
            "clear_history": "/api/v1/history",
            "health": "/api/v1/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Iniciando servidor na porta {settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
