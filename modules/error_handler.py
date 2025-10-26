"""
Centralized error handling and logging
"""
import traceback
import sys

def format_error(error: Exception, context: str = "") -> str:
    """
    Format error with context for user-friendly display.
    
    Args:
        error: The exception object
        context: Additional context (e.g., "token creation", "profit collection")
    
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Common Solana errors
    if "insufficient funds" in error_msg.lower():
        return f"[ERROR] Insufficient SOL balance\n\nContext: {context}\nDetails: Not enough SOL to cover transaction + fees"
    
    elif "blockhash not found" in error_msg.lower():
        return f"[ERROR] Transaction expired\n\nContext: {context}\nDetails: Blockhash expired, transaction was too slow"
    
    elif "rate limit" in error_msg.lower() or "429" in error_msg:
        return f"[ERROR] RPC rate limit exceeded\n\nContext: {context}\nDetails: Too many requests, wait 30 seconds"
    
    elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
        return f"[ERROR] Network connection issue\n\nContext: {context}\nDetails: {error_msg[:100]}"
    
    elif "invalid" in error_msg.lower() and "address" in error_msg.lower():
        return f"[ERROR] Invalid wallet address\n\nContext: {context}\nDetails: Check address format"
    
    elif "signature verification failed" in error_msg.lower():
        return f"[ERROR] Transaction signing failed\n\nContext: {context}\nDetails: Wallet key issue"
    
    # HTTP/API errors
    elif error_type == "HTTPStatusError" or "403" in error_msg:
        return f"[ERROR] API access denied\n\nContext: {context}\nDetails: Check API key or permissions"
    
    elif "404" in error_msg:
        return f"[ERROR] Resource not found\n\nContext: {context}\nDetails: Token or account not found"
    
    # General errors
    else:
        # Truncate long error messages
        short_msg = error_msg[:150] if len(error_msg) > 150 else error_msg
        return f"[ERROR] {error_type}\n\nContext: {context}\nDetails: {short_msg}"

def log_error(error: Exception, context: str = "", print_trace: bool = True):
    """
    Log error to console with full traceback.
    
    Args:
        error: The exception object
        context: Additional context
        print_trace: Whether to print full traceback
    """
    print(f"\n{'='*60}")
    print(f"[ERROR] {context}")
    print(f"{'='*60}")
    print(f"Type: {type(error).__name__}")
    print(f"Message: {error}")
    
    if print_trace:
        print(f"\nFull Traceback:")
        traceback.print_exc()
    
    print(f"{'='*60}\n")

def safe_async_run(coro, error_context: str = "async operation"):
    """
    Safely run async coroutine with error handling.
    
    Args:
        coro: Coroutine to run
        error_context: Context for error messages
    
    Returns:
        Result or None on error
    """
    import asyncio
    
    try:
        return asyncio.run(coro)
    except Exception as e:
        log_error(e, error_context)
        return None

def handle_telegram_error(func):
    """
    Decorator for Telegram handlers to catch and format errors.
    
    Usage:
        @handle_telegram_error
        def my_handler(message):
            # ... handler code
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log to console
            log_error(e, f"Telegram handler: {func.__name__}")
            
            # Try to send error to user
            try:
                message = args[0]  # First arg is usually message
                if hasattr(message, 'chat'):
                    from telebot import TeleBot
                    from config import TELEGRAM_TOKEN
                    bot = TeleBot(TELEGRAM_TOKEN)
                    
                    error_msg = format_error(e, func.__name__)
                    bot.reply_to(message, error_msg)
            except:
                pass  # Silently fail if can't send to user
    
    return wrapper

class ErrorCategory:
    """Error categories for better handling"""
    NETWORK = "network"
    RPC = "rpc"
    WALLET = "wallet"
    TRANSACTION = "transaction"
    API = "api"
    VALIDATION = "validation"
    UNKNOWN = "unknown"

def categorize_error(error: Exception) -> str:
    """
    Categorize error for better handling.
    
    Args:
        error: The exception object
    
    Returns:
        Error category
    """
    error_msg = str(error).lower()
    error_type = type(error).__name__
    
    if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
        return ErrorCategory.NETWORK
    
    elif "rpc" in error_msg or "rate limit" in error_msg:
        return ErrorCategory.RPC
    
    elif "insufficient funds" in error_msg or "signature" in error_msg:
        return ErrorCategory.WALLET
    
    elif "transaction" in error_msg or "blockhash" in error_msg:
        return ErrorCategory.TRANSACTION
    
    elif "403" in error_msg or "401" in error_msg or "api" in error_msg:
        return ErrorCategory.API
    
    elif "invalid" in error_msg or "validation" in error_msg:
        return ErrorCategory.VALIDATION
    
    else:
        return ErrorCategory.UNKNOWN

