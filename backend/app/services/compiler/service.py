"""
CompilerService — orchestrates planner + validator to produce a validated WorkflowSpec.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.schemas.workflow import WorkflowSpec
from app.services.compiler.planner import WorkflowPlanner
from app.services.compiler.validator import SpecValidator
from app.services.llm.factory import AnyLLMClient
from app.logging_config import get_logger

log = get_logger(__name__)


class CompilerService:
    def __init__(self, llm: AnyLLMClient) -> None:
        self._planner = WorkflowPlanner(llm)
        self._validator = SpecValidator()

    async def compile(self, prompt: str) -> WorkflowSpec:
        """
        Compile a natural-language prompt into a validated WorkflowSpec.
        1. Call planner → spec
        2. Validate → errors
        3. If errors: retry planner once with errors in prompt
        4. Clamp limits
        5. Return spec or raise HTTP 422
        """
        log.info(f"Compiling workflow for prompt: {prompt[:80]}...")

        # First attempt
        spec = await self._planner.plan(prompt)
        errors = self._validator.validate(spec)

        if errors:
            log.info(f"First compile attempt had {len(errors)} errors; retrying...")
            error_text = "\n".join(f"- {e}" for e in errors)
            retry_prompt = (
                f"{prompt}\n\n"
                f"IMPORTANT: The previous response had validation errors:\n{error_text}\n"
                f"Please fix these issues and try again."
            )
            spec = await self._planner.plan(retry_prompt)
            errors = self._validator.validate(spec)

            if errors:
                log.error(f"Compile failed after retry: {errors}")
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Failed to generate a valid workflow specification",
                        "errors": errors,
                    },
                )

        spec = self._validator.clamp_limits(spec)
        log.info(f"Workflow compiled: {spec.title} ({len(spec.fields)} fields, {len(spec.dag)} DAG nodes)")
        return spec
