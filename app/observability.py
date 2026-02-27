"""
OpenTelemetry configuration and initialization for the AI observability demo.

This module sets up comprehensive OpenTelemetry instrumentation including:
- Automatic instrumentation for web frameworks, HTTP clients, and databases
- Manual instrumentation for AI/ML specific operations
- OTLP exporters for Grafana Cloud integration
- Prometheus metrics exporters
- Resource detection and service identification
"""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.metrics._internal.aggregation import ExplicitBucketHistogramAggregation
from opentelemetry.sdk.metrics._internal.instrument import Histogram
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

# Exporters
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GRPCMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader

# Instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor

# Semantic conventions
from opentelemetry.semconv.resource import ResourceAttributes

import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)

# Global meter for eval metrics
eval_meter = metrics.get_meter(__name__)

# GenAI Eval Metrics (OTel Spec)
genai_eval_score = eval_meter.create_histogram(
    name="gen_ai.eval.score",
    description="Evaluation score for GenAI output",
    unit="score"
)
genai_eval_passed = eval_meter.create_counter(
    name="gen_ai.eval.passed",
    description="Number of evals passed"
)
genai_eval_failed = eval_meter.create_counter(
    name="gen_ai.eval.failed",
    description="Number of evals failed"
)
genai_eval_duration = eval_meter.create_histogram(
    name="gen_ai.eval.duration",
    description="Duration of eval runs",
    unit="s"
)

# Simple eval function (heuristic-based evaluation for demo)
def run_eval(model_output, reference_input, user_id=None, eval_name="heuristic_eval", system="unknown", operation="unknown", model="unknown"):
    import time
    start = time.time()
    
    # For demo purposes, use a simple heuristic evaluation:
    # - Check if response is not empty
    # - Check if response length is reasonable (> 10 characters)
    # - Check if response doesn't just repeat the input
    # - Check for basic coherence (contains spaces, not just symbols)
    
    model_output = model_output.strip() if model_output else ""
    reference_input = reference_input.strip() if reference_input else ""
    
    # Basic quality checks
    has_content = len(model_output) > 0
    reasonable_length = len(model_output) > 10
    not_just_input = model_output.lower() != reference_input.lower()
    has_spaces = ' ' in model_output
    not_gibberish = len(model_output.split()) > 2  # At least 3 words
    
    # Score based on criteria met
    criteria_met = sum([has_content, reasonable_length, not_just_input, has_spaces, not_gibberish])
    score = criteria_met / 5.0  # Normalize to 0-1
    
    # Pass if score >= 0.6 (at least 3 out of 5 criteria)
    passed = score >= 0.6
    
    duration = time.time() - start
    
    # Use comprehensive attributes matching OpenLIT labeling patterns
    # Include all relevant GenAI semantic convention attributes
    attrs = {
        "gen_ai.system": system,  # e.g., "openai", "transformers"
        "gen_ai.operation.name": operation,  # e.g., "chat", "text_generation"
        "gen_ai.request.model": model,  # The model being evaluated
        "eval.name": eval_name,  # Type of evaluation (heuristic_eval, llm_judge, etc.)
        "eval.criteria": "content,length,uniqueness,coherence",  # What we're evaluating
        "user_id": user_id or "unknown",
        "telemetry_sdk_name": "opentelemetry"  # Distinguish from OpenLIT metrics
    }
    
    genai_eval_score.record(score, attributes=attrs)
    genai_eval_duration.record(duration, attributes=attrs)
    if passed:
        genai_eval_passed.add(1, attributes=attrs)
    else:
        genai_eval_failed.add(1, attributes=attrs)
    
    return {
        "score": score, 
        "passed": passed, 
        "duration": duration,
        "criteria": {
            "has_content": has_content,
            "reasonable_length": reasonable_length,
            "not_just_input": not_just_input,
            "has_spaces": has_spaces,
            "not_gibberish": not_gibberish
        }
    }

def _parse_otlp_headers(otlp_headers: Optional[str]) -> dict:
    """Parse OTLP headers from env string into a dict.

    Handles common mistakes:
    - Surrounding quotes around the full header or values
    - Authorization=Basic <instance_id:api_key> (auto base64-encodes credentials)
    - Whitespace around keys/values
    """
    headers: dict = {}
    if not otlp_headers:
        return headers

    try:
        # Strip any surrounding quotes on the whole string
        raw = otlp_headers.strip().strip("'\"")
        # Split on commas for multiple headers
        parts = [p for p in (s.strip() for s in raw.split(",")) if p]
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            k = key.strip()
            v = value.strip().strip("'\"")  # remove accidental quotes around values

            # If Authorization header uses Basic with non-base64 creds like "11111:glc_xxx",
            # auto-encode to the correct Basic <base64(instance:token)> form.
            if k.lower() == "authorization":
                # Normalize spacing, e.g., "Basic    foo" -> "Basic foo"
                if v.lower().startswith("basic "):
                    creds = v[6:].strip()
                    # If value still looks like raw creds (contains a colon), base64 encode it
                    if ":" in creds:
                        import base64
                        encoded = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
                        v = f"Basic {encoded}"
                # If no scheme provided but looks like raw creds, assume Basic
                elif ":" in v and not v.lower().startswith(("bearer ", "basic ")):
                    import base64
                    encoded = base64.b64encode(v.encode("utf-8")).decode("utf-8")
                    v = f"Basic {encoded}"

            headers[k] = v
    except Exception as e:
        # Be defensive: never let header parsing kill startup
        logger.warning("Failed to parse OTLP headers; proceeding without custom headers", error=str(e))
        return {}

    return headers

def create_resource() -> Resource:
    """Create OpenTelemetry resource with service identification."""
    resource_attributes = {
        SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "ai-observability-demo"),
        SERVICE_VERSION: os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("DEPLOYMENT_ENVIRONMENT", "demo"),
        ResourceAttributes.SERVICE_INSTANCE_ID: os.getenv("HOSTNAME", "localhost"),
        ResourceAttributes.TELEMETRY_SDK_NAME: "opentelemetry",
        ResourceAttributes.TELEMETRY_SDK_LANGUAGE: "python",
        
        # AI/ML specific attributes
        "ai.system": "openai,chromadb,transformers",
        "ai.model.vendor": "openai,huggingface",
        "gpu.enabled": str(os.getenv("USE_GPU", "true")).lower(),
        "vector.db.system": "chromadb",
    }
    
    # Add custom resource attributes from environment
    custom_attributes = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
    if custom_attributes:
        for attr in custom_attributes.split(","):
            if "=" in attr:
                key, value = attr.split("=", 1)
                resource_attributes[key.strip()] = value.strip()
    
    return Resource.create(resource_attributes)

def _choose_otlp_mode(endpoint: str, explicit_protocol: Optional[str] = None) -> str:
    """Choose OTLP export protocol: 'grpc' or 'http'.

    Priority:
    1) explicit_protocol if provided (values: 'grpc', 'http', 'http/protobuf')
    2) Heuristics from endpoint: if contains '/otlp' or '/v1', prefer HTTP; else gRPC.
    """
    if explicit_protocol:
        proto = explicit_protocol.strip().lower()
        if proto in ("grpc",):
            return "grpc"
        if proto in ("http", "http/protobuf", "http_json", "http/json"):
            return "http"
    ep = (endpoint or "").lower()
    if "/otlp" in ep or "/v1/" in ep:
        return "http"
    return "grpc"

def _normalize_endpoints_for_mode(endpoint: str, mode: str) -> tuple[str, str]:
    """Return (traces_endpoint, metrics_endpoint) for chosen mode.

    - For HTTP: ensure base like 'https://host/otlp' and append '/v1/traces' and '/v1/metrics'
    - For gRPC: strip any path like '/otlp' or '/v1/...' and return host (optionally with scheme), no path
    """
    if mode == "http":
        base = endpoint.rstrip("/")
        # If user provided host only, add '/otlp'
        if not base.endswith("/otlp") and not base.endswith("/v1") and "/v1/" not in base:
            base = base + "/otlp"
        return base + "/v1/traces", base + "/v1/metrics"
    # grpc
    # Remove any path segments for gRPC
    # Accept forms like 'https://host:443/otlp' or 'host:4317'
    import re
    m = re.match(r"^(?P<scheme>https?://)?(?P<hostport>[^/]+)", endpoint)
    hostport = endpoint
    if m:
        hostport = (m.group("scheme") or "") + m.group("hostport")
    return hostport, hostport

def setup_tracing() -> None:
    """Configure OpenTelemetry tracing."""
    logger.info("Setting up OpenTelemetry tracing")
    
    # Create resource
    resource = create_resource()
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # OTLP Exporter for Grafana Cloud
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    otlp_protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL")
    
    if otlp_endpoint:
        mode = _choose_otlp_mode(otlp_endpoint, otlp_protocol)
        traces_ep, _ = _normalize_endpoints_for_mode(otlp_endpoint, mode)
        logger.info("Configuring OTLP trace exporter", endpoint=traces_ep, protocol=mode)

        # Parse headers (with auto-fixes for common mistakes)
        headers = _parse_otlp_headers(otlp_headers)

        if mode == "http":
            exporter = HTTPSpanExporter(
                endpoint=traces_ep,
                headers=headers,
            )
        else:
            exporter = GRPCSpanExporter(
                endpoint=traces_ep,
                headers=headers,
                insecure=traces_ep.startswith("http://"),
            )

        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        logger.warning("OTLP endpoint not configured, traces will only be available locally")
    
    # Console exporter for development
    if os.getenv("OTEL_TRACES_CONSOLE", "false").lower() == "true":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

def setup_metrics() -> None:
    """Configure OpenTelemetry metrics with GenAI semantic conventions compliance."""
    logger.info("Setting up OpenTelemetry metrics")
    
    # Create resource
    resource = create_resource()
    
    # Define Views for GenAI semantic conventions compliance
    # Token usage histogram with explicit buckets as per spec
    # https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
    token_usage_buckets = [
        1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 
        1048576, 4194304, 16777216, 67108864
    ]
    
    # Operation duration histogram with explicit buckets as per spec
    operation_duration_buckets = [
        0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 
        5.12, 10.24, 20.48, 40.96, 81.92
    ]
    
    # Time to first token histogram with explicit buckets as per spec
    ttft_buckets = [
        0.001, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 
        0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0
    ]
    
    views = [
        # Token usage metric view
        View(
            instrument_type=Histogram,
            instrument_name="gen_ai.client.token.usage",
            aggregation=ExplicitBucketHistogramAggregation(boundaries=token_usage_buckets)
        ),
        # Operation duration metric view
        View(
            instrument_type=Histogram,
            instrument_name="gen_ai.client.operation.duration",
            aggregation=ExplicitBucketHistogramAggregation(boundaries=operation_duration_buckets)
        ),
        # Time to first token metric view
        View(
            instrument_type=Histogram,
            instrument_name="gen_ai.client.time_to_first_token",
            aggregation=ExplicitBucketHistogramAggregation(boundaries=ttft_buckets)
        ),
    ]
    
    # Create metric readers (we always set our MeterProvider so that vector_*, gen_ai_*, and
    # all custom metrics are exported via our OTLP and Prometheus readers regardless of OpenLIT)
    readers = []
    
    # Prometheus exporter
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "8000"))
    if os.getenv("METRICS_ENABLED", "true").lower() == "true":
        logger.info(f"Configuring Prometheus metrics exporter on port {prometheus_port}")
        # Disable target_info metric as it's not part of GenAI semantic conventions
        readers.append(PrometheusMetricReader(disable_target_info=True))
    
    # OTLP Exporter for Grafana Cloud
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    otlp_protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL")
    
    if otlp_endpoint:
        mode = _choose_otlp_mode(otlp_endpoint, otlp_protocol)
        _, metrics_ep = _normalize_endpoints_for_mode(otlp_endpoint, mode)
        logger.info("Configuring OTLP metrics exporter", endpoint=metrics_ep, protocol=mode)

        # Parse headers (with auto-fixes for common mistakes)
        headers = _parse_otlp_headers(otlp_headers)

        if mode == "http":
            metric_exporter = HTTPMetricExporter(
                endpoint=metrics_ep,
                headers=headers,
            )
        else:
            metric_exporter = GRPCMetricExporter(
                endpoint=metrics_ep,
                headers=headers,
                insecure=metrics_ep.startswith("http://"),
            )

        readers.append(
            PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=10000,  # 10 seconds
            )
        )
    
    # Create meter provider with Views for GenAI semantic conventions
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=readers,
        views=views
    )
    
    metrics.set_meter_provider(meter_provider)
    logger.info("OpenTelemetry metrics configured with GenAI semantic conventions compliance")

def setup_automatic_instrumentation() -> None:
    """Setup automatic instrumentation for various libraries."""
    logger.info("Setting up automatic instrumentation")
    
    try:
        # FastAPI instrumentation
        FastAPIInstrumentor().instrument()
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")
    
    try:
        # HTTP client instrumentations
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTP client instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTP clients: {e}")
    
    try:
        # Database instrumentation
        SQLite3Instrumentor().instrument()
        logger.info("SQLite3 instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLite3: {e}")
    
    # Note: System monitoring with psutil is handled manually in local_model_service.py
    # There is no official OpenTelemetry instrumentation for psutil

def setup_logging() -> None:
    """Configure structured logging with OpenTelemetry correlation."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer() if os.getenv("DEBUG_MODE", "false").lower() == "true" else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set Python logging level
    logging.basicConfig(level=getattr(logging, log_level))
    
    # Reduce noise from some libraries
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured with level: {log_level}")

def initialize_observability() -> None:
    """Initialize all OpenTelemetry components."""
    logger.info("Initializing OpenTelemetry observability")
    
    try:
        # Setup logging first
        setup_logging()
        
        # Setup our MeterProvider first (OTLP + Prometheus). We use it for both manual OTel
        # metrics and, when possible, pass our meter to OpenLIT so OpenLIT metrics go through it too.
        setup_metrics()
        
        # Init OpenLIT so we get both: OpenLIT auto-instrumentation (gen_ai*, evals) AND our
        # manual OTel (vector_*, custom gen_ai*). Pass our meter so both are on one provider.
        if os.getenv("ENABLE_OPENLIT", "false").lower() == "true":
            initialize_openlit_instrumentation()
        
        # Setup tracing
        setup_tracing()
        
        # Setup automatic instrumentation
        setup_automatic_instrumentation()
        
        logger.info("OpenTelemetry observability initialized successfully")
        
        # Log configuration summary
        logger.info(
            "Observability configuration summary",
            service_name=os.getenv("OTEL_SERVICE_NAME", "ai-observability-demo"),
            service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "not_configured"),
            prometheus_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            prometheus_port=os.getenv("PROMETHEUS_PORT", "8000"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize observability: {e}")
        raise

def initialize_openlit_instrumentation():
    """
    Initialize OpenLIT auto-instrumentation alongside manual OpenTelemetry instrumentation.
    This enables comparison of both approaches in Grafana Cloud.
    
    OpenLIT will:
    - Auto-instrument OpenAI API calls
    - Use telemetry.sdk.name="openlit" 
    - Create gen_ai.* spans and metrics
    - Calculate costs automatically
    
    Manual OTel will:
    - Use telemetry.sdk.name="opentelemetry"
    - Create custom spans and metrics
    - Provide ChromaDB, local model, and custom business logic instrumentation
    """
    if os.getenv("ENABLE_OPENLIT", "false").lower() != "true":
        logger.info("OpenLIT instrumentation disabled (set ENABLE_OPENLIT=true to enable)")
        return
        
    try:
        import openlit
        
        logger.info("Initializing OpenLIT auto-instrumentation...")
        
        # Use our app meter so OpenLIT records into our MeterProvider; both OpenLIT metrics
        # (gen_ai*, evals_request_total, etc.) and our manual metrics (vector_*, etc.) export together.
        app_meter = metrics.get_meter("openlit.integration", "1.0")
        init_kw = dict(
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            otlp_headers=_parse_otlp_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS")),
            application_name=os.getenv("OTEL_SERVICE_NAME", "ai-observability-demo"),
            environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "demo"),
            pricing_json=os.getenv(
                "OPENLIT_PRICING_JSON",
                "https://raw.githubusercontent.com/openlit/openlit/main/assets/pricing.json"
            ),
            collect_gpu_stats=os.getenv("OPENLIT_COLLECT_GPU_STATS", "false").lower() == "true",
            disable_batch=False,
        )
        try:
            openlit.init(**init_kw, meter=app_meter)
            logger.info(
                "OpenLIT auto-instrumentation initialized (metrics via app MeterProvider)",
                telemetry_sdk_name="openlit",
                gpu_stats_enabled=init_kw["collect_gpu_stats"],
            )
        except TypeError:
            # Older OpenLIT may not accept meter=; init without it (OpenLIT may set its own provider).
            openlit.init(**init_kw)
            logger.info(
                "OpenLIT auto-instrumentation initialized (OpenLIT MeterProvider)",
                telemetry_sdk_name="openlit",
                gpu_stats_enabled=init_kw["collect_gpu_stats"],
            )
            logger.warning(
                "OpenLIT init does not accept meter=; manual metrics (e.g. vector_*) may not export to OTLP on some stacks"
            )
        
    except ImportError:
        logger.warning(
            "OpenLIT not installed. Install with: pip install openlit",
            enable_openlit=os.getenv("ENABLE_OPENLIT")
        )
    except Exception as e:
        logger.error(f"Failed to initialize OpenLIT: {e}")

# Initialize observability when module is imported
if os.getenv("OTEL_PYTHON_DISABLED", "false").lower() != "true":
    initialize_observability()
else:
    logger.info("OpenTelemetry disabled by OTEL_PYTHON_DISABLED environment variable")