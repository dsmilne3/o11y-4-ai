# AI Agent Instructions

## Interaction Rules

**DO NOT make code changes unless explicitly requested.**

When I ask questions like:

- "Why would I want X?"
- "What does Y do?"
- "Should I use A or B?"
- "Explain how X works"
- "Analyze this codebase"
- "What are my options?"

You should:

- ✅ Provide explanations and recommendations
- ✅ Show code examples for illustration
- ✅ Reference existing code patterns
- ❌ **DO NOT create, edit, or modify any files**
- ❌ **DO NOT run commands unless I ask you to**

**Only make changes when I explicitly say:**

- "Create X"
- "Add Y to file Z"
- "Fix the error in X"
- "Update X to do Y"
- "Implement X"

If unsure whether I want changes, **ask first**.

## Research and Verification Rules

**When asked to become an expert, research thoroughly, make recommendations,or compare technologies:**

1. **Do exhaustive research FIRST**

   - ✅ Fetch ALL relevant documentation pages
   - ✅ Check official docs, GitHub repos, and architecture guides
   - ✅ Verify claims across multiple sources
   - ❌ DO NOT make assumptions from limited information
   - ❌ DO NOT give confident answers based on incomplete research

2. **State your confidence level explicitly when making claims or drawing conclusions**

   - Use phrases like: "Based on the documentation I found..."
   - Admit gaps: "I couldn't find documentation about X, so..."
   - Distinguish facts from inferences: "The docs confirm X, but I'm inferring Y"

3. **When comparing technologies (A vs B):**

   - Research BOTH completely before comparing
   - Create feature parity matrices with verified facts
   - Note where information is missing or uncertain
   - Don't declare one "better" without complete information

4. **If you make an error:**

   - Acknowledge it immediately and completely
   - Explain what you missed in your research
   - Do deeper research to correct
   - Don't make the same mistake twice

5. **Red flags that indicate incomplete research:**
   - Making absolute statements ("X has NO capability Y")
   - Comparing features without checking both products thoroughly
   - Contradicting yourself after being challenged
   - Not finding obvious features (like eval capabilities in an observability platform)

**Example of good research response:**

```
"Let me thoroughly research both OpenLIT and Phoenix before comparing them.
I'll fetch: architecture docs, eval capabilities, telemetry features, and deployment options.
[After fetching 8-10 documentation pages]
Here's what I found with confidence levels..."
```

**Example of bad research response:**

```
"OpenLIT doesn't have eval capabilities" ← Wrong, based on incomplete research
"Phoenix is the best option" ← Premature conclusion without full comparison
```

## Project Context

This is an AI observability demo showcasing OpenTelemetry and OpenLIT instrumentation for GenAI workloads with:

- FastAPI web service (port 8080)
- OpenAI API integration (chat, embeddings)
- ChromaDB vector database
- Dual instrumentation: Manual OTel (spec-compliant) + Optional OpenLIT
- GenAI Semantic Conventions v1.37.0 compliance

See `README.md`, `GETTING_STARTED.md`, and `docs/` for full documentation.
Maintain complete understanding of the project structure, components, and code.

## Technology-Specific Research Checklists

When researching observability/AI monitoring tools, verify these components:

**For any observability platform:**

- [ ] Architecture (SDK vs Platform vs Both)
- [ ] Deployment model (SaaS, self-hosted, library-only)
- [ ] Telemetry capabilities (auto-instrumentation vs manual)
- [ ] Storage backend (where data goes)
- [ ] Semantic conventions used (OTel GenAI, OpenInference, custom)
- [ ] Evaluation capabilities (if applicable)
- [ ] Integration with existing backends (Grafana, Datadog, etc.)

**For OpenLIT specifically (since we use it):**

- [ ] OpenLIT SDK features and capabilities
- [ ] OpenLIT Platform features and capabilities
- [ ] OpenLIT Operator (Kubernetes) capabilities
- [ ] Evaluation methods (programmatic SDK vs automated Platform)
- [ ] `collect_metrics=True` flag for eval telemetry
- [ ] Distinction between operational instrumentation and evaluation

**For comparisons:**

- [ ] Create feature parity matrix
- [ ] Note architectural differences
- [ ] Identify integration compatibility with our stack
- [ ] Mark "verified" vs "inferred" for each claim
