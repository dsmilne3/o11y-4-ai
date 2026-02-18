"""
Main FastAPI application for AI observability demo.

This module orchestrates all AI services (OpenAI, vector database, local models)
with comprehensive OpenTelemetry instrumentation and Prometheus metrics exposure.
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes

import os
from dotenv import load_dotenv

# Initialize observability FIRST
from .observability import initialize_observability

# Import our services
from .openai_service import openai_service
from .vector_db_service import vector_db_service
from .local_model_service import local_model_service

load_dotenv()

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Application metrics
request_duration = meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration",
    unit="s"
)

request_count = meter.create_counter(
    name="http_requests_total",
    description="Total HTTP requests"
)

active_requests = meter.create_up_down_counter(
    name="http_requests_active",
    description="Active HTTP requests"
)

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    message: str = Field(..., description="The message to send to the chat model")
    model: Optional[str] = Field(None, description="Model to use (optional)")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

class EmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts to embed")
    model: Optional[str] = Field(None, description="Embedding model to use")
    store_in_vector_db: bool = Field(True, description="Whether to store embeddings in vector database")
    metadata: Optional[List[Dict[str, Any]]] = Field(None, description="Metadata for each text")
    user_id: Optional[str] = Field(None, description="User identifier")

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    n_results: int = Field(5, gt=0, le=100, description="Number of results to return")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")
    user_id: Optional[str] = Field(None, description="User identifier")

class LocalInferenceRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for local model")
    max_length: int = Field(100, gt=0, le=512, description="Maximum length of generated text")
    temperature: float = Field(0.7, ge=0, le=2, description="Sampling temperature")
    num_sequences: int = Field(1, gt=0, le=5, description="Number of sequences to generate")
    user_id: Optional[str] = Field(None, description="User identifier")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting AI Observability Demo application")
    
    # Initialize services (they're already initialized in their modules)
    logger.info("All services initialized")
    
    yield
    
    logger.info("Shutting down AI Observability Demo application")

# Create FastAPI app
app = FastAPI(
    title="AI Observability Demo",
    description="Comprehensive AI observability demo with OpenTelemetry, Grafana, and multiple AI services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_observability_middleware(request, call_next):
    """Add comprehensive observability to all HTTP requests."""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Increment active requests
    active_requests.add(1)
    
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        attributes={
            SpanAttributes.HTTP_METHOD: request.method,
            SpanAttributes.HTTP_URL: str(request.url),
            SpanAttributes.HTTP_ROUTE: request.url.path,
            SpanAttributes.HTTP_USER_AGENT: request.headers.get("user-agent", ""),
            "request.id": request_id,
            "request.client_ip": request.client.host if request.client else "unknown"
        }
    ) as span:
        
        try:
            # Add request ID to logger context
            logger.bind(request_id=request_id)
            
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Update span with response info
            span.set_attributes({
                SpanAttributes.HTTP_STATUS_CODE: response.status_code,
                "response.duration_seconds": duration
            })
            
            # Record metrics
            request_duration.record(
                duration,
                attributes={
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            request_count.add(
                1,
                attributes={
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            # Set span status
            if response.status_code >= 400:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
            else:
                span.set_status(Status(StatusCode.OK))
            
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                request_id=request_id
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            request_count.add(
                1,
                attributes={
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": "500"
                }
            )
            
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=duration,
                request_id=request_id
            )
            
            raise
        
        finally:
            # Decrement active requests
            active_requests.add(-1)

@app.get("/health")
async def health_check():
    """Health check endpoint with service status."""
    with tracer.start_as_current_span("health_check") as span:
        
        try:
            # Check vector database
            vector_stats = await vector_db_service.get_collection_stats()
            
            # Check local model
            model_info = await local_model_service.get_model_info()
            
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "services": {
                    "openai_service": {"status": "available"},
                    "vector_database": {
                        "status": "available",
                        "document_count": vector_stats["document_count"]
                    },
                    "local_model": {
                        "status": "available",
                        "model_name": model_info["model_name"],
                        "device": model_info["device"]
                    }
                }
            }
            
            span.set_status(Status(StatusCode.OK))
            return health_data
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            
            health_data = {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
            
            return JSONResponse(
                status_code=503,
                content=health_data
            )

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Serve a no-op favicon to avoid 404 noise from browsers
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204, media_type="image/x-icon")

@app.post("/chat")
async def chat_completion(request: ChatRequest):
    """Chat completion using OpenAI API."""
    with tracer.start_as_current_span(
        "api.chat_completion",
        attributes={
            "request.model": request.model or "default",
            "request.temperature": float(request.temperature),
            "request.user_id": request.user_id or "unknown"
        }
    ) as span:
        
        try:
            # Format message for OpenAI
            messages = [{"role": "user", "content": request.message}]
            
            # Call OpenAI service
            result = await openai_service.chat_completion(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                user_id=request.user_id,
                session_id=request.session_id
            )
            
            span.set_attributes({
                "response.tokens_used": result["usage"]["total_tokens"],
                "response.cost_usd": result["cost_usd"]
            })
            
            return {
                "response": result["response"],
                "metadata": {
                    "model": result["model"],
                    "usage": result["usage"],
                    "cost_usd": result["cost_usd"],
                    "duration_seconds": result["duration_seconds"],
                    "finish_reason": result["finish_reason"]
                }
            }
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Chat completion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed")
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings and optionally store in vector database."""
    with tracer.start_as_current_span(
        "api.create_embeddings",
        attributes={
            "request.text_count": len(request.texts),
            "request.store_in_db": request.store_in_vector_db,
            "request.user_id": request.user_id or "unknown"
        }
    ) as span:
        
        try:
            # Create embeddings
            embedding_result = await openai_service.create_embeddings(
                texts=request.texts,
                model=request.model,
                user_id=request.user_id
            )
            
            embeddings = embedding_result["embeddings"]
            vector_result = None
            
            # Store in vector database if requested
            if request.store_in_vector_db:
                vector_result = await vector_db_service.add_embeddings(
                    embeddings=embeddings,
                    documents=request.texts,
                    metadatas=request.metadata,
                    user_id=request.user_id
                )
            
            span.set_attributes({
                "response.embeddings_created": len(embeddings),
                "response.stored_in_db": request.store_in_vector_db,
                "response.cost_usd": embedding_result["cost_usd"]
            })
            
            return {
                "embeddings_created": len(embeddings),
                "stored_in_vector_db": request.store_in_vector_db,
                "metadata": {
                    "model": embedding_result["model"],
                    "usage": embedding_result["usage"],
                    "cost_usd": embedding_result["cost_usd"],
                    "duration_seconds": embedding_result["duration_seconds"]
                },
                "vector_db_result": vector_result
            }
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Embedding creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def vector_search(request: SearchRequest):
    """Perform vector similarity search."""
    with tracer.start_as_current_span(
        "api.vector_search",
        attributes={
            "request.n_results": request.n_results,
            "request.has_filter": request.filter_metadata is not None,
            "request.user_id": request.user_id or "unknown"
        }
    ) as span:
        
        try:
            # First, create embedding for the query
            embedding_result = await openai_service.create_embeddings(
                texts=[request.query],
                user_id=request.user_id
            )
            
            query_embedding = embedding_result["embeddings"][0]
            
            # Perform search
            search_result = await vector_db_service.similarity_search(
                query_embedding=query_embedding,
                n_results=request.n_results,
                where=request.filter_metadata,
                user_id=request.user_id
            )
            
            span.set_attributes({
                "response.results_found": search_result["count"],
                "response.embedding_cost_usd": embedding_result["cost_usd"]
            })
            
            return {
                "query": request.query,
                "results": search_result["results"],
                "count": search_result["count"],
                "metadata": {
                    "query_embedding_cost_usd": embedding_result["cost_usd"],
                    "search_duration_seconds": search_result["duration_seconds"],
                    "total_duration_seconds": embedding_result["duration_seconds"] + search_result["duration_seconds"]
                }
            }
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Vector search failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/local-inference")
async def local_model_inference(request: LocalInferenceRequest):
    """Generate text using local GPU model."""
    with tracer.start_as_current_span(
        "api.local_inference",
        attributes={
            "request.prompt_length": len(request.prompt),
            "request.max_length": request.max_length,
            "request.temperature": request.temperature,
            "request.user_id": request.user_id or "unknown"
        }
    ) as span:
        
        try:
            # Generate text using local model
            result = await local_model_service.generate_text(
                prompt=request.prompt,
                max_length=request.max_length,
                temperature=request.temperature,
                num_return_sequences=request.num_sequences,
                user_id=request.user_id
            )
            
            span.set_attributes({
                "response.texts_generated": len(result["generated_texts"]),
                "response.tokens_generated": result["usage"]["completion_tokens"],
                "response.tokens_per_second": result["performance"]["tokens_per_second"]
            })
            
            return {
                "generated_texts": result["generated_texts"],
                "metadata": {
                    "model": result["model"],
                    "device": result["device"],
                    "usage": result["usage"],
                    "performance": result["performance"]
                }
            }
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Local inference failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/full-pipeline")
async def full_ai_pipeline(
    background_tasks: BackgroundTasks,
    query: str,
    store_results: bool = True,
    user_id: Optional[str] = None
):
    """
    Demonstrate full AI pipeline: 
    1. Generate response with OpenAI
    2. Create embeddings
    3. Store in vector DB
    4. Generate alternative with local model
    5. Perform similarity search
    """
    with tracer.start_as_current_span(
        "api.full_pipeline",
        attributes={
            "request.query_length": len(query),
            "request.store_results": store_results,
            "request.user_id": user_id or "unknown"
        }
    ) as span:
        
        try:
            pipeline_start = time.time()
            results = {}
            
            # Step 1: OpenAI chat completion
            logger.info("Step 1: OpenAI chat completion")
            chat_result = await openai_service.chat_completion(
                messages=[{"role": "user", "content": query}],
                user_id=user_id
            )
            results["openai_response"] = chat_result
            
            # Step 2: Create embeddings for query and response
            logger.info("Step 2: Creating embeddings")
            texts_to_embed = [query, chat_result["response"]]
            embedding_result = await openai_service.create_embeddings(
                texts=texts_to_embed,
                user_id=user_id
            )
            results["embeddings"] = embedding_result
            
            # Step 3: Store in vector database
            if store_results:
                logger.info("Step 3: Storing in vector database")
                vector_result = await vector_db_service.add_embeddings(
                    embeddings=embedding_result["embeddings"],
                    documents=texts_to_embed,
                    metadatas=[
                        {"type": "query", "user_id": user_id or "unknown"},
                        {"type": "openai_response", "user_id": user_id or "unknown"}
                    ],
                    user_id=user_id
                )
                results["vector_storage"] = vector_result
            
            # Step 4: Generate with local model
            logger.info("Step 4: Local model generation")
            local_result = await local_model_service.generate_text(
                prompt=query,
                max_length=150,
                user_id=user_id
            )
            results["local_model_response"] = local_result
            
            # Step 5: Similarity search
            logger.info("Step 5: Similarity search")
            search_result = await vector_db_service.similarity_search(
                query_embedding=embedding_result["embeddings"][0],
                n_results=3,
                user_id=user_id
            )
            results["similarity_search"] = search_result
            
            total_duration = time.time() - pipeline_start
            
            # Calculate total costs
            total_cost = (
                chat_result["cost_usd"] + 
                embedding_result["cost_usd"]
            )
            
            span.set_attributes({
                "pipeline.total_duration_seconds": total_duration,
                "pipeline.total_cost_usd": total_cost,
                "pipeline.steps_completed": 5
            })
            
            return {
                "query": query,
                "results": results,
                "summary": {
                    "total_duration_seconds": total_duration,
                    "total_cost_usd": total_cost,
                    "steps_completed": 5,
                    "openai_tokens_used": chat_result["usage"]["total_tokens"] + embedding_result["usage"]["total_tokens"],
                    "local_tokens_generated": local_result["usage"]["completion_tokens"],
                    "documents_stored": len(texts_to_embed) if store_results else 0,
                    "search_results_found": search_result["count"]
                }
            }
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Full pipeline failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_system_stats():
    """Get comprehensive system and service statistics."""
    with tracer.start_as_current_span("api.get_stats") as span:
        try:
            # Get vector DB stats
            vector_stats = await vector_db_service.get_collection_stats()
            
            # Get model info
            model_info = await local_model_service.get_model_info()
            
            stats = {
                "vector_database": vector_stats,
                "local_model": model_info,
                "system": {
                    "timestamp": time.time(),
                    "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
                }
            }
            
            return stats
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            logger.error(f"Failed to get stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8080"))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )