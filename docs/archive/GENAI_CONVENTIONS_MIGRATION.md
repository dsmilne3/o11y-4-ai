# GenAI Semantic Conventions Migration

## Overview

This document summarizes the migration of manual OpenTelemetry instrumentation to use GenAI Semantic Conventions, enabling direct comparison with OpenLIT auto-instrumentation in Grafana Cloud.

## Objective

Enable side-by-side comparison of:

- **Manual OpenTelemetry** (telemetry_sdk_name="opentelemetry") using GenAI conventions
- **OpenLIT auto-instrumentation** (telemetry_sdk_name="openlit") using GenAI conventions

Both instrumentations now use the same attribute namespace and metric naming patterns, differentiated only by the `telemetry.sdk.name` resource attribute.

## Changes Summary

### Span Names

| Before                  | After                     |
| ----------------------- | ------------------------- |
| `llm.chat_completion`   | `gen_ai.chat.completions` |
| `llm.create_embeddings` | `gen_ai.embeddings`       |

### Attributes

| Before                        | After                            | Description                |
| ----------------------------- | -------------------------------- | -------------------------- |
| `llm.vendor`                  | `gen_ai.system`                  | AI system (e.g., "openai") |
| `llm.request.model`           | `gen_ai.request.model`           | Model name                 |
| `llm.request.temperature`     | `gen_ai.request.temperature`     | Temperature parameter      |
| `llm.request.max_tokens`      | `gen_ai.request.max_tokens`      | Max tokens parameter       |
| `llm.usage.prompt_tokens`     | `gen_ai.usage.input_tokens`      | Input token count          |
| `llm.usage.completion_tokens` | `gen_ai.usage.output_tokens`     | Output token count         |
| `llm.usage.total_tokens`      | `gen_ai.usage.total_tokens`      | Total token count          |
| `llm.response.finish_reason`  | `gen_ai.response.finish_reasons` | Completion finish reason   |
| `llm.token.cost`              | `gen_ai.token.cost`              | Cost per token             |

### Metrics

| Before                         | After                              | Description                                                         |
| ------------------------------ | ---------------------------------- | ------------------------------------------------------------------- |
| `llm_request_duration_seconds` | `gen_ai.client.operation.duration` | Operation latency (seconds)                                         |
| `llm_tokens_total`             | `gen_ai.client.token.usage`        | Token usage counter                                                 |
| `llm_requests_total`           | `gen_ai.client.operation.count`    | Operation count                                                     |
| `llm_cost_total`               | `gen_ai.client.operation.cost`     | Total cost (USD)                                                    |
| `llm_errors_total`             | _(removed)_                        | Now tracked via `gen_ai.client.operation.count` with `status=error` |

### Metric Labels

All metrics now include standardized GenAI labels:

- `gen_ai.system`: "openai"
- `gen_ai.request.model`: Model name
- `gen_ai.operation.name`: "chat" or "embeddings"
- `status`: "success" or "error"
- `error_type`: Exception type (when status=error)
- `user_id`: Custom user identifier (preserved)
- `session_id`: Custom session identifier (preserved)
- `telemetry_sdk_name`: "opentelemetry" (set at resource level)

## Code Structure

### GenAIAttributes Class

```python
class GenAIAttributes:
    """GenAI Semantic Convention attribute names."""
    SYSTEM = "gen_ai.system"
    REQUEST_MODEL = "gen_ai.request.model"
    REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"
    RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
    TOKEN_COST = "gen_ai.token.cost"
    OPERATION_NAME = "gen_ai.operation.name"
```

### Metrics Definitions

```python
# Operation duration
gen_ai_client_operation_duration = Histogram(
    name="gen_ai.client.operation.duration",
    description="Duration of GenAI operations",
    unit="s"
)

# Token usage
gen_ai_client_token_usage = Counter(
    name="gen_ai.client.token.usage",
    description="Total tokens used by GenAI operations",
    unit="tokens"
)

# Operation count
gen_ai_client_operation_count = Counter(
    name="gen_ai.client.operation.count",
    description="Total count of GenAI operations",
    unit="operations"
)

# Operation cost
gen_ai_client_operation_cost = Counter(
    name="gen_ai.client.operation.cost",
    description="Total cost of GenAI operations",
    unit="USD"
)
```

## Testing

### 1. Verify Server Startup

```bash
# Restart server
kill -15 $(lsof -ti:8080)
sleep 2
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Expected output:

```
INFO:     OpenTelemetry initialized with service: ai-demo-app
INFO:     OpenLIT initialized with service: ai-demo-app
INFO:     Application startup complete.
```

### 2. Check Metrics Endpoint

```bash
curl http://localhost:8080/metrics | grep -E "(gen_ai|telemetry_sdk_name)"
```

Expected metrics:

- `gen_ai_client_operation_duration{...}`
- `gen_ai_client_token_usage{...}`
- `gen_ai_client_operation_count{...}`
- `gen_ai_client_operation_cost{...}`
- All metrics should have `telemetry_sdk_name="opentelemetry"` label

### 3. Generate Test Traffic

```bash
# Run demo scenarios
python scripts/demo_scenarios.py --scenario all --iterations 5
```

### 4. Query Grafana Cloud

**Traces:**

```promql
# Manual OTel traces
{telemetry.sdk.name="opentelemetry"} | span_name=~"gen_ai.*"

# OpenLIT traces
{telemetry.sdk.name="openlit"} | span_name=~"gen_ai.*"
```

**Metrics:**

```promql
# Compare operation costs
sum by (telemetry_sdk_name, gen_ai_request_model) (
  rate(gen_ai_client_operation_cost_total[5m])
)

# Compare token usage
sum by (telemetry_sdk_name, gen_ai_request_model, gen_ai_operation_name) (
  rate(gen_ai_client_token_usage_total[5m])
)
```

## Benefits

1. **Standardization**: Using widely adopted GenAI semantic conventions
2. **Interoperability**: Consistent attribute names across manual and auto instrumentation
3. **Comparison**: Direct apples-to-apples comparison via `telemetry.sdk.name` label
4. **Future-proofing**: Aligned with OpenTelemetry's GenAI conventions specification

## References

- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenLIT Documentation](https://docs.openlit.io/)
- [Grafana Cloud OTLP Integration](https://grafana.com/docs/grafana-cloud/send-data/otlp/)

## Maintenance Notes

- Custom attributes (`user_id`, `session_id`) are preserved alongside GenAI conventions
- Cost calculation logic remains unchanged
- Error tracking now uses standard `status` and `error_type` labels instead of separate metrics
- OpenLIT auto-instrumentation automatically adds similar telemetry without code changes
