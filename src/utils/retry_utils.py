#!/usr/bin/env python3
"""
Retry Utilities with Exponential Backoff.
Handles transient API failures with smart retry logic.
"""

import time
import random
from functools import wraps
from typing import Callable, Type, Tuple, Optional


def exponential_backoff_retry(
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 300.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_callback: Optional[Callable] = None
):
    """
    Decorator for exponential backoff retry.

    Delay calculation: min(base_delay * (exponential_base ^ attempt), max_delay)
    With jitter: delay * (0.5 + random.random()) to prevent thundering herd

    Example delays with base=2, exponential_base=2:
    - Attempt 1: ~2s (with jitter: 1-2s)
    - Attempt 2: ~4s (with jitter: 2-4s)
    - Attempt 3: ~8s (with jitter: 4-8s)
    - Attempt 4: ~16s (with jitter: 8-16s)
    - Attempt 5: ~32s (with jitter: 16-32s)

    Args:
        max_retries: Maximum number of retries (default: 5)
        base_delay: Initial delay in seconds (default: 2.0)
        max_delay: Maximum delay cap in seconds (default: 300.0)
        exponential_base: Base for exponential growth (default: 2.0)
        retryable_exceptions: Tuple of exception types to retry on
        log_callback: Optional function to call for logging (receives string message)

    Returns:
        Decorated function with retry logic

    Example:
        @exponential_backoff_retry(
            max_retries=3,
            base_delay=1.0,
            retryable_exceptions=(requests.exceptions.HTTPError,),
            log_callback=print
        )
        def fetch_data():
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    # Attempt the function call
                    return func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e

                    # If this was the last retry, raise the exception
                    if attempt == max_retries:
                        if log_callback:
                            log_callback(f"❌ Failed after {max_retries} retries: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter (randomness between 0.5x and 1.0x of delay)
                    jittered_delay = delay * (0.5 + random.random() * 0.5)

                    if log_callback:
                        log_callback(
                            f"⚠️  Attempt {attempt + 1}/{max_retries + 1} failed: {e}\n"
                            f"   Retrying in {jittered_delay:.1f}s..."
                        )

                    time.sleep(jittered_delay)

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 300.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_callback: Optional[Callable] = None,
    **kwargs
):
    """
    Functional version of exponential backoff retry (non-decorator).

    Use this when you need to apply retry logic without decorating a function.

    Args:
        func: Function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retries
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Tuple of exception types to retry on
        log_callback: Optional function for logging
        **kwargs: Keyword arguments for func

    Returns:
        Result of func(*args, **kwargs)

    Example:
        result = retry_with_backoff(
            fetch_data,
            url="https://api.example.com",
            max_retries=3,
            retryable_exceptions=(requests.exceptions.HTTPError,)
        )
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)

        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_retries:
                if log_callback:
                    log_callback(f"❌ Failed after {max_retries} retries: {e}")
                raise

            delay = min(
                base_delay * (2.0 ** attempt),
                max_delay
            )
            jittered_delay = delay * (0.5 + random.random() * 0.5)

            if log_callback:
                log_callback(
                    f"⚠️  Attempt {attempt + 1}/{max_retries + 1} failed: {e}\n"
                    f"   Retrying in {jittered_delay:.1f}s..."
                )

            time.sleep(jittered_delay)

    raise last_exception


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 2.0,
        max_delay: float = 300.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retries
            base_delay: Initial delay in seconds
            max_delay: Maximum delay cap in seconds
            exponential_base: Base for exponential growth
            jitter: Whether to add jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds (with jitter if enabled)
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


if __name__ == "__main__":
    # Test retry utilities
    import sys

    attempt_count = 0

    @exponential_backoff_retry(
        max_retries=3,
        base_delay=0.5,
        retryable_exceptions=(ValueError,),
        log_callback=print
    )
    def failing_function():
        """Simulates a function that fails the first 2 times"""
        global attempt_count
        attempt_count += 1

        print(f"\n→ Attempt {attempt_count}")

        if attempt_count < 3:
            raise ValueError(f"Simulated failure #{attempt_count}")

        return f"Success on attempt {attempt_count}!"

    print("=" * 70)
    print("Testing Exponential Backoff Retry")
    print("=" * 70)

    try:
        result = failing_function()
        print(f"\n✓ {result}")
    except Exception as e:
        print(f"\n✗ Final failure: {e}")

    # Test RetryConfig
    print("\n" + "=" * 70)
    print("Testing RetryConfig")
    print("=" * 70)

    config = RetryConfig(
        max_retries=5,
        base_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True
    )

    print("\nCalculated delays (with jitter):")
    for i in range(5):
        delay = config.calculate_delay(i)
        print(f"  Attempt {i+1}: {delay:.2f}s")

    # Test functional version
    print("\n" + "=" * 70)
    print("Testing Functional Retry")
    print("=" * 70)

    attempt_count = 0

    def another_failing_function():
        global attempt_count
        attempt_count += 1
        print(f"\n→ Attempt {attempt_count}")

        if attempt_count < 2:
            raise RuntimeError(f"Failure #{attempt_count}")

        return "Success!"

    try:
        result = retry_with_backoff(
            another_failing_function,
            max_retries=3,
            base_delay=0.3,
            retryable_exceptions=(RuntimeError,),
            log_callback=print
        )
        print(f"\n✓ {result}")
    except Exception as e:
        print(f"\n✗ Final failure: {e}")

    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)
