from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
import sys
import time
from datetime import datetime
import uuid

# Importar modelos separados
from models import (
    NuipRequest,
    MultipleNuipRequest,
    PoliceNameRequest,
    PoliceQuery,
    MultiplePoliceNameRequest,
    ScrapingResponse,
    PoliceNameResponse,
    MultiplePoliceNameResponse,
    JobStatus,
    HealthResponse,
    BalanceResponse,
    MultipleScrapingResponse,
    AsyncJobResponse,
    ErrorResponse
)

# Importar utilidades
from utils.time_utils import format_execution_time, calculate_response_time, get_current_timestamp

# Importar clases existentes
from config import settings
from registraduria_scraper import RegistraduriaScraperAuto, save_registraduria_results
from police_scraper import PoliciaScraperAuto, save_police_results 

# Crear la aplicación FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# Almacenamiento en memoria para trabajos
jobs_storage: Dict[str, JobStatus] = {}

# Configuración global
API_KEY = os.getenv('APIKEY_2CAPTCHA')
if not API_KEY:
    print("❌ Error: No se encontró la API key de 2captcha")
    sys.exit(1)

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print("🚀 Iniciando Registraduría Scraper API...")
    print(f"🔑 API Key configurada: {API_KEY[:10]}...")

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    start_time = time.time()
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    
    return {
        "message": "Registraduría Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "single_query": "/scrape/single",
            "multiple_query": "/scrape/multiple",
            "async_multiple": "/scrape/async-multiple",
            "police_name_query": "/scrape/police-name",
            "police_multiple_query": "/scrape/police-multiple",
            "police_async_multiple": "/scrape/police-async-multiple",
            "job_status": "/jobs/{job_id}",
            "jobs_list": "/jobs",
            "health": "/health",
            "balance": "/balance"
        },
        "timestamp": get_current_timestamp(),
        "response_time_seconds": response_time_seconds,
        "execution_time": execution_time
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Endpoint de salud de la API"""
    start_time = time.time()
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    
    return HealthResponse(
        status="healthy",
        timestamp=get_current_timestamp(),
        api_key_configured=bool(API_KEY),
        response_time_seconds=response_time_seconds,
        execution_time=execution_time
    )

@app.post("/scrape/single", response_model=ScrapingResponse)
async def scrape_single_nuip(request: NuipRequest):
    """Consulta un solo NUIP de forma síncrona"""
    start_time = time.time()
    
    try:
        scraper = RegistraduriaScraperAuto(API_KEY, headless=True)
        
        try:
            result = scraper.scrape_nuip(request.nuip)
            
            response_time_seconds, execution_time = calculate_response_time(start_time)
            
            return ScrapingResponse(
                status=result.get("status", "unknown"),
                message=result.get("message"),
                nuip=result.get("nuip"),
                data=result.get("data"),
                total_records=result.get("total_records"),
                timestamp=result.get("timestamp", get_current_timestamp()),
                response_time_seconds=response_time_seconds,
                execution_time=execution_time
            )
            
        finally:
            scraper.close()
            
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Error al procesar la consulta: {str(e)}",
                "response_time_seconds": response_time_seconds,
                "execution_time": execution_time
            }
        )

@app.post("/scrape/police-name", response_model=PoliceNameResponse)
async def scrape_police_name(request: PoliceNameRequest):
    """
    Consulta el nombre de una persona por NUIP y fecha de expedición en el sistema de la Policía Nacional
    """
    start_time = time.time()
    
    try:
        scraper = PoliciaScraperAuto(headless=True)
        
        try:
            result = scraper.scrape_name_by_nuip(request.nuip, request.fecha_expedicion)
            
            response_time_seconds, execution_time = calculate_response_time(start_time)
            
            response = PoliceNameResponse(
                status=result.get("status", "unknown"),
                message=result.get("message"),
                nuip=result.get("nuip"),
                fecha_expedicion=result.get("fecha_expedicion"),
                name=result.get("name"),
                timestamp=result.get("timestamp", get_current_timestamp()),
                response_time_seconds=response_time_seconds,
                execution_time=execution_time
            )
            
            if result.get("status") == "success":
                save_police_results(result)
            
            return response
            
        finally:
            scraper.close()
            
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Error al procesar la consulta de nombre: {str(e)}",
                "response_time_seconds": response_time_seconds,
                "execution_time": execution_time
            }
        )

@app.post("/scrape/police-multiple", response_model=MultiplePoliceNameResponse)
async def scrape_multiple_police_names(request: MultiplePoliceNameRequest):
    """Consulta múltiples nombres por NUIP y fecha de expedición de forma síncrona"""
    start_time = time.time()
    
    try:
        if len(request.queries) > 20:
            raise HTTPException(
                status_code=400,
                detail="Máximo 20 consultas por request. Use el endpoint async para consultas más grandes."
            )
        
        scraper = PoliciaScraperAuto(headless=True)
        
        try:
            results = []
            total = len(request.queries)
            successful_count = 0
            failed_count = 0
            
            for i, query in enumerate(request.queries):
                print(f"Procesando consulta {i+1}/{total}: NUIP {query.nuip}")
                result = scraper.scrape_name_by_nuip(query.nuip, query.fecha_expedicion)
                results.append(result)
                
                # Contar resultados exitosos y fallidos
                if result.get("status") == "success":
                    successful_count += 1
                    save_police_results(result)
                else:
                    failed_count += 1
                
                # Delay entre consultas si no es la última
                if i < total - 1:
                    await asyncio.sleep(request.delay)
            
            # Guardar todos los resultados
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"resultados/consultas_policia_multiple_{timestamp}.json"
            save_police_results(results, filename)
            
            response_time_seconds, execution_time = calculate_response_time(start_time)
            
            return MultiplePoliceNameResponse(
                status="completed",
                total_processed=len(results),
                results=results,
                file_saved=filename,
                timestamp=get_current_timestamp(),
                response_time_seconds=response_time_seconds,
                execution_time=execution_time,
                successful_queries=successful_count,
                failed_queries=failed_count
            )
            
        finally:
            scraper.close()
            
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Error al procesar las consultas de policía: {str(e)}",
                "response_time_seconds": response_time_seconds,
                "execution_time": execution_time
            }
        )

@app.post("/scrape/police-async-multiple", response_model=AsyncJobResponse)
async def scrape_multiple_police_names_async(request: MultiplePoliceNameRequest, background_tasks: BackgroundTasks):
    """Consulta múltiples nombres por NUIP y fecha de expedición de forma asíncrona"""
    start_time = time.time()
    
    job_id = str(uuid.uuid4())
    
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        progress={"total": len(request.queries), "completed": 0},
        created_at=get_current_timestamp()
    )
    
    jobs_storage[job_id] = job_status
    
    background_tasks.add_task(
        process_multiple_police_names_background,
        job_id,
        request.queries,
        request.delay,
        start_time
    )
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    
    return AsyncJobResponse(
        job_id=job_id,
        status="accepted",
        message=f"Procesando {len(request.queries)} consultas de policía en segundo plano",
        check_status_url=f"/jobs/{job_id}",
        response_time_seconds=response_time_seconds,
        execution_time=execution_time
    )

@app.post("/scrape/multiple", response_model=MultipleScrapingResponse)
async def scrape_multiple_nuips(request: MultipleNuipRequest):
    """Consulta múltiples NUIPs de forma síncrona"""
    start_time = time.time()
    
    try:
        if len(request.nuips) > 50:
            raise HTTPException(
                status_code=400,
                detail="Máximo 50 NUIPs por consulta. Use el endpoint async para consultas más grandes."
            )
        
        scraper = RegistraduriaScraperAuto(API_KEY, headless=True)
        
        try:
            results = scraper.scrape_multiple_nuips(request.nuips, request.delay)
            filename = save_registraduria_results(results)
            
            response_time_seconds, execution_time = calculate_response_time(start_time)
            
            return MultipleScrapingResponse(
                status="completed",
                total_processed=len(results),
                results=results,
                file_saved=filename,
                timestamp=get_current_timestamp(),
                response_time_seconds=response_time_seconds,
                execution_time=execution_time
            )
            
        finally:
            scraper.close()
            
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Error al procesar las consultas: {str(e)}",
                "response_time_seconds": response_time_seconds,
                "execution_time": execution_time
            }
        )

@app.post("/scrape/async-multiple", response_model=AsyncJobResponse)
async def scrape_multiple_nuips_async(request: MultipleNuipRequest, background_tasks: BackgroundTasks):
    """Consulta múltiples NUIPs de forma asíncrona usando background tasks"""
    start_time = time.time()
    
    job_id = str(uuid.uuid4())
    
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        progress={"total": len(request.nuips), "completed": 0},
        created_at=get_current_timestamp()
    )
    
    jobs_storage[job_id] = job_status
    
    background_tasks.add_task(
        process_multiple_nuips_background,
        job_id,
        request.nuips,
        request.delay,
        start_time
    )
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    
    return AsyncJobResponse(
        job_id=job_id,
        status="accepted",
        message=f"Procesando {len(request.nuips)} NUIPs en segundo plano",
        check_status_url=f"/jobs/{job_id}",
        response_time_seconds=response_time_seconds,
        execution_time=execution_time
    )

async def process_multiple_police_names_background(job_id: str, queries: List[PoliceQuery], delay: int, start_time: float):
    """Función para procesar consultas de policía en segundo plano"""
    try:
        jobs_storage[job_id].status = "running"
        
        scraper = PoliciaScraperAuto(headless=True)
        
        try:
            results = []
            total = len(queries)
            successful_count = 0
            failed_count = 0
            
            for i, query in enumerate(queries):
                print(f"Procesando consulta {i+1}/{total}: NUIP {query.nuip}")
                
                result = scraper.scrape_name_by_nuip(query.nuip, query.fecha_expedicion)
                results.append(result)
                
                # Contar resultados exitosos y fallidos
                if result.get("status") == "success":
                    successful_count += 1
                    save_police_results(result)
                else:
                    failed_count += 1
                
                # Actualizar progreso
                jobs_storage[job_id].progress = {
                    "total": total,
                    "completed": i + 1,
                    "current_query": f"NUIP: {query.nuip}, Fecha: {query.fecha_expedicion}",
                    "successful": successful_count,
                    "failed": failed_count
                }
                
                # Delay entre consultas si no es la última
                if i < total - 1:
                    await asyncio.sleep(delay)
            
            # Guardar todos los resultados
            filename = f"resultados/async_police_results_{job_id}.json"
            save_police_results(results, filename)
            
            response_time_seconds, execution_time = calculate_response_time(start_time)
            
            jobs_storage[job_id].status = "completed"
            jobs_storage[job_id].result = {
                "total_processed": len(results),
                "results": results,
                "file_saved": filename,
                "successful_queries": successful_count,
                "failed_queries": failed_count
            }
            jobs_storage[job_id].completed_at = get_current_timestamp()
            jobs_storage[job_id].response_time_seconds = response_time_seconds
            jobs_storage[job_id].execution_time = execution_time
            
        finally:
            scraper.close()
            
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        jobs_storage[job_id].status = "failed"
        jobs_storage[job_id].result = {"error": str(e)}
        jobs_storage[job_id].completed_at = get_current_timestamp()
        jobs_storage[job_id].response_time_seconds = response_time_seconds
        jobs_storage[job_id].execution_time = execution_time
        
        print(f"❌ Error en procesamiento background para job {job_id}: {e}")

async def process_multiple_nuips_background(job_id: str, nuips: List[str], delay: int, start_time: float):
    """Función para procesar NUIPs en segundo plano"""
    try:
        jobs_storage[job_id].status = "running"
        
        scraper = RegistraduriaScraperAuto(API_KEY, headless=True)
        
        try:
            results = []
            total = len(nuips)
            
            for i, nuip in enumerate(nuips):
                result = scraper.scrape_nuip(nuip)
                results.append(result)
                
                jobs_storage[job_id].progress = {
                    "total": total,
                    "completed": i + 1,
                    "current_nuip": nuip
                }
                
                if i < total - 1:
                    await asyncio.sleep(delay)
            
            filename = save_registraduria_results(results, f"resultados/async_results_{job_id}.json")
            
            response_time_seconds, execution_time = calculate_response_time(start_time)
            
            jobs_storage[job_id].status = "completed"
            jobs_storage[job_id].result = {
                "total_processed": len(results),
                "results": results,
                "file_saved": filename
            }
            jobs_storage[job_id].completed_at = get_current_timestamp()
            jobs_storage[job_id].response_time_seconds = response_time_seconds
            jobs_storage[job_id].execution_time = execution_time
            
        finally:
            scraper.close()
            
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        jobs_storage[job_id].status = "failed"
        jobs_storage[job_id].result = {"error": str(e)}
        jobs_storage[job_id].completed_at = get_current_timestamp()
        jobs_storage[job_id].response_time_seconds = response_time_seconds
        jobs_storage[job_id].execution_time = execution_time

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Obtiene el estado de un trabajo asíncrono"""
    start_time = time.time()
    
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    job_data = jobs_storage[job_id].dict()
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    job_data["api_response_time_seconds"] = response_time_seconds
    job_data["api_execution_time"] = execution_time
    
    return job_data

@app.get("/jobs")
async def list_jobs():
    """Lista todos los trabajos"""
    start_time = time.time()
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    
    return {
        "total_jobs": len(jobs_storage),
        "jobs": list(jobs_storage.values()),
        "response_time_seconds": response_time_seconds,
        "execution_time": execution_time
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Elimina un trabajo del almacenamiento"""
    start_time = time.time()
    
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    del jobs_storage[job_id]
    
    response_time_seconds, execution_time = calculate_response_time(start_time)
    
    return {
        "message": "Trabajo eliminado exitosamente",
        "response_time_seconds": response_time_seconds,
        "execution_time": execution_time
    }

@app.get("/balance", response_model=BalanceResponse)
async def get_2captcha_balance():
    """Obtiene el balance de la cuenta de 2captcha"""
    start_time = time.time()
    
    try:
        from main import TwoCaptchaSolver
        solver = TwoCaptchaSolver(API_KEY)
        balance = solver.get_balance()
        
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        return BalanceResponse(
            balance=balance,
            response_time_seconds=response_time_seconds,
            execution_time=execution_time
        )
    except Exception as e:
        response_time_seconds, execution_time = calculate_response_time(start_time)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Error al obtener balance: {str(e)}",
                "response_time_seconds": response_time_seconds,
                "execution_time": execution_time
            }
        )

# Manejo de errores global actualizado
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc),
            "timestamp": get_current_timestamp(),
            "response_time_seconds": 0.0,
            "execution_time": "0ms"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )