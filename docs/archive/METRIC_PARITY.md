# Metric Parity: Manual OTel vs OpenLIT

## Overview

This document tracks the parity between manual OpenTelemetry instrumentation and OpenLIT auto-instrumentation. The goal is to ensure that both approaches provide comparable telemetry for meaningful comparison.

## Metrics Comparison

### ✅ Fully Implemented

| Metric                                | Manual OTel  | OpenLIT      | Notes                      |
| ------------------------------------- | ------------ | ------------ | -------------------------- |
| `gen_ai.client.operation.duration`    | ✅ Histogram | ✅ Histogram | Operation latency tracking |
| `gen_ai.total_requests`               | ✅ Counter   | ✅ Counter   | Total request count        |
| `gen_ai.usage.input_tokens`           | ✅ Counter   | ✅ Counter   | Input token consumption    |
| `gen_ai.usage.output_tokens`          | ✅ Counter   | ✅ Counter   | Output token generation    |
| `gen_ai.usage.cost`                   | ✅ Histogram | ✅ Histogram | Cost distribution          |
| `gen_ai.server.time_per_output_token` | ✅ Histogram | ✅ Histogram | Average time per token     |

### ⚠️ Partially Implemented

| Metric                              | Manual OTel          | OpenLIT      | Notes                                            |
| ----------------------------------- | -------------------- | ------------ | ------------------------------------------------ |
| `gen_ai.server.time_to_first_token` | ❌ Not yet           | ✅ Yes       | Requires streaming support to measure accurately |
| `gen_ai.client.token.usage`         | ✅ Counter (by type) | ✅ Histogram | Different metric types, both valid               |

### ✅ Additional Metrics (Manual OTel Only)

| Metric                          | Purpose                                                 |
| ------------------------------- | ------------------------------------------------------- |
| `gen_ai.client.operation.count` | Operation count with status labels (success/error)      |
| `gen_ai.client.operation.cost`  | Cost counter with user_id labels for per-user tracking  |
| `gen_ai.client.token.usage`     | Token counter with user_id labels for per-user tracking |

## Attributes Comparison

### Common Attributes (Both Implementations)

| Attribute               | Example Value              | Description        |
| ----------------------- | -------------------------- | ------------------ |
| `gen_ai.system`         | `"openai"`                 | AI system provider |
| `gen_ai.request.model`  | `"gpt-4-turbo-preview"`    | Requested model    |
| `gen_ai.response.model` | `"gpt-4-0125-preview"`     | Actual model used  |
| `gen_ai.operation.name` | `"chat"` or `"embeddings"` | Operation type     |
| `server_address`        | `"api.openai.com"`         | Server endpoint    |
| `server_port`           | `443`                      | Server port        |

### OpenLIT-Specific Attributes

| Attribute                | Example Value             | Description                   |
| ------------------------ | ------------------------- | ----------------------------- |
| `deployment_environment` | `"demo"`                  | Environment name              |
| `service_name`           | `"ai-observability-demo"` | Service identifier            |
| `telemetry_sdk_name`     | `"openlit"`               | SDK identifier (metric label) |

### Manual OTel-Specific Attributes

| Attribute    | Example Value            | Description                  |
| ------------ | ------------------------ | ---------------------------- |
| `user_id`    | `"test_user"`            | User identifier for tracking |
| `session_id` | `"test_session"`         | Session identifier           |
| `status`     | `"success"` or `"error"` | Operation status             |
| `error_type` | Exception class name     | Error classification         |

Note: Manual OTel sets `telemetry_sdk_name="opentelemetry"` as a resource attribute, not a metric label.

## Span Comparison

### Span Names

| Operation       | Manual OTel               | OpenLIT                          | Standard      |
| --------------- | ------------------------- | -------------------------------- | ------------- |
| Chat completion | `gen_ai.chat.completions` | `gen_ai.client.chat.completions` | GenAI semconv |
| Embeddings      | `gen_ai.embeddings`       | `gen_ai.client.embeddings`       | GenAI semconv |

Both implementations follow GenAI semantic conventions with slight naming variations.

### Span Attributes

Both implementations include:

- Request parameters (model, temperature, max_tokens)
- Usage statistics (input_tokens, output_tokens)
- Response metadata (finish_reasons, response_id)
- Cost information

Manual OTel additionally includes:

- Span events for individual input messages
- Custom business context (user_id, session_id)

## Implementation Details

### Manual OTel Approach

**Strengths:**

- Fine-grained control over telemetry
- Custom business attributes (user_id, session_id)
- Detailed span events for message tracking
- Flexible metric labeling for per-user analysis
- Error tracking with detailed error_type labels

**Limitations:**

- Requires code changes for new instrumentation
- No TTFT tracking without streaming implementation
- More code to maintain

### OpenLIT Approach

**Strengths:**

- Zero-code instrumentation (automatic)
- Comprehensive out-of-the-box metrics
- TTFT tracking for streaming responses
- Automatic cost tracking with built-in pricing database
- Consistent instrumentation across multiple AI providers

**Limitations:**

- Less control over custom attributes
- May not capture business-specific context
- Resource attributes set differently (metric labels vs resource attributes)

## Side-by-Side Example

### Manual OTel Metric

```promql
gen_ai_total_requests_total{
  gen_ai_operation_name="chat",
  gen_ai_request_model="gpt-4-turbo-preview",
  gen_ai_response_model="gpt-4-0125-preview",
  gen_ai_system="openai",
  server_address="api.openai.com",
  server_port="443"
} 1.0
```

### OpenLIT Metric

```promql
gen_ai_total_requests_total{
  deployment_environment="demo",
  gen_ai_operation_name="chat",
  gen_ai_request_model="gpt-4-turbo-preview",
  gen_ai_response_model="gpt-4-0125-preview",
  gen_ai_system="openai",
  server_address="api.openai.com",
  server_port="443",
  service_name="ai-observability-demo",
  telemetry_sdk_name="openlit"
} 1.0
```

## Querying in Grafana Cloud

### Comparing Request Counts

```promql
# Manual OTel (filter by resource attribute)
sum(rate(gen_ai_total_requests_total[5m]))
  by (gen_ai_request_model)
  and on() (target_info{telemetry_sdk_name="opentelemetry"})

# OpenLIT (filter by metric label)
sum(rate(gen_ai_total_requests_total{telemetry_sdk_name="openlit"}[5m]))
  by (gen_ai_request_model)
```

### Comparing Token Usage

```promql
# Total input tokens - Manual OTel
sum(rate(gen_ai_usage_input_tokens_total[5m]))
  by (gen_ai_request_model)
  and on() (target_info{telemetry_sdk_name="opentelemetry"})

# Total input tokens - OpenLIT
sum(rate(gen_ai_usage_input_tokens_total{telemetry_sdk_name="openlit"}[5m]))
  by (gen_ai_request_model)
```

### Comparing Costs

```promql
# Cost distribution - Manual OTel
histogram_quantile(0.95,
  sum(rate(gen_ai_usage_cost_USD_bucket[5m]))
    by (le, gen_ai_request_model)
    and on() (target_info{telemetry_sdk_name="opentelemetry"})
)

# Cost distribution - OpenLIT
histogram_quantile(0.95,
  sum(rate(gen_ai_usage_cost_USD_bucket{telemetry_sdk_name="openlit"}[5m]))
    by (le, gen_ai_request_model)
)
```

## Recommendations

### When to Use Manual OTel

- Need custom business context (user tracking, session correlation)
- Require fine-grained control over instrumentation
- Want to instrument custom AI workflows beyond standard APIs
- Need specific error classification and tracking

### When to Use OpenLIT

- Want zero-code instrumentation
- Need quick setup for standard AI providers
- Require comprehensive metrics out-of-the-box
- Want automatic cost tracking with latest pricing
- Need streaming metrics (TTFT)

### Best Practice: Use Both

As demonstrated in this project:

1. **OpenLIT** for baseline metrics and comparison
2. **Manual OTel** for business-specific telemetry
3. **Differentiate** using `telemetry_sdk_name` attribute
4. **Compare** both approaches in Grafana to validate instrumentation

## Testing Parity

To verify parity, run:

```bash
# Generate test traffic
python scripts/demo_scenarios.py --scenario all --iterations 10

# Compare metric counts
curl -s http://localhost:8080/metrics | grep "gen_ai_total_requests_total" | grep -v "^#"

# Compare token usage
curl -s http://localhost:8080/metrics | grep "gen_ai_usage_input_tokens" | grep "_total{" | grep -v "^#"

# Compare cost tracking
curl -s http://localhost:8080/metrics | grep "gen_ai_usage_cost_USD_sum{" | grep -v "^#"
```

Both implementations should show similar values (within variance due to different request paths through instrumentors).

## Future Enhancements

### For Manual OTel

- [ ] Add streaming support for TTFT measurement
- [ ] Implement prompt caching metrics
- [ ] Add token-level attribution (input vs output costs)
- [ ] Add model performance benchmarking

### For OpenLIT

- [ ] Configure custom attributes (if supported)
- [ ] Explore GPU metrics collection
- [ ] Test with additional AI providers (Anthropic, etc.)

## Conclusion

Both approaches now provide **substantial parity** in terms of:

- Core GenAI semantic convention metrics
- Standard attributes for filtering and aggregation
- Cost and token tracking
- Operation latency measurement

The main differences are:

- **Attribute scope**: OpenLIT uses metric labels, Manual OTel uses resource attributes
- **Custom context**: Manual OTel includes user_id/session_id
- **TTFT**: OpenLIT supports, Manual OTel requires streaming implementation

This parity enables direct comparison and validation of both approaches in production monitoring.
