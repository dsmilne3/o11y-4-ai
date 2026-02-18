"""
Vector database service using ChromaDB with OpenTelemetry instrumentation.

This module provides vector storage and retrieval capabilities with comprehensive
observability for embedding operations, similarity searches, and database performance.
"""

import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
import structlog
import chromadb
from chromadb.config import Settings
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes
import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics
vector_operation_duration = meter.create_histogram(
    name="vector_operation_duration_seconds",
    description="Duration of vector database operations",
    unit="s"
)

vector_operation_count = meter.create_counter(
    name="vector_operations_total",
    description="Total number of vector database operations"
)

vector_storage_size = meter.create_up_down_counter(
    name="vector_storage_documents_total",
    description="Total number of documents in vector storage"
)

vector_search_results = meter.create_histogram(
    name="vector_search_results_count",
    description="Number of results returned by vector searches"
)

vector_errors = meter.create_counter(
    name="vector_errors_total",
    description="Total number of vector database errors"
)

class VectorDatabaseService:
    """ChromaDB vector database service with comprehensive observability."""
    
    def __init__(self):
        self.persist_directory = os.getenv(
            "CHROMA_PERSIST_DIRECTORY", 
            "./data/chroma_db"
        )
        self.collection_name = os.getenv(
            "CHROMA_COLLECTION_NAME", 
            "ai_demo_collection"
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "AI demo embeddings collection"}
        )
        
        logger.info(
            "Vector database initialized",
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
            document_count=self.collection.count()
        )
    
    async def add_embeddings(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add embeddings to the vector database.
        
        Args:
            embeddings: List of embedding vectors
            documents: List of source documents
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document
            user_id: User identifier for tracking
            
        Returns:
            Dict containing operation results
        """
        start_time = time.time()
        
        with tracer.start_as_current_span(
            "vector.add_embeddings",
            attributes={
                "db.system": "chromadb",
                "db.collection.name": self.collection_name,
                "vector.document_count": len(documents),
                "vector.embedding_dimension": len(embeddings[0]) if embeddings else 0,
                "vector.user_id": user_id or "unknown"
            }
        ) as span:
            
            try:
                # Generate IDs if not provided
                if ids is None:
                    ids = [str(uuid.uuid4()) for _ in documents]
                
                # Default metadata if not provided
                if metadatas is None:
                    metadatas = [{"user_id": user_id or "unknown"} for _ in documents]
                else:
                    # Ensure user_id is in metadata
                    for metadata in metadatas:
                        metadata["user_id"] = user_id or "unknown"
                
                logger.info(
                    "Adding embeddings to vector database",
                    collection=self.collection_name,
                    document_count=len(documents),
                    embedding_dimension=len(embeddings[0]) if embeddings else 0,
                    user_id=user_id
                )
                
                # Add to collection
                self.collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                duration = time.time() - start_time
                new_count = self.collection.count()
                
                # Update span attributes
                span.set_attributes({
                    "vector.operation_result.documents_added": len(documents),
                    "vector.collection.total_documents": new_count,
                    "vector.operation_result.ids": ids[:5]  # First 5 IDs for debugging
                })
                
                # Record metrics
                vector_operation_duration.record(
                    duration,
                    attributes={
                        "operation": "add_embeddings",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                vector_operation_count.add(
                    1,
                    attributes={
                        "operation": "add_embeddings",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "status": "success",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                vector_storage_size.add(
                    len(documents),
                    attributes={
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                span.set_status(Status(StatusCode.OK))
                
                logger.info(
                    "Embeddings added successfully",
                    collection=self.collection_name,
                    documents_added=len(documents),
                    total_documents=new_count,
                    duration=duration,
                    user_id=user_id
                )
                
                return {
                    "documents_added": len(documents),
                    "total_documents": new_count,
                    "ids": ids,
                    "duration_seconds": duration
                }
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metrics
                vector_errors.add(
                    1,
                    attributes={
                        "operation": "add_embeddings",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "error_type": type(e).__name__,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                vector_operation_count.add(
                    1,
                    attributes={
                        "operation": "add_embeddings",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "status": "error",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                logger.error(
                    "Failed to add embeddings",
                    collection=self.collection_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration=duration
                )
                
                raise
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform similarity search in the vector database.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter
            user_id: User identifier for tracking
            
        Returns:
            Dict containing search results and metadata
        """
        start_time = time.time()
        
        with tracer.start_as_current_span(
            "vector.similarity_search",
            attributes={
                "db.system": "chromadb",
                "db.collection.name": self.collection_name,
                "vector.query.embedding_dimension": len(query_embedding),
                "vector.query.n_results": n_results,
                "vector.query.has_filter": where is not None,
                "vector.user_id": user_id or "unknown"
            }
        ) as span:
            
            try:
                logger.info(
                    "Performing similarity search",
                    collection=self.collection_name,
                    n_results=n_results,
                    has_filter=where is not None,
                    user_id=user_id
                )
                
                # Perform search
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where,
                    include=["documents", "metadatas", "distances"]
                )
                
                duration = time.time() - start_time
                actual_results = len(results["ids"][0]) if results["ids"] else 0
                
                # Calculate similarity scores from distances
                distances = results["distances"][0] if results["distances"] else []
                similarities = [1 / (1 + dist) for dist in distances]  # Simple similarity calculation
                
                # Update span attributes
                span.set_attributes({
                    "vector.search_result.count": actual_results,
                    "vector.search_result.max_similarity": max(similarities) if similarities else 0,
                    "vector.search_result.min_similarity": min(similarities) if similarities else 0,
                    "vector.search_result.avg_distance": sum(distances) / len(distances) if distances else 0
                })
                
                # Record metrics
                vector_operation_duration.record(
                    duration,
                    attributes={
                        "operation": "similarity_search",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                vector_operation_count.add(
                    1,
                    attributes={
                        "operation": "similarity_search",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "status": "success",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                vector_search_results.record(
                    actual_results,
                    attributes={
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                span.set_status(Status(StatusCode.OK))
                
                logger.info(
                    "Similarity search completed",
                    collection=self.collection_name,
                    results_count=actual_results,
                    duration=duration,
                    max_similarity=max(similarities) if similarities else 0
                )
                
                # Format results
                formatted_results = []
                for i in range(actual_results):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": distances[i],
                        "similarity": similarities[i]
                    })
                
                return {
                    "results": formatted_results,
                    "count": actual_results,
                    "duration_seconds": duration,
                    "query_metadata": {
                        "n_results_requested": n_results,
                        "filter_applied": where is not None,
                        "embedding_dimension": len(query_embedding)
                    }
                }
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metrics
                vector_errors.add(
                    1,
                    attributes={
                        "operation": "similarity_search",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "error_type": type(e).__name__,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                vector_operation_count.add(
                    1,
                    attributes={
                        "operation": "similarity_search",
                        "db_system": "chromadb",
                        "collection": self.collection_name,
                        "status": "error",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                logger.error(
                    "Similarity search failed",
                    collection=self.collection_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration=duration
                )
                
                raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        start_time = time.time()
        
        with tracer.start_as_current_span(
            "vector.get_stats",
            attributes={
                "db.system": "chromadb",
                "db.collection.name": self.collection_name
            }
        ) as span:
            
            try:
                count = self.collection.count()
                duration = time.time() - start_time
                
                span.set_attributes({
                    "vector.collection.document_count": count
                })
                
                logger.info(
                    "Retrieved collection stats",
                    collection=self.collection_name,
                    document_count=count,
                    duration=duration
                )
                
                return {
                    "collection_name": self.collection_name,
                    "document_count": count,
                    "persist_directory": self.persist_directory
                }
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error("Failed to get collection stats", error=str(e))
                raise

# Global service instance
vector_db_service = VectorDatabaseService()