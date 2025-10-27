"""
Retry utilities for handling RPC failures and transaction errors
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Any, Optional
from settings import MAX_RETRIES, RETRY_DELAY

class RetryError(Exception):
    """Raised when all retries are exhausted."""
    pass

def retry_sync(max_attempts: int = MAX_RETRIES, delay: float = RETRY_DELAY, 
               backoff: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator for synchronous functions with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        print(f"[ERROR] {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise RetryError(f"Max retries ({max_attempts}) exceeded") from e
                    
                    print(f"[WARNING]  {func.__name__} attempt {attempt}/{max_attempts} failed: {e}")
                    print(f"   Retrying in {current_delay:.1f}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator

def retry_async(max_attempts: int = MAX_RETRIES, delay: float = RETRY_DELAY,
                backoff: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator for async functions with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        print(f"[ERROR] {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise RetryError(f"Max retries ({max_attempts}) exceeded") from e
                    
                    print(f"[WARNING]  {func.__name__} attempt {attempt}/{max_attempts} failed: {e}")
                    print(f"   Retrying in {current_delay:.1f}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator

class RetryableRPC:
    """Wrapper for RPC calls with automatic retry logic."""
    
    def __init__(self, client, max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
        self.client = client
        self.max_retries = max_retries
        self.delay = delay
    
    @retry_async(max_attempts=MAX_RETRIES, delay=RETRY_DELAY)
    async def get_balance(self, pubkey):
        """Get balance with retry."""
        return await self.client.get_balance(pubkey)
    
    @retry_async(max_attempts=MAX_RETRIES, delay=RETRY_DELAY)
    async def send_transaction(self, tx, *signers):
        """Send transaction with retry."""
        return await self.client.send_transaction(tx, *signers)
    
    @retry_async(max_attempts=MAX_RETRIES, delay=RETRY_DELAY)
    async def get_signature_statuses(self, signatures):
        """Get signature statuses with retry."""
        return await self.client.get_signature_statuses(signatures)
    
    @retry_async(max_attempts=MAX_RETRIES, delay=RETRY_DELAY)
    async def get_recent_blockhash(self):
        """Get recent blockhash with retry."""
        return await self.client.get_recent_blockhash()
    
    @retry_async(max_attempts=MAX_RETRIES, delay=RETRY_DELAY)
    async def confirm_transaction(self, signature, commitment="confirmed"):
        """Confirm transaction with retry."""
        return await self.client.confirm_transaction(signature, commitment)

def with_retry(func: Callable, *args, max_attempts: int = MAX_RETRIES, 
               delay: float = RETRY_DELAY, **kwargs) -> Any:
    """
    Execute a function with retry logic (non-decorator version).
    
    Usage:
        result = with_retry(risky_function, arg1, arg2, max_attempts=3)
    """
    current_delay = delay
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt == max_attempts:
                raise RetryError(f"Max retries ({max_attempts}) exceeded") from e
            
            print(f"[WARNING]  Attempt {attempt}/{max_attempts} failed: {e}")
            print(f"   Retrying in {current_delay:.1f}s...")
            time.sleep(current_delay)
            current_delay *= 1.5  # Exponential backoff
    
    raise last_exception

