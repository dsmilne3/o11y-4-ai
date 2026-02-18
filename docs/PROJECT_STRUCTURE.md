# Project Structure

```
o11y-4-ai/
├── README.md                           # Main project documentation
├── GETTING_STARTED.md                  # Quick start guide
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment configuration template
├── .dockerignore                      # Docker ignore patterns
├── Dockerfile                         # Container configuration
├── docker-compose.yml                 # Multi-service deployment
│
├── app/                               # Main application package
│   ├── __init__.py                    # Package initialization
│   ├── main.py                        # FastAPI application with all endpoints
│   ├── observability.py               # OpenTelemetry configuration
│   ├── openai_service.py              # OpenAI API integration with OTel
│   ├── vector_db_service.py           # ChromaDB integration with OTel
│   └── local_model_service.py         # Local GPU model service with OTel
│
├── config/                            # Configuration files
│   ├── config.alloy                   # Grafana Alloy configuration
│   └── alloy.env.example              # Alloy environment template
│
├── scripts/                           # Utility scripts
│   ├── setup.sh                       # Initial setup script
│   ├── start-alloy.sh                 # Grafana Alloy startup script
│   ├── demo_scenarios.py              # Demo workflow scenarios
│   └── performance_test.py            # Performance testing suite
│
├── tests/                             # Test suite
│   ├── __init__.py                    # Test package initialization
│   └── test_basic.py                  # Basic functionality tests
│
└── data/                              # Runtime data (created automatically)
    └── chroma_db/                     # Vector database storage
```

# Component Overview

## Core Services

### 1. **OpenAI Service** (`app/openai_service.py`)

- GPT chat completions with cost tracking
- Embedding generation for vector storage
- Comprehensive OpenTelemetry instrumentation
- Token usage metrics and cost calculation
- Error handling and retry logic

### 2. **Vector Database Service** (`app/vector_db_service.py`)

- ChromaDB integration for embeddings storage
- Similarity search with performance metrics
- Document storage with metadata support
- Vector operation tracing and metrics

### 3. **Local Model Service** (`app/local_model_service.py`)

- Hugging Face Transformers integration
- GPU acceleration support with monitoring
- Hardware metrics collection (GPU, CPU, memory)
- Local text generation with performance tracking

### 4. **Main Application** (`app/main.py`)

- FastAPI web framework with automatic OpenAPI docs
- RESTful API endpoints for all AI operations
- Comprehensive middleware for observability
- Health checks and system statistics

## Observability Stack

### 1. **OpenTelemetry Instrumentation** (`app/observability.py`)

- Automatic instrumentation for web frameworks
- Custom spans for AI/ML operations
- Metrics collection and export
- Resource detection and tagging

### 2. **Grafana Alloy Configuration** (`config/config.alloy`)

- OTLP receivers for traces, metrics, and logs
- Prometheus metrics scraping
- Data forwarding to Grafana Cloud
- System monitoring and service discovery

## Key Features

### API Endpoints

- `POST /chat` - OpenAI chat completions
- `POST /embed` - Generate and store embeddings
- `POST /search` - Vector similarity search
- `POST /local-inference` - Local model text generation
- `POST /full-pipeline` - End-to-end AI workflow
- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics
- `GET /stats` - System statistics

### Observability Features

- **Distributed Tracing**: End-to-end request tracing
- **Metrics Collection**: Performance, costs, and business metrics
- **Structured Logging**: Correlated logs with trace context
- **Hardware Monitoring**: GPU utilization and system resources
- **Cost Tracking**: OpenAI API usage and cost analysis

### Demo Scenarios

- Chat completion workflows
- Embedding generation and vector search
- Local model inference
- Full AI pipeline demonstrations
- Error condition testing
- Performance load simulation

## Technology Stack

### Core Technologies

- **Python 3.11+** - Runtime environment
- **FastAPI** - Web framework with automatic docs
- **OpenTelemetry** - Observability instrumentation
- **ChromaDB** - Vector database for embeddings
- **Transformers** - Local model inference
- **OpenAI API** - Cloud-based AI services

### Observability

- **Grafana Alloy** - Telemetry collection and forwarding
- **Grafana Cloud** - Visualization and alerting
- **Prometheus** - Metrics collection
- **OTLP** - Telemetry data transport

### Deployment

- **Docker** - Containerization
- **Docker Compose** - Multi-service orchestration
- **Virtual Environments** - Local development

## Quick Commands

```bash
# Setup
./scripts/setup.sh

# Local Development
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Docker Deployment
docker-compose up --build

# Run Demos
python scripts/demo_scenarios.py

# Performance Testing
python scripts/performance_test.py --concurrent-users 10

# Start Grafana Alloy
./scripts/start-alloy.sh
```

## Environment Configuration

### Required

```env
OPENAI_API_KEY=sk-your-api-key-here
```

### Optional (GPU)

```env
USE_GPU=true
GPU_DEVICE_ID=0
LOCAL_MODEL_NAME=microsoft/DialoGPT-medium
```

### Optional (Grafana Cloud)

```env
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic your_base64_credentials
```

This project demonstrates best practices for AI observability, providing a complete example of monitoring AI workloads with comprehensive telemetry data.
