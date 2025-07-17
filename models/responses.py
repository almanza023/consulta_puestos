from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ScrapingResponse(BaseModel):
    status: str
    message: Optional[str] = None
    nuip: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    total_records: Optional[int] = None
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class PoliceNameResponse(BaseModel):
    status: str
    message: Optional[str] = None
    nuip: Optional[str] = None
    fecha_expedicion: Optional[str] = None
    name: Optional[str] = None
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class MultiplePoliceNameResponse(BaseModel):
    status: str
    total_processed: int
    results: List[Dict[str, Any]]
    file_saved: str
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None
    successful_queries: Optional[int] = None
    failed_queries: Optional[int] = None

class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    created_at: str
    completed_at: Optional[str] = None
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    api_key_configured: bool
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class BalanceResponse(BaseModel):
    balance: float
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class MultipleScrapingResponse(BaseModel):
    status: str
    total_processed: int
    results: List[Dict[str, Any]]
    file_saved: str
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class AsyncJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    check_status_url: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class CombinedResponse(BaseModel):
    """Respuesta para consulta combinada individual"""
    status: str
    message: Optional[str] = None
    nuip: Optional[str] = None
    fecha_expedicion: Optional[str] = None
    registraduria_result: Optional[Dict[str, Any]] = None
    police_result: Optional[Dict[str, Any]] = None
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None

class MultipleCombinedResponse(BaseModel):
    """Respuesta para múltiples consultas combinadas"""
    status: str
    total_processed: int
    results: List[CombinedResponse]
    file_saved: Optional[str] = None
    timestamp: str
    response_time_seconds: Optional[float] = None
    execution_time: Optional[str] = None
    successful_queries: Optional[int] = None
    failed_queries: Optional[int] = None

class CertificadoVigenciaResponse(BaseModel):
    """Modelo para respuesta de certificado de vigencia"""
    status: str
    message: str
    nuip: str
    fecha_expedicion: str
    pdf_file: Optional[str] = None
    captcha_image: Optional[str] = None
    captcha_text: Optional[str] = None
    timestamp: str
    response_time_seconds: float
    execution_time: str
    # Nuevos campos para los datos extraídos del PDF
    cedula_ciudadania: Optional[str] = None
    fecha_expedicion_pdf: Optional[str] = None
    lugar_expedicion: Optional[str] = None
    nombre: Optional[str] = None
    estado: Optional[str] = None
    pdf_data: Optional[Dict[str, Any]] = None

class MultipleCertificadoResponse(BaseModel):
    """Modelo para respuesta de múltiples certificados"""
    status: str
    total_processed: int
    results: List[CertificadoVigenciaResponse]
    file_saved: Optional[str] = None
    timestamp: str
    response_time_seconds: float
    execution_time: str
    successful_queries: int
    failed_queries: int

