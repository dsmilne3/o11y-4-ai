# Getting Started with AI Observability Demo

This guide will help you set up and run the AI Observability Demo to showcase comprehensive monitoring of AI workloads.

## Prerequisites

### Required

- **Python 3.9+** with pip
- **OpenAI API Key** - Get one from [OpenAI Platform](https://platform.openai.com/api-keys)

### Optional

- **CUDA-compatible GPU** for local model acceleration
- **Grafana Cloud Account** for remote observability ([free tier available](https://grafana.com/cloud/))

## Quick Start (5 minutes)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd o11y-4-ai

# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Configure Environment

Edit the `.env` file with your API keys:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: Grafana Cloud (for remote monitoring)
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic your_base64_credentials
```

### 3. Start the Application

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or venv\Scripts\activate  # Windows

# Start the demo application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Run Demo Scenarios

In a new terminal:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all demo scenarios
python scripts/demo_scenarios.py

# Or run specific scenarios
python scripts/demo_scenarios.py --scenario chat
python scripts/demo_scenarios.py --scenario pipeline
```

### 5. View Results

- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health
- **Metrics**: http://localhost:8000/metrics
- **Application Stats**: http://localhost:8080/stats

## What You'll See

### 1. **Comprehensive Traces**

- End-to-end request tracing across all AI components
- LLM operation spans with token usage and costs
- Vector database operations
- Local model inference with GPU metrics

### 2. **Rich Metrics**

- Request rates, latencies, and error rates
- Token consumption and API costs
- GPU utilization and memory usage
- Vector database performance
- Custom business metrics

### 3. **Structured Logs**

- Correlated logs with trace IDs
- Performance insights
- Error details with context
- Business events

## API Endpoints

### Core AI Operations

```bash
# Chat completion with OpenAI
curl -X POST "http://localhost:8080/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?", "user_id": "demo_user"}'

# Generate and store embeddings
curl -X POST "http://localhost:8080/embed" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Machine learning is a subset of AI"], "user_id": "demo_user"}'

# Vector similarity search
curl -X POST "http://localhost:8080/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?", "n_results": 5, "user_id": "demo_user"}'

# Local model inference
curl -X POST "http://localhost:8080/local-inference" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "The future of AI is", "max_length": 100, "user_id": "demo_user"}'

# Full AI pipeline demonstration
curl -X POST "http://localhost:8080/full-pipeline?query=Explain%20neural%20networks&user_id=demo_user"
```

### Observability Endpoints

```bash
# Health check with service status
curl http://localhost:8080/health

# Prometheus metrics
curl http://localhost:8000/metrics

# System statistics
curl http://localhost:8080/stats
```

## Grafana Cloud Integration

### Telemetry Export Options

The application can send telemetry to Grafana Cloud in two ways:

**Direct OTLP Export (No Alloy Required):**
- ✅ **Traces**: Sent directly via OTLP HTTP/gRPC
- ✅ **Metrics**: Sent directly via OTLP HTTP/gRPC
- ❌ **Logs**: Not sent directly (requires Alloy)

**Via Grafana Alloy (Optional but Recommended):**
- ✅ **Traces**: Can be collected and forwarded (or use direct export)
- ✅ **Metrics**: Can scrape Prometheus metrics and forward to Grafana Cloud
- ✅ **Logs**: Required for sending logs to Grafana Cloud (Loki)
- ✅ **System Metrics**: Additional system-level metrics collection

**Note:** If you only need traces and metrics, you can use direct OTLP export by configuring `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` in your `.env` file. Alloy is **required** if you want to send logs to Grafana Cloud.

### 1. **Get Grafana Cloud Credentials**

Sign up for [Grafana Cloud](https://grafana.com/cloud/) and get:

- OTLP endpoint and credentials (for direct export or Alloy)
- Prometheus endpoint and credentials (for Alloy)
- Loki endpoint and credentials (for Alloy - **required for logs**)

### 2. **Configure Grafana Alloy** (Optional for Logs)

```bash
# Copy Alloy environment file
cp config/alloy.env.example config/alloy.env

# Edit with your Grafana Cloud credentials
vim config/alloy.env
```

### 3. **Start Grafana Alloy**

```bash
# Install Grafana Alloy
# macOS: brew install grafana/grafana/alloy
# Linux: See https://grafana.com/docs/alloy/latest/set-up/install/

# Start Alloy
./scripts/start-alloy.sh
```

### 4. **Enable AI Observability Integration**

In your Grafana Cloud instance:

1. Go to **Integrations** → **AI Observability**
2. Install the integration
3. Import the pre-built dashboards
4. Set up alerting rules

## Advanced Configuration

### Local Model Configuration

For GPU acceleration:

```env
# .env file
USE_GPU=true
GPU_DEVICE_ID=0
LOCAL_MODEL_NAME=microsoft/DialoGPT-medium
```

For CPU-only (slower but works everywhere):

```env
USE_GPU=false
LOCAL_MODEL_NAME=microsoft/DialoGPT-small
```

### Vector Database Options

**Embedded ChromaDB** (default):

```env
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
CHROMA_COLLECTION_NAME=ai_demo_collection
```

**External ChromaDB**:

```bash
# Start with Docker profile
docker-compose --profile external-chromadb up chromadb

# Update .env
echo "CHROMA_SERVER_URL=http://localhost:8001" >> .env
```

### Performance Testing

```bash
# Run performance tests
python scripts/performance_test.py --concurrent-users 10 --duration 120

# Mixed workload test
python scripts/performance_test.py --test-type mixed --duration 300 --output results.json

# Load simulation
python scripts/demo_scenarios.py --scenario load --load-duration 10
```

## Troubleshooting

### Common Issues

**"Import errors"**: Make sure virtual environment is activated and dependencies are installed

```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"OpenAI API errors"**: Check your API key and quota

```bash
# Test your API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**"GPU not detected"**: Verify CUDA installation

```bash
# Check CUDA
nvidia-smi

# Check PyTorch CUDA support
python -c "import torch; print(torch.cuda.is_available())"
```

**"Port already in use"**: Change ports in `.env`

```env
APP_PORT=8081
PROMETHEUS_PORT=8001
```

### Logs and Debugging

```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
echo "DEBUG_MODE=true" >> .env

# Check application logs
tail -f logs/app.log
```

## What's Next?

1. **Explore Dashboards**: Use the pre-built Grafana dashboards to analyze AI performance
2. **Set Up Alerts**: Configure alerts for high costs, errors, or performance degradation
3. **Custom Metrics**: Add your own business metrics using the OpenTelemetry SDK
4. **Scale Testing**: Run load tests to understand system limits
5. **Production Deployment**: Deploy to Kubernetes or cloud platforms

## Learn More

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Observability](https://grafana.com/products/cloud/)
- [AI Observability Best Practices](https://grafana.com/blog/2024/03/13/observability-for-llms/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)

## Support

- 📖 Check the full documentation in the repository
- 🐛 Report issues on GitHub
- 💬 Join the community discussions
- 📧 Contact support for enterprise features
