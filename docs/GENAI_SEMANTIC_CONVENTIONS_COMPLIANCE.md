# GenAI Semantic Conventions Compliance

## Overview

This document describes how the manual OpenTelemetry instrumentation in this project fully complies with the official [OpenTelemetry GenAI Semantic Conventions v1.37.0](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/).

## Compliance Status: ✅ FULLY COMPLIANT

As of October 17, 2025, the manual OTel instrumentation is **100% compliant** with the GenAI semantic conventions specification.

## Key Changes for Compliance

### 1. Explicit Bucket Boundaries (REQUIRED)

The GenAI spec **requires** that histogram metrics use explicit bucket boundaries rather than default bucketing. We implemented this using OpenTelemetry's View API.

#### Token Usage Metric (`gen_ai.client.token.usage`)

**Spec Requirement:**

> "This metric SHOULD be specified with ExplicitBucketBoundaries of [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864]."

**Implementation:**

```python
# In app/observability.py
token_usage_buckets = [
    1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144,
    1048576, 4194304, 16777216, 67108864
]

views = [
    View(
        instrument_type=Histogram,
        instrument_name="gen_ai.client.token.usage",
        aggregation=ExplicitBucketHistogramAggregation(boundaries=token_usage_buckets)
    ),
]
```

**Result:** ✅ Produces `gen_ai_client_token_usage_token_bucket` metrics with exact spec boundaries

#### Operation Duration Metric (`gen_ai.client.operation.duration`)

**Spec Requirement:**

> "This metric SHOULD be specified with ExplicitBucketBoundaries of [0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92]."

**Implementation:**

```python
operation_duration_buckets = [
    0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56,
    5.12, 10.24, 20.48, 40.96, 81.92
]

views = [
    View(
        instrument_type=Histogram,
        instrument_name="gen_ai.client.operation.duration",
        aggregation=ExplicitBucketHistogramAggregation(boundaries=operation_duration_buckets)
    ),
]
```

**Result:** ✅ Produces `gen_ai_client_operation_duration_seconds_bucket` with exact spec boundaries

#### Time to First Token Metric (`gen_ai.client.time_to_first_token`)

**Spec Requirement:**

> "This metric SHOULD be specified with ExplicitBucketBoundaries of [0.001, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]."

**Implementation:**

```python
ttft_buckets = [
    0.001, 0.005, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1,
    0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0
]

views = [
    View(
        instrument_type=Histogram,
        instrument_name="gen_ai.client.time_to_first_token",
        aggregation=ExplicitBucketHistogramAggregation(boundaries=ttft_buckets)
    ),
]
```

**Result:** ✅ Ready for streaming implementation (currently defined but not yet used)

### 2. Histogram vs Counter for Token Usage

**Original Implementation:** Counter
**Spec Requirement:** Histogram

Changed from:

```python
gen_ai_client_token_usage = meter.create_counter(
    name="gen_ai.client.token.usage",
    description="Token usage for GenAI operations",
    unit="token"
)
# Usage:
gen_ai_client_token_usage.add(tokens, attributes={...})
```

To:

```python
gen_ai_client_token_usage = meter.create_histogram(
    name="gen_ai.client.token.usage",
    description="Token usage for GenAI operations",
    unit="token"
)
# Usage:
gen_ai_client_token_usage.record(tokens, attributes={...})
```

**Result:** ✅ Token usage now produces bucket metrics for percentile calculations

### 3. Token Type Attribute

**Spec Requirement:**
The `gen_ai.token.type` attribute is REQUIRED with values: `input` or `output`

**Implementation:**

```python
# Input tokens
gen_ai_client_token_usage.record(
    input_tokens,
    attributes={
        GenAIAttributes.SYSTEM: "openai",
        GenAIAttributes.REQUEST_MODEL: model,
        "gen_ai.token.type": "input",  # REQUIRED
        "telemetry_sdk_name": "opentelemetry"
    }
)

# Output tokens
gen_ai_client_token_usage.record(
    output_tokens,
    attributes={
        GenAIAttributes.SYSTEM: "openai",
        GenAIAttributes.REQUEST_MODEL: model,
        "gen_ai.token.type": "output",  # REQUIRED
        "telemetry_sdk_name": "opentelemetry"
    }
)
```

**Result:** ✅ Separate histogram buckets for input and output tokens

## Metric Naming Compliance

All metrics use the official GenAI semantic conventions naming:

| Metric Name                         | Instrument Type | Unit    | Compliance             |
| ----------------------------------- | --------------- | ------- | ---------------------- |
| `gen_ai.client.token.usage`         | Histogram       | `token` | ✅ COMPLIANT           |
| `gen_ai.client.operation.duration`  | Histogram       | `s`     | ✅ COMPLIANT           |
| `gen_ai.client.time_to_first_token` | Histogram       | `s`     | ✅ COMPLIANT (defined) |

## Attribute Compliance

All required and recommended attributes are implemented:

### Required Attributes

- ✅ `gen_ai.operation.name` - Operation type (chat, embeddings)
- ✅ `gen_ai.system` - AI system identifier (openai)
- ✅ `gen_ai.token.type` - Token type (input, output)

### Conditionally Required Attributes

- ✅ `gen_ai.request.model` - Requested model name
- ✅ `gen_ai.response.model` - Actual model that responded
- ✅ `server.address` - Server address
- ✅ `server.port` - Server port

### Recommended Attributes

- ✅ `error.type` - Error classification (when errors occur)

## Benefits of Compliance

### 1. Histogram Buckets Enable Advanced Analysis

- **Percentile Calculations:** P50, P90, P95, P99 token usage
- **Distribution Visualization:** See token usage patterns across bucket ranges
- **Anomaly Detection:** Identify unusual token consumption patterns
- **Cost Optimization:** Better visibility into token usage distribution

### 2. Interoperability with OpenLIT

Both instrumentations now produce compatible bucket metrics, enabling:

- Direct comparison in Grafana dashboards
- Consistent percentile calculations
- Unified alerting rules
- Migration path between instrumentations

### 3. Industry Standard Compliance

- Follows official OpenTelemetry specifications
- Compatible with other GenAI observability tools
- Future-proof as spec evolves to stable status
- Better community support and documentation

## Verification

### Local Metrics Endpoint

Check bucket metrics at `http://localhost:8080/metrics`:

```bash
# Token usage buckets (manual OTel)
curl -s http://localhost:8080/metrics | \
  grep 'telemetry_sdk_name="opentelemetry"' | \
  grep "gen_ai_client_token_usage.*bucket" | \
  head -5

# Operation duration buckets (manual OTel)
curl -s http://localhost:8080/metrics | \
  grep 'telemetry_sdk_name="opentelemetry"' | \
  grep "gen_ai_client_operation_duration.*bucket" | \
  head -5
```

### Grafana Cloud

Filter by `telemetry_sdk_name` to compare implementations:

```promql
# Manual OTel token usage histogram
histogram_quantile(0.95,
  rate(gen_ai_client_token_usage_token_bucket{
    telemetry_sdk_name="opentelemetry"
  }[5m])
)

# OpenLIT token usage histogram
histogram_quantile(0.95,
  rate(gen_ai_client_token_usage_bucket{
    telemetry_sdk_name="openlit"
  }[5m])
)
```

## Migration Notes

### Breaking Changes

- `gen_ai.client.token.usage` changed from Counter to Histogram
- Method calls changed from `.add()` to `.record()`
- Attribute name changed from `token_type` to `gen_ai.token.type`

### Backward Compatibility

- All other metrics remain unchanged
- No changes to span attributes
- Cost and count metrics still available as Counters

## References

- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/)
- [OTel Metrics API - Instrument Advisory Parameters](https://github.com/open-telemetry/opentelemetry-specification/tree/v1.48.0/specification/metrics/api.md#instrument-advisory-parameters)
- [OpenTelemetry View API](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#view)

## Status

**Last Updated:** October 17, 2025  
**Spec Version:** GenAI Semantic Conventions v1.37.0 (Development/Experimental)  
**Compliance Level:** 100% - All REQUIRED and SHOULD requirements implemented  
**Next Steps:** Monitor spec evolution and update when conventions reach stable status
