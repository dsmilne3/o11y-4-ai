# AI Observability Demo - Operations Guide

## Overview

This demo showcases comprehensive OpenTelemetry instrumentation for AI/ML applications with:

- FastAPI web service (port 8080)
- OpenAI API integration (chat, embeddings)
- ChromaDB vector database (persistent storage)
- Local GPU model inference (HuggingFace Transformers with Apple Silicon MPS support)
- Prometheus metrics (port 8080/metrics)
- OTLP export to Grafana Cloud (HTTP protocol)

## Quick Start

### 1. Start the Server

```bash
cd /Users/davidmilne/Projects/o11y-4-ai
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**Background mode** (logs to `/tmp/ai-demo.log`):

```bash
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 >/tmp/ai-demo.log 2>&1 &
```

### 2. Verify Health

```bash
curl http://localhost:8080/health
```

Expected response:

```json
{
  "status": "healthy",
  "services": {
    "openai_service": { "status": "available" },
    "vector_database": { "status": "available", "document_count": 3 },
    "local_model": {
      "status": "available",
      "model_name": "microsoft/DialoGPT-medium",
      "device": "mps"
    }
  }
}
```

### 3. View Metrics

```bash
curl http://localhost:8080/metrics
```

Key metrics to monitor:

- `model_inference_duration_seconds` - Local model inference time
- `model_tokens_generated_total` - Total tokens generated
- `gpu_memory_used_bytes` - GPU memory (MPS on Apple Silicon)
- `openai_api_duration_seconds` - OpenAI API response time
- `openai_cost_usd_total` - Cumulative API costs

## Running Demo Scenarios

### Full Demo Suite (Recommended)

Runs all scenarios: chat, embeddings, search, local inference, pipeline, error testing.

```bash
python scripts/demo_scenarios.py --scenario all
```

**Duration:** ~2 minutes  
**Generates:** ~30 traces with nested spans, comprehensive metrics

### Individual Scenarios

```bash
# Chat completions only
python scripts/demo_scenarios.py --scenario chat

# Embeddings and vector search
python scripts/demo_scenarios.py --scenario embed

# Local model inference
python scripts/demo_scenarios.py --scenario local

# Full pipeline (all services)
python scripts/demo_scenarios.py --scenario pipeline

# Error condition testing
python scripts/demo_scenarios.py --scenario errors
```

### Load Generation

For stress testing or metrics volume:

```bash
# Structured load with varied scenarios
python scripts/demo_scenarios.py --scenario load --load-duration 5

# Simple load generator (bash script)
bash scripts/load_generator.sh
```

**Difference:**

- `demo_scenarios.py --scenario load`: Varied, realistic traffic across all endpoints
- `load_generator.sh`: Simple repetitive requests (health, local-inference, stats)

## API Endpoints

| Endpoint           | Method | Purpose                          |
| ------------------ | ------ | -------------------------------- |
| `/health`          | GET    | Health check with service status |
| `/metrics`         | GET    | Prometheus metrics endpoint      |
| `/stats`           | GET    | Vector DB statistics             |
| `/chat`            | POST   | OpenAI chat completion           |
| `/embed`           | POST   | Generate embeddings (OpenAI)     |
| `/search`          | POST   | Vector similarity search         |
| `/local-inference` | POST   | Local GPU model inference        |
| `/full-pipeline`   | POST   | Complete AI pipeline demo        |

### Example API Calls

**Chat Completion:**

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain machine learning",
    "temperature": 0.7,
    "max_tokens": 200,
    "user_id": "demo_user"
  }'
```

**Local Inference:**

```bash
curl -X POST http://localhost:8080/local-inference \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "The future of AI is",
    "max_length": 100,
    "temperature": 0.8
  }'
```

**Vector Search:**

```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "n_results": 3
  }'
```

**Full Pipeline:**

```bash
curl -X POST "http://localhost:8080/full-pipeline?query=Explain%20AI&store_results=true&user_id=test"
```

## Monitoring & Observability

### Telemetry Destinations

1. **Grafana Cloud** (traces & metrics via OTLP HTTP)

   - Endpoint: `https://otlp-gateway-prod-us-west-0.grafana.net/otlp`
   - Protocol: HTTP (auto-selected based on endpoint)
   - Headers: Basic auth (auto-encoded from `.env`)

2. **Prometheus** (metrics scraping)
   - Endpoint: `http://localhost:8080/metrics`
   - Format: OpenMetrics/Prometheus text

### Key Observability Features

**Traces:**

- Automatic: FastAPI requests, HTTP clients, database operations
- Manual: AI operations (chat, embeddings, inference) with custom attributes
- Nested spans: Full pipeline shows complete service dependency tree
- Error tracking: Exceptions captured with stack traces

**Metrics:**

- Model performance: inference duration, tokens/sec
- Hardware: GPU memory (MPS), CPU, system memory
- API costs: Real-time USD tracking for OpenAI
- Vector DB: Search quality (similarity scores, distances)

**Attributes:**

- User context: `user_id`, `session_id`
- Model details: `model.name`, `model.device`, `model.parameters`
- Usage: `llm.usage.prompt_tokens`, `llm.usage.completion_tokens`
- Performance: `tokens_per_second`, `batch_efficiency`

### Viewing Telemetry

**Grafana Cloud:**

1. Navigate to your Grafana instance
2. Explore → Traces: Search by service name `ai-observability-demo`
3. Explore → Metrics: Query Prometheus-style (`model_inference_duration_seconds`)

**Local Prometheus Metrics:**

```bash
# View all metrics
curl http://localhost:8080/metrics

# Filter specific metrics
curl http://localhost:8080/metrics | grep model_inference

# GPU/hardware metrics
curl http://localhost:8080/metrics | grep -E "gpu_|cpu_|memory_"
```

## Server Management

### Check Server Status

```bash
# Check if server is running
lsof -ti:8080

# View server process details
ps aux | grep uvicorn | grep -v grep
```

### Stop Server

**Graceful shutdown:**

```bash
kill -15 $(lsof -ti:8080)
```

**Force stop:**

```bash
kill -9 $(lsof -ti:8080)
```

**Safe stop script:**

```bash
p=$(lsof -ti:8080)
if [ -n "$p" ]; then
  echo "Stopping server PID(s): $p"
  kill -15 $p
  sleep 2
  p2=$(lsof -ti:8080)
  if [ -n "$p2" ]; then
    echo "Force killing lingering PID(s): $p2"
    kill -9 $p2
  fi
else
  echo "No server found on :8080"
fi
```

### View Logs

**Foreground mode:** Logs appear in terminal

**Background mode:**

```bash
tail -f /tmp/ai-demo.log
```

**Structured logs** (JSON format when `DEBUG_MODE=false`):

```bash
tail -f /tmp/ai-demo.log | jq '.'
```

## Configuration

### Environment Variables (`.env`)

Key settings:

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...

# OpenTelemetry
OTEL_SERVICE_NAME=ai-observability-demo
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-west-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=authorization=Basic <instance_id>:<api_token>

# Model & GPU
LOCAL_MODEL_NAME=microsoft/DialoGPT-medium
USE_GPU=true
GPU_DEVICE_ID=0

# Vector DB
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# Logging
LOG_LEVEL=INFO
PROMETHEUS_PORT=8000
```

**Note on OTLP Headers:**

- Raw credentials (`instance_id:api_key`) are auto-encoded to Base64
- Pre-encoded Basic tokens work too: `authorization=Basic <base64>`

### Protocol Selection (Automatic)

The observability layer automatically chooses the correct OTLP protocol:

- **HTTP**: If endpoint contains `/otlp` or `/v1/` (e.g., Grafana Cloud)
- **gRPC**: For bare `host:port` endpoints (e.g., `localhost:4317`)

Override with: `OTEL_EXPORTER_OTLP_PROTOCOL=http` or `=grpc`

## Hardware Support

### Apple Silicon (MPS)

**Auto-detected** when `USE_GPU=true` and CUDA unavailable:

- Device: `mps` (Metal Performance Shaders)
- Model dtype: `torch.float16` for memory efficiency
- Metrics: GPU memory usage (allocated + driver)
- Limitation: No utilization percentage (PyTorch API limitation)

### NVIDIA CUDA

**Auto-detected** when available:

- Device: `cuda:0` (or configured GPU_DEVICE_ID)
- Metrics: Full GPU monitoring (utilization, temp, memory) via GPUtil
- Model loading: Uses `device_map="auto"` for optimal placement

### CPU Fallback

When GPU unavailable or `USE_GPU=false`:

- Device: `cpu`
- Model dtype: `torch.float32`
- Performance: ~10x slower than GPU

## Troubleshooting

### Server Won't Start

**Port already in use:**

```bash
# Find and kill process using port 8080
lsof -ti:8080 | xargs kill -9
```

**Missing dependencies:**

```bash
pip install -r requirements.txt
```

**Environment issues:**

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Telemetry Not Appearing in Grafana

**Check OTLP configuration:**

```bash
# Verify endpoint is reachable
curl -I https://otlp-gateway-prod-us-west-0.grafana.net/otlp/v1/traces

# Check headers are properly formatted
grep OTEL_EXPORTER_OTLP_HEADERS .env
```

**Verify local metrics work:**

```bash
curl http://localhost:8080/metrics | head -20
```

**Check logs for export errors:**

```bash
tail -f /tmp/ai-demo.log | grep -i otlp
```

### GPU Not Being Used

**Check device detection:**

```bash
curl http://localhost:8080/health | jq '.services.local_model'
```

**Verify MPS availability (Mac):**

```python
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

**Check GPU memory metrics:**

```bash
curl http://localhost:8080/metrics | grep gpu_memory
```

### High API Costs

**Monitor cost metrics:**

```bash
curl http://localhost:8080/metrics | grep openai_cost_usd_total
```

**Reduce costs:**

- Lower `max_tokens` in chat requests
- Use `gpt-3.5-turbo` instead of `gpt-4`
- Prefer local inference for simple tasks
- Cache embeddings in vector DB

## Files Changed/Fixed

### Critical Fixes Applied

1. **`.env`** - Fixed OTLP headers (authorization format), added missing vars
2. **`app/observability.py`** - Added HTTP/gRPC protocol selection, header auto-encoding
3. **`app/local_model_service.py`** - Fixed type errors, added MPS support, `dtype` parameter
4. **`app/main.py`** - Added favicon handler, fixed span attribute types
5. **`Dockerfile`** - Fixed case consistency (`AS base`)
6. **Removed `config/alloy.yaml`** - Obsolete, using `config.alloy` instead

### Type Safety

All Pylance type errors resolved with targeted `# type: ignore` comments for HuggingFace library quirks.

## Summary of Capabilities

**What This Demo Shows:**

1. **Multi-service AI pipeline** with OpenAI + local models + vector DB
2. **Production-grade instrumentation** (not auto-instrumentation)
3. **Hardware monitoring** integrated with inference metrics
4. **Cost tracking** for API usage in real-time
5. **Vector search quality** metrics (similarity, distances)
6. **Error scenarios** properly traced and captured
7. **Nested spans** showing full request flow across services
8. **Apple Silicon GPU support** (MPS) with metrics

**Trade-offs vs Auto-Instrumentation (OpenLIT):**

| Feature           | This Demo (Manual)                 | OpenLIT (Auto)                   |
| ----------------- | ---------------------------------- | -------------------------------- |
| Setup complexity  | Higher (explicit code)             | Lower (one-line init)            |
| Customization     | Full control                       | Limited                          |
| Hardware metrics  | Custom per-service                 | Separate collector               |
| Vector DB quality | Detailed attributes                | Basic only                       |
| Cost calculation  | Real-time custom                   | Pre-built                        |
| Learning curve    | Steeper                            | Easier                           |
| Best for          | Production platforms, custom needs | Rapid prototyping, standard LLMs |

**When manual OTel makes sense:**

- Custom model serving infrastructure
- Non-standard vector DB implementations
- Business-specific metrics requirements
- Multi-tenant platforms with complex attribution
- SLA/SLO enforcement with custom alerting
- Deep hardware integration needs

**When OpenLIT makes sense:**

- Standard OpenAI/Anthropic/Cohere APIs
- Quick MVP or proof-of-concept
- Standard LangChain/LlamaIndex apps
- Small teams without DevOps resources

## Next Steps

1. **Explore Grafana Cloud:**

   - View traces: Filter by `service.name=ai-observability-demo`
   - Build dashboards: Use Prometheus metrics for visualization
   - Set alerts: On costs, latency, error rates

2. **Customize for your use case:**

   - Add your own models/endpoints
   - Extend custom metrics
   - Add business-specific attributes

3. **Production readiness:**
   - Add authentication/authorization
   - Implement rate limiting
   - Set up proper error handling
   - Configure log aggregation
   - Add health probes for orchestration

## Support

**Issues?** Check the logs first:

```bash
tail -100 /tmp/ai-demo.log
```

**Still stuck?** Verify prerequisites:

- Python 3.11+
- PyTorch with MPS/CUDA support
- Valid OpenAI API key
- Grafana Cloud OTLP credentials

---

**Last Updated:** 2025-10-14  
**Server Status:** Running on PID 51055, port 8080  
**Demo Scenarios:** Successfully executed all scenarios  
**Telemetry Status:** Flowing to Grafana Cloud (verified)
