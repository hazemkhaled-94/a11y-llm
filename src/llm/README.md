# llm package

Implementation package for all LLM-related behavior used by the accessibility smoke pipeline.

## Modules

- `config.py`: environment-backed LLM connection settings
- `connector.py`: async model invocation facade (`litellm`) with retries
- `models.py`: strict Pydantic request/response schemas
- `wcag_evaluator.py`: chunked WCAG evaluator orchestration and response normalization

## Runtime flow

1. `LLMConfigLoader` reads required environment variables.
2. `Connector` submits completion requests via `litellm.acompletion`.
3. `WCAGEvaluator` splits input elements into batches.
4. For each batch, prompts are built with JSON schema reinforcement.
5. Model output is parsed and validated against `WCAGEvaluationResult`.
6. Missing result IDs are reconciled with `MANUAL_REVIEW` placeholders.

## Required environment variables

- `AUDITOR_LLM_API_KEY`
- `AUDITOR_LLM_MODEL`
- `AUDITOR_LLM_URL`

These are consumed by `LLMConfigLoader.load_from_environment()`.

## Connector defaults (current implementation)

`Connector.generate_completion()` sends these defaults to the provider:

- `max_tokens=4096`
- `timeout=900`
- `temperature=0.2`
- `seed=200994`
- `extra_body.options.num_ctx=131072`

Retry behavior uses `tenacity`:

- up to 3 attempts
- exponential backoff, min 2s / max 10s

## Data contracts

Primary Pydantic models in `models.py`:

- `ExtractedElement`
- `WCAGEvaluationRequest`
- `ElementEvaluationResult`
- `WCAGEvaluationResult`

Allowed element statuses:

- `PASS`
- `FAIL`
- `NEEDS_CONTEXT`
- `MANUAL_REVIEW`

Top-level evaluation status:

- `SUCCESS`
- `ERROR`

## Response normalization behavior

`WCAGEvaluator` accepts multiple content shapes from model output:

- JSON object containing `results`
- JSON array (wrapped as `{"status": "SUCCESS", "results": [...]}`)
- single-result object with `element_id`, `status`, `reason` (wrapped into list)
- fenced JSON markdown blocks are unwrapped before parse
- list-of-text chunks are concatenated when provider returns typed text parts

Any non-parseable or schema-invalid output raises:

- `ValueError("LLM returned malformed or non-compliant JSON.")`

## Integration points

Used primarily by:

- `tests/base/wcag/base.py`

It is designed to remain transport/provider-agnostic behind the `CompletionClient` protocol.
