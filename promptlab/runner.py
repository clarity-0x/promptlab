"""Test execution engine for running prompts across models."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import litellm
from litellm import acompletion

from .config import PromptConfig, TestCase, render_prompt


class TestResult:
    """Result of running a single test case."""
    
    def __init__(
        self,
        test_case_idx: int,
        model: str,
        inputs: Dict[str, Any],
        expected: str,
        response: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        cost: Optional[float] = None,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.test_case_idx = test_case_idx
        self.model = model
        self.inputs = inputs
        self.expected = expected
        self.response = response
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost = cost
        self.latency_ms = latency_ms
        self.error = error
    
    @property
    def matches(self) -> Optional[bool]:
        """Check if response matches expected output."""
        if self.response is None or self.error:
            return None
        return self.response.strip().lower() == self.expected.strip().lower()


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
                
                # Make API call with timeout
                response = await asyncio.wait_for(
                    acompletion(
                        model=model,
                        messages=messages,
                        timeout=self.timeout
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
                    cost = litellm.completion_cost(response)
                except Exception:
                    # Cost calculation may fail for some models
                    pass
                
                return TestResult(
                    test_case_idx=test_case_idx,
                    model=model,
                    inputs=test_case.inputs,
                    expected=test_case.expected,
                    response=response_content,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    latency_ms=latency_ms
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
                return TestResult(
                    test_case_idx=test_case_idx,
                    model=model,
                    inputs=test_case.inputs,
                    expected=test_case.expected,
                    error=f"{type(e).__name__}: {str(e)}"
                )