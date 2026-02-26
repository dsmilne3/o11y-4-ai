# AI Observability Demo with OpenTelemetry

This demo application showcases comprehensive observability for AI workloads using OpenTelemetry, Grafana Alloy, and Grafana Cloud's AI Observability integration.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Demo App      │    │  OpenAI API     │    │ Local GPU Model │
│   (FastAPI)     │───▶│   Service       │    │   (Transformers)│
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └─────────────▶│   ChromaDB      │◀─────────────┘
                        │ Vector Database │
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │ OpenTelemetry   │
                        │ Instrumentation │
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │ Grafana Alloy   │
                        │   Collector     │
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │ Grafana Cloud   │
                        │ AI Observability│
                        └─────────────────┘
```

## Components

### 1. **Demo Application (FastAPI)**

- Main orchestration service
- RESTful API endpoints for different AI workflows
- Comprehensive OpenTelemetry instrumentation

### 2. **OpenAI API Service**

- GPT model integration for text generation
- Embedding generation for vector storage
- LLM-specific OpenTelemetry semantic conventions

### 3. **Vector Database (ChromaDB)**

- Document embeddings storage and retrieval
- Similarity search capabilities
- Database operation tracing

### 4. **Local GPU Model Service**

- Hugging Face Transformers integration
- GPU acceleration support
- Hardware metrics collection

### 5. **Observability Stack**

- **OpenTelemetry**: Traces, metrics, and logs
- **Grafana Alloy**: Collection and forwarding
- **Grafana Cloud**: Visualization and alerting

## Features Demonstrated

- **LLM Observability**: Token usage, latency, model performance
- **Vector Operations**: Embedding generation, similarity search
- **GPU Monitoring**: Utilization, memory, temperature
- **Error Tracking**: API failures, model errors, timeouts
- **Cost Tracking**: OpenAI API usage and costs
- **Performance Metrics**: Response times, throughput

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd o11y-4-ai
chmod +x scripts/setup.sh
./scripts/setup.sh

# Configure environment (edit .env with your OPENAI_API_KEY)
# Then start the application
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

**For detailed setup instructions, troubleshooting, and advanced configuration, see the [Getting Started Guide](GETTING_STARTED.md).**

### Docker Setup

```bash
docker-compose up --build
```

## API Endpoints

- `POST /chat` - Chat completion with OpenAI
- `POST /embed` - Generate and store embeddings
- `POST /search` - Vector similarity search
- `POST /local-inference` - Local model inference
- `GET /health` - Health check with metrics
- `GET /metrics` - Prometheus metrics endpoint

## Observability Features

### Traces

- End-to-end request tracing
- LLM operation spans with semantic attributes
- Database operation tracing
- Custom business logic spans

### Metrics

- Request/response metrics
- Token usage and costs
- GPU utilization
- Database performance
- Error rates and latencies

### Logs

- Structured logging with correlation IDs
- Error details and stack traces
- Performance insights
- Business metrics

## Documentation

- **[Getting Started Guide](GETTING_STARTED.md)** - Detailed setup and configuration instructions
- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Operations Guide](docs/OPERATIONS.md)** - Running and troubleshooting the application
- **[GenAI Semantic Conventions](docs/GENAI_SEMANTIC_CONVENTIONS_COMPLIANCE.md)** - Full compliance documentation

## Configuration

See `config/` directory for:

- OpenTelemetry configuration
- Grafana Alloy setup
- Environment variables
- Model configurations

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black .
flake8 .
mypy .
```

## Deployment

See `deployment/` directory for:

- Kubernetes manifests
- Docker configurations
- Production settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
