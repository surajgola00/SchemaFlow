# SchemaFlow — Engineering Audit & Upgrade Log

This document details the complete file-by-file audit, structural weaknesses resolved, security hardening, and test verification completed for **Code Cubicle 6.0 — Problem Statement 01: AI-Powered Data Intelligence Platform**.

---

## 1. Initial State vs. Upgraded Production State

| Component / Subsystem | Initial Vulnerability / Limitation | Upgraded Hardened Implementation |
|---|---|---|
| **Compilation Engine** | Fixed 3 hardcoded schemas with static 5-step DAG. Not truly dynamic. | Dynamic LLM-driven planner (`WorkflowPlanner`) with Pydantic v2 schema generation, source strategy selection, cycle rejection via Kahn's topological sort, and re-prompt self-correction. |
| **LLM Integration** | Mock-only fallback; OpenAI-compatible client broke when custom endpoints had trailing slashes or differing completion schemas. | Google Gemini native integration via OpenAI-compatible endpoint with automatic pre-validation normalization for dict assumptions and connector arrays. Live vs. Mock status banner in UI. |
| **Evidence & Grounding** | Claimed "zero hallucination" but stored unverified snippets without character offsets or quote validation. | **Evidence-Verified Extraction**: character span offset checking (`[start, end]`), verbatim quote verification, numeric/token containment check, and fail-safe nulling/rejection of ungrounded attributes. |
| **Crawler & Ingestion** | No robots.txt respect, no SSRF protection, vulnerable to private IP redirection and denial-of-service via huge payloads. | Strict SSRF defense with pre-flight DNS & redirect-hop validation (RFC 1918, loopback, cloud metadata `169.254.169.254`), per-domain token bucket rate limiting, robots.txt caching, 5MB response size caps, and quarantine delimiters for prompt injection defense. |
| **Pipeline DAG Engine** | Linear fake loop. Could not pause, resume, cancel, isolate node failures, or run parallel nodes. | Asyncio DAG engine executing nodes in topological order with concurrent wave execution, failure isolation (independent parallel branches continue; dependents skipped), budget stops, and clean pause/resume/cancel mechanics. |
| **Deduplication & Quality** | Basic string deduplication only. | 3-tier deduplication: exact unique key, canonical URL normalization (tracking query params and anchors stripped), and RapidFuzz token set ratio matching ($\ge 88\%$). |
| **Task Management** | Monitor-only SSE. | Full lifecycle control: Pause, Resume, Cancel, Retry-Failed, and recurring scheduling via APScheduler rehydrated at startup. |
| **Data Explorer & UI** | Basic HTML table without column filtering or feedback loop. | TanStack Table v8 with per-column typed filters, global search, column visibility toggle, evidence score slider, verified-only toggle, 4 export formats (CSV, JSON, XLSX, Report), and user feedback persisted to exclude false positives. |
| **Dataset Versioning** | History list without run-to-run diffing or schema evolution tracking. | Dataset version timeline with full added/removed/changed run-to-run diff view and schema hash change detection. |
| **Automated Testing** | 0 automated tests. | 50 passing unit and integration tests spanning DAG execution, SSRF, robots.txt, rate limits, verifier, normalizers, and API lifecycle. |

---

## 2. File-by-File Changes & Responsibilities

### Backend

- **`backend/app/main.py`**
  - Configures CORS origins for both `localhost:5173` and `127.0.0.1:5173`.
  - Application lifespan initializes SQLite tables, rehydrates APScheduler jobs from the database, preloads offline replay fixtures, and initializes logging.
  - Global exception handler catching unhandled exceptions and returning standard structured JSON responses (`{"detail": "...", "error_type": "..."}`).

- **`backend/app/config.py`**
  - Pydantic `BaseSettings` reading environment variables with fallback defaults.
  - Masks sensitive API keys in debug string outputs.
  - Provides configuration for `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `DATABASE_URL`, and rate limits.

- **`backend/app/services/llm/client.py`**
  - Dual-mode client supporting Google Gemini and deterministic offline fallback.
  - Sanitizes prompts against prompt injection: encapsulates web text in `<source_document>` tags with strict system instructions.
  - Pre-validation schema normalizer handling edge cases (dict-shaped assumptions, string risk notes, missing connectors) before Pydantic parsing.

- **`backend/app/services/compiler/planner.py`**
  - Prompts LLM for complete `WorkflowSpec` containing `entity_type`, `fields`, `source_strategy`, `limits`, `dag`, `assumptions`, `risk_notes`, and `clarifying_questions`.
  - Validates DAG acyclicity using Kahn's algorithm; re-prompts the LLM if cyclic dependencies or malformed schema structures are detected.

- **`backend/app/services/crawler/fetcher.py`**
  - Enforces SSRF defense (`is_safe_url`) on initial request and every subsequent redirect URL.
  - Respects domain `robots.txt` via `RobotsCache`; surfaces disallow reasons as compliance events rather than bypassing security.
  - Enforces per-domain rate limiting via `DomainRateLimiter`.
  - Caps response payloads to 5 MB to prevent memory exhaustion attacks.

- **`backend/app/services/extraction/verifier.py`**
  - Implements **Evidence-Verified Extraction**.
  - Verifies exact substring match of quote in crawled document; calculates character start/end offsets.
  - Checks value containment within evidence quote (verbatim, numeric equivalence, or fuzzy match $\ge 85\%$).
  - Discards candidate records if required fields lack evidence; nulls out ungrounded optional fields.

- **`backend/app/services/quality/dedupe.py`**
  - Three-tier deduplication engine:
    1. Exact composite key deduplication.
    2. Canonical URL deduplication (strips tracking parameters, trailing slashes, fragments).
    3. RapidFuzz token sort and token set ratio comparison.

- **`backend/app/services/executor/engine.py`**
  - Asynchronous topological DAG execution engine (`DagEngine`).
  - Executes independent nodes in parallel waves.
  - Isolates node failures so non-dependent downstream branches continue.
  - Responds immediately to pause, resume, and cancel signals.

- **`backend/app/services/connectors/web_search.py`**
  - Primary search integration with DuckDuckGo HTML parser.
  - Graceful fallback: when HTML search is rate-limited or blocked, seamlessly falls back to RSS, HackerNews, Wikipedia, arXiv, and GitHub connectors and logs compliance event `web_search_fallback`.

- **`backend/app/routers/exports.py`**
  - Generates CSV, JSON, multi-tab Excel (`.xlsx`), and executive HTML reports.
  - Queries `RecordFeedback` table and strictly excludes records flagged as `"wrong"` by users.

### Frontend

- **`frontend/src/components/ReactFlowDag.tsx`**
  - Custom React Flow component rendering interactive directed acyclic graphs.
  - Supports node status coloring (Pending, Running, Succeeded, Failed, Skipped) and live item count stream (`in: X -> out: Y`).
  - Supports zoom, pan, and responsive auto-centering.

- **`frontend/src/components/Studio.tsx`**
  - Prompt Studio with 5 pre-configured demo presets.
  - Real-time compiler feedback displaying Entity Type, Source Strategy, Assumptions, Compliance & Exclusions (Risk Notes), and Clarifying Questions.
  - Interactive Schema Editor and Execution Limits sliders.
  - Embedded read-only `ReactFlowDag` preview.

- **`frontend/src/components/ExecutionView.tsx`**
  - Real-time SSE execution monitor with live progress and counters.
  - Full pipeline controls: Pause, Resume, Cancel, Retry-Failed, Save as Demo Fixture.
  - Three interactive sub-tabs: Live Pipeline DAG, Structured Terminal Logs, and Sources Panel (Used & Blocked with exact reasons).

- **`frontend/src/components/DataGrid.tsx`**
  - TanStack Table v8 data explorer with global fuzzy search.
  - Per-column typed filters and column visibility toggle menu.
  - Evidence Score threshold slider and Verified-Only filter.
  - Direct inline feedback buttons (`ThumbsUp` / `ThumbsDown`) to flag wrong records and trigger backend exclusion from exports.
  - Four export formats: CSV, JSON (with provenance), XLSX (with quality sheet), and HTML Report.

- **`frontend/src/components/ProvenanceDrawer.tsx`**
  - Slide-out drawer displaying exact source quote grounding, character offsets, source URLs, and audit trail for any selected record.

- **`frontend/src/components/History.tsx`**
  - Workflows & Runs browser with workflow cloning and dataset re-inspection.
  - Recurring schedule creation modal with cron presets (`0 */6 * * *`, `0 9 * * *`, `0 9 * * 1`).
  - Managed Datasets view with version timeline (v1, v2, v3...) and run-to-run diff view (+Added, -Removed, ~Changed, Schema Hash Changes).

---

## 3. Test Verification Summary

All 50 unit and integration tests execute successfully without failures:

```
tests/test_api.py::test_full_pipeline_api_lifecycle PASSED
tests/test_api.py::test_run_controls_pause_resume_cancel_retry PASSED
tests/test_compiler.py::test_compile_startup_prompt PASSED
tests/test_compiler.py::test_compile_jobs_prompt PASSED
tests/test_compiler.py::test_validator_detects_cycles PASSED
tests/test_dag_engine.py::test_topological_order PASSED
tests/test_dag_engine.py::test_parallel_nodes PASSED
tests/test_dag_engine.py::test_failure_isolation PASSED
tests/test_dag_engine.py::test_cancellation PASSED
tests/test_dag_engine.py::test_pause_resume_halting PASSED
tests/test_dag_engine.py::test_budget_stop PASSED
tests/test_dedupe.py::TestDedupe::test_build_dedupe_key PASSED
tests/test_dedupe.py::TestDedupe::test_exact_key_dedupe PASSED
tests/test_dedupe.py::TestDedupe::test_canonical_url_dedupe PASSED
tests/test_dedupe.py::TestDedupe::test_fuzzy_dedupe PASSED
tests/test_error_handling.py::test_deliberately_wrong_llm_key_error_handling PASSED
tests/test_fetcher.py::test_robots_disallow_respected PASSED
tests/test_fetcher.py::test_per_domain_rate_limit PASSED
tests/test_fetcher.py::test_ssrf_redirect_to_private_blocked PASSED
tests/test_fetcher.py::test_response_size_cap PASSED
tests/test_fetcher.py::test_login_wall_and_rate_limit_marked_blocked PASSED
tests/test_normalizers.py::TestNormalizers::test_normalize_whitespace PASSED
tests/test_normalizers.py::TestNormalizers::test_normalize_url PASSED
tests/test_normalizers.py::TestNormalizers::test_parse_currency_indian_units PASSED
tests/test_normalizers.py::TestNormalizers::test_parse_currency_global_units PASSED
tests/test_normalizers.py::TestNormalizers::test_normalize_date PASSED
tests/test_normalizers.py::TestNormalizers::test_apply_normalizers PASSED
tests/test_planner.py::test_invalid_spec_reprompt_recovery PASSED
tests/test_planner.py::test_cyclic_dag_rejected_by_validator PASSED
tests/test_planner.py::test_cyclic_dag_rejected_by_compiler_service PASSED
tests/test_ssrf.py::TestSSRF::test_blocks_localhost PASSED
tests/test_ssrf.py::TestSSRF::test_blocks_loopback_ip PASSED
tests/test_ssrf.py::TestSSRF::test_blocks_aws_metadata PASSED
tests/test_ssrf.py::TestSSRF::test_blocks_file_scheme PASSED
tests/test_ssrf.py::TestSSRF::test_allows_public_urls PASSED
tests/test_validators.py::TestValidators::test_validate_url PASSED
tests/test_validators.py::TestValidators::test_validate_email PASSED
tests/test_validators.py::TestValidators::test_validate_min_len PASSED
tests/test_validators.py::TestValidators::test_validate_range PASSED
tests/test_validators.py::TestValidators::test_validate_enum PASSED
tests/test_validators.py::TestValidators::test_run_validators_chain PASSED
tests/test_verifier.py::TestVerifierExactMatch::test_exact_match_present PASSED
tests/test_verifier.py::TestVerifierExactMatch::test_evidence_not_in_chunk PASSED
tests/test_verifier.py::TestVerifierExactMatch::test_value_not_in_evidence_is_nulled PASSED
tests/test_verifier.py::TestVerifierExactMatch::test_required_field_missing_rejects_record PASSED
tests/test_verifier.py::TestVerifierFuzzyMatch::test_fuzzy_match_high_similarity PASSED
tests/test_verifier.py::TestVerifierFuzzyMatch::test_completely_fabricated_evidence_rejected PASSED
tests/test_verifier.py::TestVerifierMultipleFields::test_partial_verification_status PASSED
tests/test_verifier.py::TestVerifierMultipleFields::test_confidence_weighted_by_required PASSED
tests/test_verifier.py::TestVerifierMultipleFields::test_offset_tracking PASSED
======================= 50 passed, 1 warning in 12.24s ========================
```

Frontend compilation test:
```
npx tsc --noEmit -> exited 0 (Zero TypeScript errors)
```
