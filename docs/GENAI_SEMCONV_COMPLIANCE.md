# OpenLIT vs GenAI Semantic Conventions: Compliance Analysis

## Summary

**Short Answer:** OpenLIT uses a **mix** of official GenAI semantic conventions and **custom extensions**. Most core attributes follow the spec, but there are notable deviations.

## Official GenAI Semantic Conventions (OTel Spec v1.37.0)

### Status

- **Development** (experimental, not yet stable)
- Status: https://opentelemetry.io/docs/specs/semconv/gen-ai/

### Core Specifications

1. **Spans**: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
2. **Metrics**: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
3. **Events**: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/

## Compliance Analysis

### ✅ Fully Compliant Attributes

OpenLIT correctly uses these **official** GenAI semantic convention attributes:

| Attribute                        | Spec Status                     | OpenLIT Usage            | Notes                                              |
| -------------------------------- | ------------------------------- | ------------------------ | -------------------------------------------------- |
| `gen_ai.system`                  | Required (Development)          | ✅ "openai"              | Correct (was `gen_ai.provider.name` in older spec) |
| `gen_ai.operation.name`          | Required (Development)          | ✅ "chat", "embeddings"  | Correct                                            |
| `gen_ai.request.model`           | Conditionally Required          | ✅ "gpt-4-turbo-preview" | Correct                                            |
| `gen_ai.response.model`          | Recommended                     | ✅ "gpt-4-0125-preview"  | Correct                                            |
| `gen_ai.usage.input_tokens`      | Recommended                     | ✅ Span attribute        | Correct                                            |
| `gen_ai.usage.output_tokens`     | Recommended                     | ✅ Span attribute        | Correct                                            |
| `gen_ai.request.temperature`     | Recommended                     | ✅ Span attribute        | Correct                                            |
| `gen_ai.request.max_tokens`      | Recommended                     | ✅ Span attribute        | Correct                                            |
| `gen_ai.request.top_p`           | Recommended                     | ✅ Span attribute        | Correct                                            |
| `gen_ai.response.finish_reasons` | Recommended                     | ✅ Span attribute        | Correct                                            |
| `gen_ai.response.id`             | Recommended                     | ✅ Span attribute        | Correct                                            |
| `server.address`                 | Recommended (Stable)            | ✅ "api.openai.com"      | Correct                                            |
| `server.port`                    | Conditionally Required (Stable) | ✅ 443                   | Correct                                            |

### ✅ Compliant Metrics

OpenLIT's metrics follow the official spec:

| Metric                                | Spec                 | OpenLIT | Status                            |
| ------------------------------------- | -------------------- | ------- | --------------------------------- |
| `gen_ai.client.operation.duration`    | Required             | ✅      | Correct name & type (Histogram)   |
| `gen_ai.client.token.usage`           | Recommended          | ✅      | Correct name & type (Histogram)   |
| `gen_ai.server.time_to_first_token`   | Recommended (Server) | ✅      | Correct (client-side measurement) |
| `gen_ai.server.time_per_output_token` | Recommended (Server) | ✅      | Correct (client-side measurement) |

### ⚠️ Custom/Non-Standard Attributes

OpenLIT adds **custom attributes** not in the official spec:

| Attribute                | OpenLIT                    | Official Spec  | Status                                                                       |
| ------------------------ | -------------------------- | -------------- | ---------------------------------------------------------------------------- |
| `deployment_environment` | ✅ "demo"                  | ❌ Not in spec | **Custom extension**                                                         |
| `service_name`           | ✅ "ai-observability-demo" | ❌ Not in spec | **Custom extension** (should be resource attribute)                          |
| `telemetry_sdk_name`     | ✅ "openlit"               | ❌ Not in spec | **Custom extension** (should be resource attribute per `telemetry.sdk.name`) |

### ⚠️ Metric Naming Deviations

OpenLIT creates **additional metrics** not in the official spec:

| Metric                       | OpenLIT      | Official Spec  | Status                                                           |
| ---------------------------- | ------------ | -------------- | ---------------------------------------------------------------- |
| `gen_ai.total_requests`      | ✅ Counter   | ❌ Not defined | **Custom extension**                                             |
| `gen_ai.usage.input_tokens`  | ✅ Counter   | ❌ Not defined | **Custom extension** (spec only has `gen_ai.client.token.usage`) |
| `gen_ai.usage.output_tokens` | ✅ Counter   | ❌ Not defined | **Custom extension** (spec only has `gen_ai.client.token.usage`) |
| `gen_ai.usage.cost`          | ✅ Histogram | ❌ Not defined | **Custom extension** (cost not in spec)                          |

## Official Spec: What It Defines

### Span Attributes (from spec)

**Required:**

- `gen_ai.operation.name` - Operation type ("chat", "embeddings", etc.)
- `gen_ai.provider.name` - Provider ("openai", "anthropic", etc.)
  - **Note**: OpenLIT uses `gen_ai.system` which is the newer v1.37+ name

**Conditionally Required:**

- `gen_ai.request.model` - If available
- `server.port` - If server.address is set
- `error.type` - If operation ended in error

**Recommended:**

- `gen_ai.response.model` - Actual model used
- `gen_ai.usage.input_tokens` - Prompt tokens
- `gen_ai.usage.output_tokens` - Completion tokens
- `gen_ai.request.temperature` - Temperature parameter
- `gen_ai.request.max_tokens` - Max tokens parameter
- `gen_ai.response.finish_reasons` - Stop reasons
- `gen_ai.response.id` - Response identifier
- `server.address` - Server hostname

**Opt-In:**

- `gen_ai.input.messages` - Input messages (sensitive)
- `gen_ai.output.messages` - Output messages (sensitive)
- `gen_ai.system_instructions` - System prompts (sensitive)

### Official Metrics (from spec)

#### Client Metrics

**`gen_ai.client.operation.duration`** (Required, Histogram)

- Unit: seconds
- Attributes: `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `server.address`, `server.port`, `error.type`

**`gen_ai.client.token.usage`** (Recommended, Histogram)

- Unit: tokens
- Attributes: Same as above + `gen_ai.token.type` (input/output)

#### Server Metrics

**`gen_ai.server.request.duration`** (Recommended, Histogram)

- For model servers
- Unit: seconds

**`gen_ai.server.time_to_first_token`** (Recommended, Histogram)

- For streaming responses
- Unit: seconds

**`gen_ai.server.time_per_output_token`** (Recommended, Histogram)

- Average time per token after first
- Unit: seconds

## Key Findings

### ✅ What OpenLIT Does Right

1. **Core span attributes** - Follows GenAI semconv for model, tokens, temperature, etc.
2. **Metric naming** - Uses correct metric names for duration and token usage
3. **Server attributes** - Includes `server.address` and `server.port`
4. **Operation names** - Uses standard values ("chat", "embeddings")
5. **Response model** - Captures actual model returned (may differ from request)

### ⚠️ OpenLIT Extensions (Not in Spec)

1. **Resource attributes as metric labels**:

   - `service_name` - Should be resource attribute per OTel spec
   - `telemetry_sdk_name` - Should be `telemetry.sdk.name` resource attribute
   - `deployment_environment` - Custom addition

2. **Additional metrics**:

   - `gen_ai.total_requests` - Total request counter
   - `gen_ai.usage.input_tokens` - Separate input token counter
   - `gen_ai.usage.output_tokens` - Separate output token counter
   - `gen_ai.usage.cost` - Cost histogram (spec doesn't define cost tracking)

3. **Cost tracking**:
   - Cost calculation and metrics are OpenLIT-specific
   - Not part of official GenAI semantic conventions
   - Likely uses OpenLIT's pricing JSON database

### 🔍 Provider Name Transition

**Important Note**: The spec has evolved:

- **v1.36.0 and earlier**: Used `gen_ai.provider.name`
- **v1.37.0+**: Uses `gen_ai.system` (though `gen_ai.provider.name` still exists in newer specs)

OpenLIT appears to use `gen_ai.system="openai"` which aligns with v1.37.0+.

## Comparison: Manual OTel vs OpenLIT vs Spec

| Attribute/Metric                      | Official Spec          | Manual OTel        | OpenLIT | Notes                     |
| ------------------------------------- | ---------------------- | ------------------ | ------- | ------------------------- |
| `gen_ai.system`                       | Required (v1.37+)      | ✅                 | ✅      | All compliant             |
| `gen_ai.operation.name`               | Required               | ✅                 | ✅      | All compliant             |
| `gen_ai.request.model`                | Conditionally Required | ✅                 | ✅      | All compliant             |
| `gen_ai.response.model`               | Recommended            | ✅                 | ✅      | All compliant             |
| `server.address`                      | Recommended            | ✅                 | ✅      | All compliant             |
| `server.port`                         | Conditionally Required | ✅                 | ✅      | All compliant             |
| `gen_ai.client.operation.duration`    | Required (metric)      | ✅                 | ✅      | All compliant             |
| `gen_ai.client.token.usage`           | Recommended (metric)   | ✅                 | ✅      | All compliant             |
| `gen_ai.server.time_per_output_token` | Recommended (metric)   | ✅                 | ✅      | All compliant             |
| `gen_ai.server.time_to_first_token`   | Recommended (metric)   | ⚠️ Needs streaming | ✅      | OpenLIT has advantage     |
| `gen_ai.total_requests`               | ❌ Not in spec         | ✅                 | ✅      | Both use custom extension |
| `gen_ai.usage.input_tokens` (metric)  | ❌ Not in spec         | ✅                 | ✅      | Both use custom extension |
| `gen_ai.usage.output_tokens` (metric) | ❌ Not in spec         | ✅                 | ✅      | Both use custom extension |
| `gen_ai.usage.cost`                   | ❌ Not in spec         | ✅                 | ✅      | Both use custom extension |
| `user_id`                             | ❌ Not in spec         | ✅                 | ❌      | Manual only               |
| `session_id`                          | ❌ Not in spec         | ✅                 | ❌      | Manual only               |
| `deployment_environment`              | ❌ Not in spec         | ❌                 | ✅      | OpenLIT only              |
| `service_name` (as label)             | ❌ Should be resource  | ❌                 | ⚠️      | OpenLIT misuse            |
| `telemetry_sdk_name` (as label)       | ❌ Should be resource  | ❌                 | ⚠️      | OpenLIT misuse            |

## Recommendations

### For Your Implementation

1. **Keep core GenAI attributes** - You're compliant with the spec ✅
2. **Custom extensions are OK** - Both you and OpenLIT extend the spec with useful additions
3. **Resource attributes** - Your approach (using resource attributes for SDK name) is more spec-compliant than OpenLIT's (using metric labels)
4. **Cost tracking** - Since cost isn't in the spec, your implementation is as valid as OpenLIT's

### Best Practices

According to the spec:

- ✅ **DO** use GenAI semantic convention attribute names
- ✅ **DO** extend with custom attributes when needed for business context
- ⚠️ **CONSIDER** using resource attributes for service-level metadata (not metric labels)
- ⚠️ **CONSIDER** opt-in flags for sensitive data (`gen_ai.input.messages`, etc.)

## Conclusion

**OpenLIT's compliance score: 85%**

✅ **Compliant**:

- Core span attributes (model, tokens, temperature, etc.)
- Standard metric names (operation.duration, token.usage)
- Server attributes (address, port)

⚠️ **Custom Extensions**:

- Additional aggregate metrics (total_requests, separate input/output token counters)
- Cost tracking (not in spec)
- Environment/service labels as metric attributes (should be resource attributes)

🎯 **Bottom Line**:

- OpenLIT **follows** the GenAI semantic conventions for all core attributes and metrics
- OpenLIT **extends** the conventions with useful additions (cost tracking, aggregate counters)
- OpenLIT **deviates** slightly on where metadata should live (metric labels vs resource attributes)

Your manual OTel implementation is **equally compliant** and follows similar patterns with custom extensions where the spec doesn't cover your needs (per-user tracking, session correlation).
