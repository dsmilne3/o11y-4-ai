"""
OpenAI API service with comprehensive OpenTelemetry instrumentation.

This module provides LLM observability following OpenTelemetry GenAI semantic conventions
for AI/ML workloads, including token tracking, cost calculation, and performance metrics.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
import structlog
from openai import AsyncOpenAI
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes

# GenAI Semantic Conventions
# Reference: https://opentelemetry.io/docs/specs/semconv/gen-ai/
class GenAIAttributes:
    """OpenTelemetry GenAI Semantic Conventions"""
    SYSTEM = "gen_ai.system"
    REQUEST_MODEL = "gen_ai.request.model"
    REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    REQUEST_TOP_P = "gen_ai.request.top_p"
    RESPONSE_MODEL = "gen_ai.response.model"
    RESPONSE_ID = "gen_ai.response.id"
    RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    OPERATION_NAME = "gen_ai.operation.name"
    
    # Custom extensions for cost tracking
    TOKEN_COST = "gen_ai.token.cost"
import os
from dotenv import load_dotenv

# Initialize observability FIRST
from .observability import run_eval

load_dotenv()

# OpenLIT evaluation imports - create instance later after env is loaded
try:
    from openlit.evals import All
    OPENLIT_AVAILABLE = True
except ImportError:
    All = None
    OPENLIT_AVAILABLE = False

logger = structlog.get_logger(__name__)

# Create OpenLIT evals instance after environment is loaded
openlit_evals = None
if OPENLIT_AVAILABLE and All:
    try:
        openlit_evals = All(collect_metrics=True)
    except Exception as e:
        logger.warning(f"Failed to create OpenLIT evals: {e}")
        OPENLIT_AVAILABLE = False
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics using GenAI semantic conventions
gen_ai_client_operation_duration = meter.create_histogram(
    name="gen_ai.client.operation.duration",
    description="Duration of GenAI operations",
    unit="s"
)

gen_ai_client_token_usage = meter.create_histogram(
    name="gen_ai.client.token.usage",
    description="Token usage for GenAI operations",
    unit="token"
)

gen_ai_client_operation_count = meter.create_counter(
    name="gen_ai.client.operation.count",
    description="Total number of GenAI operations"
)

gen_ai_client_operation_cost = meter.create_counter(
    name="gen_ai.client.operation.cost",
    description="Cost of GenAI operations",
    unit="USD"
)

# Additional metrics to match OpenLIT
gen_ai_server_time_to_first_token = meter.create_histogram(
    name="gen_ai.server.time_to_first_token",
    description="Time to first token for streaming responses",
    unit="s"
)

gen_ai_server_time_per_output_token = meter.create_histogram(
    name="gen_ai.server.time_per_output_token",
    description="Average time per output token",
    unit="s"
)

gen_ai_usage_cost = meter.create_histogram(
    name="gen_ai.usage.cost",
    description="Cost distribution for GenAI operations",
    unit="USD"
)

gen_ai_usage_input_tokens = meter.create_counter(
    name="gen_ai.usage.input_tokens",
    description="Total input tokens consumed",
    unit="token"
)

gen_ai_usage_output_tokens = meter.create_counter(
    name="gen_ai.usage.output_tokens",
    description="Total output tokens generated",
    unit="token"
)

gen_ai_total_requests = meter.create_counter(
    name="gen_ai.total_requests",
    description="Total number of GenAI requests"
)

class OpenAIService:
    """OpenAI API service with comprehensive observability."""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
        
        # Token pricing (per 1K tokens) - update these based on current OpenAI pricing
        self.pricing = {
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "text-embedding-ada-002": {"input": 0.0001, "output": 0.0}
        }
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int = 0) -> float:
        """Calculate the cost of an API call."""
        if model not in self.pricing:
            logger.warning(f"Unknown model pricing: {model}")
            return 0.0
        
        pricing = self.pricing[model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate chat completion with full observability.
        
        Args:
            messages: List of chat messages
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            user_id: User identifier for tracking
            session_id: Session identifier for tracking
            
        Returns:
            Dict containing response and metadata
        """
        model = model or self.default_model
        start_time = time.time()
        
        with tracer.start_as_current_span(
            "gen_ai.chat.completions",
            attributes={
                GenAIAttributes.SYSTEM: "openai",
                GenAIAttributes.REQUEST_MODEL: model,
                GenAIAttributes.REQUEST_TEMPERATURE: temperature,
                GenAIAttributes.REQUEST_MAX_TOKENS: max_tokens or -1,
                GenAIAttributes.OPERATION_NAME: "chat",
                "user_id": user_id or "unknown",
                "session_id": session_id or "unknown",
                "message_count": len(messages)
            }
        ) as span:
            
            try:
                logger.info(
                    "Starting chat completion",
                    model=model,
                    message_count=len(messages),
                    user_id=user_id,
                    session_id=session_id
                )
                
                # Record input messages as span events
                for i, message in enumerate(messages):
                    span.add_event(
                        f"input_message_{i}",
                        attributes={
                            "message.role": message.get("role", "unknown"),
                            "message.content_length": len(message.get("content", ""))
                        }
                    )
                
                # Make OpenAI API call
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Extract response data
                completion = response.choices[0].message.content
                usage = response.usage
                finish_reason = response.choices[0].finish_reason
                
                # Calculate metrics
                duration = time.time() - start_time
                input_tokens = usage.prompt_tokens if usage else 0
                output_tokens = usage.completion_tokens if usage else 0
                total_tokens = usage.total_tokens if usage else 0
                cost = self._calculate_cost(model, input_tokens, output_tokens)
                
                # Calculate time per output token (approximation for non-streaming)
                time_per_token = duration / output_tokens if output_tokens > 0 else 0
                
                # Get actual response model (may differ from request model)
                response_model = getattr(response, 'model', model)
                
                # Update span attributes with response data
                span.set_attributes({
                    GenAIAttributes.RESPONSE_MODEL: response_model,
                    GenAIAttributes.RESPONSE_ID: response.id,
                    GenAIAttributes.RESPONSE_FINISH_REASONS: [finish_reason],
                    GenAIAttributes.USAGE_INPUT_TOKENS: input_tokens,
                    GenAIAttributes.USAGE_OUTPUT_TOKENS: output_tokens,
                    GenAIAttributes.TOKEN_COST: cost,
                    "response.characters": len(completion or ""),
                    "server.address": "api.openai.com",
                    "server.port": 443
                })
                
                # Common metric attributes matching OpenLIT
                common_attrs = {
                    GenAIAttributes.SYSTEM: "openai",
                    GenAIAttributes.REQUEST_MODEL: model,
                    GenAIAttributes.RESPONSE_MODEL: response_model,
                    GenAIAttributes.OPERATION_NAME: "chat",
                    "server_address": "api.openai.com",
                    "server_port": 443,
                    "telemetry_sdk_name": "opentelemetry"
                }
                
                # Record metrics using GenAI conventions
                gen_ai_client_operation_duration.record(duration, attributes=common_attrs)
                
                # Token usage with type differentiation (Histogram as per GenAI spec)
                gen_ai_client_token_usage.record(
                    input_tokens,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        "gen_ai.token.type": "input",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                gen_ai_client_token_usage.record(
                    output_tokens,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        "gen_ai.token.type": "output",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                # Total token counters matching OpenLIT
                gen_ai_usage_input_tokens.add(input_tokens, attributes=common_attrs)
                gen_ai_usage_output_tokens.add(output_tokens, attributes=common_attrs)
                
                # Operation count
                gen_ai_client_operation_count.add(
                    1,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        GenAIAttributes.OPERATION_NAME: "chat",
                        "status": "success",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                # Total requests counter
                gen_ai_total_requests.add(1, attributes=common_attrs)
                
                # Cost tracking (both counter and histogram)
                gen_ai_client_operation_cost.add(
                    cost,
                    attributes={
                        "model": model,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                gen_ai_usage_cost.record(cost, attributes=common_attrs)
                
                # Time per output token
                if output_tokens > 0:
                    gen_ai_server_time_per_output_token.record(time_per_token, attributes=common_attrs)
                
                span.set_status(Status(StatusCode.OK))
                
                logger.info(
                    "Chat completion successful",
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    duration=duration,
                    cost=cost,
                    finish_reason=finish_reason
                )
                
                # --- Eval Instrumentation ---
                # For demo: use the prompt as reference (exact match), real evals should use a dataset
                eval_result = run_eval(completion, messages[0]["content"], user_id=user_id, 
                                     system="openai", operation="chat", model=model)
                
                # OpenLIT evaluation (LLM-as-a-Judge)
                openlit_eval_result = None
                if OPENLIT_AVAILABLE and openlit_evals and completion:
                    try:
                        # Provide the user prompt as context for evaluation
                        contexts = [messages[0]["content"]] if messages else None
                        openlit_eval_result = openlit_evals.measure(
                            prompt=messages[0]["content"] if messages else "",
                            contexts=contexts,
                            text=completion
                        )
                        logger.info("OpenLIT evaluation completed", result=openlit_eval_result)
                    except Exception as e:
                        logger.warning("OpenLIT evaluation failed", error=str(e))

                return {
                    "response": completion,
                    "model": model,
                    "usage": {
                        "prompt_tokens": input_tokens,
                        "completion_tokens": output_tokens,
                        "total_tokens": total_tokens
                    },
                    "finish_reason": finish_reason,
                    "cost_usd": cost,
                    "duration_seconds": duration,
                    "eval": eval_result,
                    "openlit_eval": openlit_eval_result
                }
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metrics
                gen_ai_client_operation_count.add(
                    1,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        GenAIAttributes.OPERATION_NAME: "chat",
                        "status": "error",
                        "error_type": type(e).__name__,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                logger.error(
                    "Chat completion failed",
                    model=model,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration=duration
                )
                
                raise
    
    async def create_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create embeddings with observability.
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use
            user_id: User identifier
            
        Returns:
            Dict containing embeddings and metadata
        """
        model = model or self.embedding_model
        start_time = time.time()
        
        with tracer.start_as_current_span(
            "gen_ai.embeddings",
            attributes={
                GenAIAttributes.SYSTEM: "openai",
                GenAIAttributes.REQUEST_MODEL: model,
                GenAIAttributes.OPERATION_NAME: "embeddings",
                "user_id": user_id or "unknown",
                "text_count": len(texts),
                "total_characters": sum(len(text) for text in texts)
            }
        ) as span:
            
            try:
                logger.info(
                    "Creating embeddings",
                    model=model,
                    text_count=len(texts),
                    user_id=user_id
                )
                
                # Make OpenAI API call
                response = await self.client.embeddings.create(
                    model=model,
                    input=texts
                )
                
                # Extract response data
                embeddings = [item.embedding for item in response.data]
                usage = response.usage
                input_tokens = usage.total_tokens
                cost = self._calculate_cost(model, input_tokens)
                duration = time.time() - start_time
                
                # Get actual response model
                response_model = getattr(response, 'model', model)
                
                # Update span attributes
                span.set_attributes({
                    GenAIAttributes.RESPONSE_MODEL: response_model,
                    GenAIAttributes.USAGE_INPUT_TOKENS: input_tokens,
                    GenAIAttributes.TOKEN_COST: cost,
                    "embedding.dimension": len(embeddings[0]) if embeddings else 0,
                    "server.address": "api.openai.com",
                    "server.port": 443
                })
                
                # Common metric attributes matching OpenLIT
                common_attrs = {
                    GenAIAttributes.SYSTEM: "openai",
                    GenAIAttributes.REQUEST_MODEL: model,
                    GenAIAttributes.RESPONSE_MODEL: response_model,
                    GenAIAttributes.OPERATION_NAME: "embeddings",
                    "server_address": "api.openai.com",
                    "server_port": 443,
                    "telemetry_sdk_name": "opentelemetry"
                }
                
                # Record metrics using GenAI conventions
                gen_ai_client_operation_duration.record(duration, attributes=common_attrs)
                
                # Token usage (Histogram as per GenAI spec)
                gen_ai_client_token_usage.record(
                    input_tokens,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        "gen_ai.token.type": "input",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                # Total token counters matching OpenLIT
                gen_ai_usage_input_tokens.add(input_tokens, attributes=common_attrs)
                
                gen_ai_client_operation_count.add(
                    1,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        GenAIAttributes.OPERATION_NAME: "embeddings",
                        "status": "success",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                # Total requests counter
                gen_ai_total_requests.add(1, attributes=common_attrs)
                
                # Cost tracking (both counter and histogram)
                gen_ai_client_operation_cost.add(
                    cost,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        GenAIAttributes.OPERATION_NAME: "embeddings",
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                gen_ai_usage_cost.record(cost, attributes=common_attrs)
                
                span.set_status(Status(StatusCode.OK))
                
                logger.info(
                    "Embeddings created successfully",
                    model=model,
                    text_count=len(texts),
                    tokens=input_tokens,
                    dimension=len(embeddings[0]) if embeddings else 0,
                    cost=cost,
                    duration=duration
                )
                
                return {
                    "embeddings": embeddings,
                    "model": model,
                    "usage": {"total_tokens": input_tokens},
                    "cost_usd": cost,
                    "duration_seconds": duration
                }
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metrics
                gen_ai_client_operation_count.add(
                    1,
                    attributes={
                        GenAIAttributes.SYSTEM: "openai",
                        GenAIAttributes.REQUEST_MODEL: model,
                        GenAIAttributes.OPERATION_NAME: "embeddings",
                        "status": "error",
                        "error_type": type(e).__name__,
                        "user_id": user_id or "unknown",
                        "telemetry_sdk_name": "opentelemetry"
                    }
                )
                
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                logger.error(
                    "Embedding creation failed",
                    model=model,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration=duration
                )
                
                raise

# Global service instance
openai_service = OpenAIService()