"""Test execution engine for running prompts across models."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from .config import PromptConfig, TestCase, render_prompt
from .models import TestResult
from .matching import check_match


class PromptRunner:
    """Executes prompt tests across multiple models."""
    
    def __init__(self, max_concurrent: int = 10, timeout: int = 30):
        """Initialize the runner with concurrency and timeout settings."""
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_all(
        self,
        config: PromptConfig,
        models: List[str]
    ) -> List[TestResult]:
        """Run all test cases across all models."""
        tasks = []
        
        for model in models:
            for idx, test_case in enumerate(config.test_cases):
                task = self._run_single_test(config, model, idx, test_case)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        task_idx = 0
        
        for model in models:
            for idx, test_case in enumerate(config.test_cases):
                result = results[task_idx]
                task_idx += 1
                
                if isinstance(result, Exception):
                    result = TestResult(
                        test_case_idx=idx,
                        model=model,
                        inputs=test_case.inputs,
                        expected=test_case.expected,
                        error=str(result)
                    )
                
                final_results.append(result)
        
        return final_results
    
    async def _run_single_test(
        self,
        config: PromptConfig,
        model: str,
        test_case_idx: int,
        test_case: TestCase
    ) -> TestResult:
        """Run a single test case against a model."""
        async with self.semaphore:
            start_time = time.time()
            
            try:
                # Render the prompt with variables
                rendered_prompt = render_prompt(config.prompt, test_case.inputs)
                
                # Prepare messages
                messages = []
                if config.system:
                    messages.append({"role": "system", "content": config.system})
                messages.append({"role": "user", "content": rendered_prompt})
                
                # Merge global parameters with per-test overrides
                api_params = {}
                api_params.update(config.parameters)
                if test_case.parameters:
                    api_params.update(test_case.parameters)
                
                # Lazy import litellm (heavy dependency, ~100MB import chain)
                from litellm import acompletion as _acompletion
                
                # Make API call with timeout and parameters
                response = await asyncio.wait_for(
                    _acompletion(
                        model=model,
                        messages=messages,
                        timeout=self.timeout,
                        **api_params
                    ),
                    timeout=self.timeout + 5  # Give a bit of extra buffer
                )
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                # Extract response content
                response_content = response.choices[0].message.content
                
                # Extract usage information
                usage = response.usage
                tokens_in = usage.prompt_tokens if usage else None
                tokens_out = usage.completion_tokens if usage else None
                
                # Calculate cost (litellm should provide this)
                cost = None
                try:
                    import litellm as _litellm
                    cost = _litellm.completion_cost(response)
                except Exception:
                    # Cost calculation may fail for some models
                    pass
                
                # Determine match mode: test-specific, then config-specific, then default
                match_mode = test_case.match or config.match
                
                # Evaluate match (wrap in thread for semantic mode to avoid blocking)
                if match_mode == "semantic":
                    match_result = await asyncio.to_thread(
                        check_match, response_content, test_case.expected, match_mode, model
                    )
                else:
                    match_result = check_match(
                        response_content, test_case.expected, match_mode, None
                    )
                
                return TestResult(
                    test_case_idx=test_case_idx,
                    model=model,
                    inputs=test_case.inputs,
                    expected=test_case.expected,
                    response=response_content,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    latency_ms=latency_ms,
                    match_result=match_result
                )
                
            except asyncio.TimeoutError:
                return TestResult(
                    test_case_idx=test_case_idx,
                    model=model,
                    inputs=test_case.inputs,
                    expected=test_case.expected,
                    error="Timeout"
                )
            except Exception as e:
                # Better API key error messages
                error_msg = self._format_api_error(e, model)
                return TestResult(
                    test_case_idx=test_case_idx,
                    model=model,
                    inputs=test_case.inputs,
                    expected=test_case.expected,
                    error=error_msg
                )
    
    def _format_api_error(self, error: Exception, model: str) -> str:
        """Format API errors with helpful environment variable hints."""
        error_str = str(error).lower()
        
        # Check for authentication errors
        if "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
            if model.startswith("gpt-") or model.startswith("openai/"):
                return f"Authentication failed: Set OPENAI_API_KEY environment variable. Original error: {error}"
            elif model.startswith("claude-") or model.startswith("anthropic/"):
                return f"Authentication failed: Set ANTHROPIC_API_KEY environment variable. Original error: {error}"
            elif model.startswith("gemini") or model.startswith("google/"):
                return f"Authentication failed: Set GOOGLE_API_KEY environment variable. Original error: {error}"
            elif model.startswith("command") or model.startswith("cohere/"):
                return f"Authentication failed: Set COHERE_API_KEY environment variable. Original error: {error}"
            else:
                return f"Authentication failed: Check your API key for model {model}. Original error: {error}"
        
        return f"{type(error).__name__}: {str(error)}"