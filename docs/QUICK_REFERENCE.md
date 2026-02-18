# Quick Reference: Metric Parity Cheat Sheet

## ✅ Implemented Metrics

| Metric Name                           | Type      | Purpose                 | Both?       |
| ------------------------------------- | --------- | ----------------------- | ----------- |
| `gen_ai.client.operation.duration`    | Histogram | Request latency         | ✅          |
| `gen_ai.total_requests`               | Counter   | Total requests          | ✅          |
| `gen_ai.usage.input_tokens`           | Counter   | Input tokens consumed   | ✅          |
| `gen_ai.usage.output_tokens`          | Counter   | Output tokens generated | ✅          |
| `gen_ai.usage.cost`                   | Histogram | Cost distribution       | ✅          |
| `gen_ai.server.time_per_output_token` | Histogram | Token generation speed  | ✅          |
| `gen_ai.client.token.usage`           | Counter   | Tokens by type          | ✅          |
| `gen_ai.client.operation.count`       | Counter   | Ops with status         | Manual only |
| `gen_ai.client.operation.cost`        | Counter   | Per-user costs          | Manual only |

## ⚠️ Not Implemented

| Metric Name                         | Why Not         | Effort |
| ----------------------------------- | --------------- | ------ |
| `gen_ai.server.time_to_first_token` | Needs streaming | High   |

## 🔍 Quick Tests

### Check Both Instrumentations Working

```bash
curl -s http://localhost:8080/metrics | grep "gen_ai_total_requests_total{" | grep -v "^#"
```

### Compare Token Counts

```bash
curl -s http://localhost:8080/metrics | grep "gen_ai_usage_input_tokens.*_total{" | grep -v "^#"
```

### Compare Costs

```bash
curl -s http://localhost:8080/metrics | grep "gen_ai_usage_cost_USD_sum{" | grep -v "^#"
```

### Generate Test Traffic

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "user_id": "user123"}'
```

## 📊 Grafana Filters

### Manual OTel

```promql
{} and on() (target_info{telemetry_sdk_name="opentelemetry"})
```

### OpenLIT

```promql
{telemetry_sdk_name="openlit"}
```

## ✨ Key Attributes

Both implementations include:

- `gen_ai.system` → "openai"
- `gen_ai.request.model` → requested model
- `gen_ai.response.model` → actual model
- `gen_ai.operation.name` → "chat" or "embeddings"
- `server_address` → "api.openai.com"
- `server_port` → 443

Manual OTel adds:

- `user_id` → custom user tracking
- `session_id` → session correlation
- `status` → "success" or "error"
- `error_type` → exception class

## 📈 Result

**Parity Score: 83% (15/18 metric series)**

Ready for production comparison in Grafana Cloud! 🚀
