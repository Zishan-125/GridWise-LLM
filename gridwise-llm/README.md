# GridWise LLM — BUP CSE Fest 2026

Competition-oriented implementation of the **BUP CSE Fest 2026 Smart Campus Energy Optimization Challenge — GridWise LLM**.

The implementation follows the canonical Problem Statement for challenge behavior and the Participant Guide & Evaluation Rubric for deployment, scoring, reliability, Docker, and reproducibility. The supplied public cases are retained only as validation fixtures; no case ID, note phrase, or reference schedule is used as runtime logic.

## Architecture

```text
Operator Notes
     |
     v
Language-capable LLM (structured JSON)
     |
     v
Deterministic Guardrails / Normalization
     |
     v
Validated Directives
     |
     +--> effective solar / reserves / window constraints
     |
     v
24-hour Linear Program (SciPy HiGHS)
     |
     v
24-hour Schedule
     |
     v
Independent Replay Validator
     |
     v
Recalculated Totals
     |
     v
Exact JSON API Response
```

### LLM role

The LLM is directly on the **operator-note interpretation path**. It receives the notes, the supported directive vocabulary, time-window rules, and the current 24-hour context. It must return one structured interpretation per note. The numerical optimizer never asks the LLM to choose energy actions.

The default production adapter is an OpenAI-compatible Chat Completions endpoint with deterministic temperature and JSON-schema output. `LLM_BASE_URL` permits compatible providers.

A missing/unavailable LLM is a controlled service failure; the service does **not** pretend that a note was interpreted successfully.

### Supported directives

- `solar_reduction`: `{"hours":[...],"factor": number}`
- `minimum_battery_reserve`: `{"hours":[...],"minimum_energy_kwh": number}`
- `no_charge_window`: `{"hours":[...]}`
- `no_discharge_window`: `{"hours":[...]}`
- `max_grid_window`: `{"hours":[...],"max_grid_kwh": number}`
- `no_op`: `null`

Whole-hour windows are start-inclusive/end-exclusive. For example, 1 PM–3 PM is `[13,14]`. For solar reduction, the factor is the fraction remaining: an 80% reduction is `0.2`.

## Optimizer formulation

For each hour, the LP uses:

- `grid[h] >= 0`
- `solar_used[h] >= 0`
- one **signed battery flow** variable `flow[h]` (`>0` charge, `<0` discharge)
- `energy_after[h]`

The signed flow is deliberate: it makes simultaneous charge/discharge impossible without adding binary variables.

Energy balance:

```text
grid[h] + solar_used[h] - flow[h] = demand[h]
```

Battery transition:

```text
energy_after[h] = energy_before[h] + flow[h]
```

with the initial energy used for hour 0 and:

```text
reserve[h] <= energy_after[h] <= capacity
```

Charge/discharge rate bounds, no-charge/no-discharge windows, effective solar, and grid caps become LP bounds. End-of-day neutrality is:

```text
energy_after[23] = initial_energy
```

Objective:

```text
minimize sum(grid[h] * tariff[h])
```

The solver is SciPy `linprog(method="highs")`.

## API

### `GET /health`

Returns exactly:

```json
{"status":"ok"}
```

### `POST /optimize-energy`

Request:

```json
{
  "scenario_id": "GRID-101",
  "operator_notes": [
    "Solar output will drop to about 20% from 1 PM to 3 PM.",
    "Do not charge the battery between 2 PM and 4 PM."
  ],
  "hours": [
    {"hour": 0, "demand_kwh": 180, "solar_kwh": 0, "tariff_bdt_per_kwh": 7}
  ],
  "battery": {
    "capacity_kwh": 500,
    "initial_energy_kwh": 200,
    "minimum_energy_kwh": 50,
    "max_charge_kwh_per_hour": 100,
    "max_discharge_kwh_per_hour": 100
  }
}
```

The `hours` array must contain exactly 24 entries for hours `0..23`.

Response top-level fields are exactly:

```text
scenario_id
directive_interpretation
hourly_plan
total_grid_kwh
total_cost_bdt
peak_grid_kwh
plan_summary
```

Each `hourly_plan` entry contains:

```text
hour
grid_kwh
solar_used_kwh
battery_action
battery_kwh
battery_energy_after_kwh
```

`battery_action` is exactly `charge`, `discharge`, or `idle`.

## Deterministic guardrails

The guardrail layer treats LLM output as untrusted and rejects:

- malformed or missing note mappings
- duplicate/out-of-range note indices
- unsupported directive types
- malformed adjustment objects
- duplicate/unsorted/out-of-range hours
- non-finite numeric values
- solar factors outside `[0,1]`
- invalid reserves
- negative grid caps
- incorrect `applies`/`no_op` semantics

Valid hour arrays are normalized to unique ascending integers. The optimizer is called only after guardrails succeed.

## Independent replay

The returned schedule is independently replayed from hour 0 through 23. Replay checks energy balance, effective solar, battery transitions and bounds, action consistency, rates, all directives, grid caps, final neutrality, and recomputes totals.

The service never trusts solver-reported totals; totals are recalculated from the final serialized hourly plan.

## Environment

Copy `.env.example` to `.env` and set:

```text
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=8
LLM_MAX_RETRIES=1
PORT=8000
LOG_LEVEL=INFO
```

Do not commit `.env` or credentials.

## Local quickstart

Python 3.11+:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and provide the LLM credentials/provider
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl -fsS http://localhost:8000/health
```

Example optimization request:

```bash
curl -sS -X POST http://localhost:8000/optimize-energy \
  -H 'Content-Type: application/json' \
  --data @example-request.json
```

For a complete generic input, use `example-request.json` as the POST body. A successful response has exactly the fields below:
```json
{
  "scenario_id": "EXAMPLE-001",
  "directive_interpretation": [
    {
      "note_index": 0,
      "applies": false,
      "directive_type": "no_op",
      "structured_adjustment": null,
      "explanation": "The note does not affect the current energy schedule."
    }
  ],
  "hourly_plan": [
    {
      "hour": 0,
      "grid_kwh": 10.0,
      "solar_used_kwh": 0.0,
      "battery_action": "idle",
      "battery_kwh": 0.0,
      "battery_energy_after_kwh": 20.0
    }
  ],
  "total_grid_kwh": 240.0,
  "total_cost_bdt": 1200.0,
  "peak_grid_kwh": 10.0,
  "plan_summary": "Optimized grid cost using available solar and battery flexibility while enforcing all validated operator directives."
}
```
The actual response contains all 24 hourly plan entries; the abbreviated block above shows the exact field shapes and a valid first-hour entry.

## Public-sample validation

The public sample pack is copied unchanged to `data/public_samples.json` for reproducibility.

With the service running and a real LLM configured:

```bash
python scripts/test_public_samples.py
```

The script posts every public input and checks basic response shape. The test suite also contains optimizer/replay tests that do not require an LLM.

For an offline optimization regression against the public reference semantics, the expected directive interpretations can be used as test fixtures; they are **not** runtime logic.

## Testing

```bash
pytest -q
```

Tests cover API health/schema behavior, guardrails, prompts, optimization/replay, edge cases, and randomized feasible scenarios.

## Benchmarking

With the service running:

```bash
python scripts/benchmark.py
```

The benchmark reports p50, p95, p99, max latency, and failures over repeated requests. Actual latency depends heavily on the selected model/provider and network.

The challenge target is p95 <= 5 seconds, with a 30-second per-request timeout.

## Docker

Build:

```bash
docker build -t gridwise-llm:latest .
```

Run:

```bash
docker run --rm -p 8000:8000 --env-file .env gridwise-llm:latest
```

Then:

```bash
curl -fsS http://localhost:8000/health
```

Compose:

```bash
docker compose up --build
```

No secret is copied into the image; `.env` is excluded by `.dockerignore`.

## Error behavior

- `200`: successful health or optimization
- `400/422`: request validation failure (FastAPI/Pydantic)
- `503`: LLM provider unavailable
- `422`: optimization infeasible
- `500`: controlled internal optimization/replay failure

Production responses do not expose stack traces, provider credentials, API keys, or raw secret values.

## Known limitations / risks

1. Semantic interpretation quality depends on the selected language model. The prompt and strict post-validation reduce, but cannot eliminate, model errors.
2. A production submission must provide a reachable LLM provider/model with adequate latency and quota.
3. The official hidden judge remains the source of truth for hidden language distributions and any stricter numerical checks.
4. Overlapping `solar_reduction` directives are composed multiplicatively. Organizer scoring scenarios are documented as feasible and should not require contradictory hard directives.
5. SciPy/HiGHS is deterministic for a fixed input and library/runtime environment, but equivalent optimal LP solutions can have different action sequences.

## Dependencies

FastAPI, Uvicorn, Pydantic, pydantic-settings, HTTPX, NumPy, SciPy, pytest, pytest-asyncio.

## Attribution

Uses open-source Python ecosystem libraries listed above. The optimization engine is SciPy `linprog` with HiGHS. The challenge specification is the supplied BUP CSE Fest 2026 document pack.

## Final compliance audit

- [x] `/health` and `/optimize-energy`
- [x] exact top-level response fields
- [x] 1–3 notes and exactly one ordered interpretation per note
- [x] six supported directive types only
- [x] deterministic LLM guardrails
- [x] effective solar / reserve / charge / discharge / grid-cap application
- [x] mathematical cost optimization
- [x] independent replay validation
- [x] totals recalculated from hourly plan
- [x] Docker and compose
- [x] environment-based secrets
- [x] public-sample fixture and runner
- [x] randomized tests
- [x] benchmark script
- [x] no public case lookup in runtime logic

Before submission, run the complete local test suite, public-sample runner, benchmark, Docker health check, and the final external reachability check from the judging environment.
