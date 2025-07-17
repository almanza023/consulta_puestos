from .requests import (
    NuipRequest, 
    MultipleNuipRequest, 
    PoliceNameRequest,
    PoliceQuery,
    MultiplePoliceNameRequest,
    CombinedQuery,
    MultipleCombinedRequest,
    CertificadoVigenciaRequest,
    MultipleCertificadoRequest
    
)
from .responses import (
    ScrapingResponse, 
    PoliceNameResponse,
    MultiplePoliceNameResponse,
    JobStatus, 
    HealthResponse, 
    BalanceResponse,
    MultipleScrapingResponse,
    CombinedResponse,
    MultipleCombinedResponse,
    AsyncJobResponse,
    CertificadoVigenciaResponse,
    MultipleCertificadoResponse,
    ErrorResponse
)

__all__ = [
    # Request models
    'NuipRequest',
    'MultipleNuipRequest', 
    'PoliceNameRequest',
    'PoliceQuery',
    'MultiplePoliceNameRequest',
    'CombinedQuery',
    'MultipleCombinedRequest',
    'CertificadoVigenciaRequest',
    'MultipleCertificadoRequest',
    
    
    # Response models
    'ScrapingResponse',
    'PoliceNameResponse',
    'MultiplePoliceNameResponse',
    'JobStatus',
    'HealthResponse',
    'BalanceResponse',
    'MultipleScrapingResponse',
    'AsyncJobResponse',
    'CombinedResponse',
    'MultipleCombinedResponse',
    'CertificadoVigenciaResponse',
    'MultipleCertificadoResponse',
    'ErrorResponse'
]