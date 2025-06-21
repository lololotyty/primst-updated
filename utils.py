"""Utility functions for the bot"""
import math
import time
import asyncio
import gc
import os
import psutil
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

def humanbytes(size):
    """Convert bytes to human readable format"""
    if not size:
        return "0 B"
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"

def TimeFormatter(seconds: int) -> str:
    """Format seconds into human readable time"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0:
        time_parts.append(f"{seconds}s")
        
    return " ".join(time_parts) if time_parts else "0s"

class PerformanceOptimizer:
    """Performance optimization utilities for the Telegram bot."""
    
    def __init__(self):
        self.memory_threshold = 800  # MB
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    async def optimize_memory(self):
        """Force garbage collection and monitor memory usage."""
        try:
            # Force full garbage collection
            collected = gc.collect(generation=2)
            
            # Get current memory usage
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            logger.info(f"Memory cleanup: {collected} objects collected, Current usage: {memory_mb:.2f} MB")
            
            # Warn if memory usage is high
            if memory_mb > self.memory_threshold:
                logger.warning(f"High memory usage detected: {memory_mb:.2f} MB")
                
            return memory_mb
        except Exception as e:
            logger.error(f"Error in memory optimization: {e}")
            return 0
    
    async def periodic_cleanup(self):
        """Run periodic cleanup tasks."""
        while True:
            try:
                current_time = time.time()
                if current_time - self.last_cleanup >= self.cleanup_interval:
                    await self.optimize_memory()
                    self.last_cleanup = current_time
                    
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(30)
    
    @staticmethod
    async def with_timeout(coro, timeout: float = 300, default=None):
        """Execute coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Operation timed out after {timeout} seconds")
            return default
        except Exception as e:
            logger.error(f"Error in timed operation: {e}")
            return default
    
    @staticmethod
    async def retry_operation(operation: Callable, max_retries: int = 3, delay: float = 1.0):
        """Retry an operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Operation failed after {max_retries} attempts: {e}")
                    raise
                
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except (OSError, FileNotFoundError):
        return 0.0

def is_file_too_large(file_path: str, max_size_mb: float = 2048) -> bool:
    """Check if file is too large (default 2GB)."""
    return get_file_size_mb(file_path) > max_size_mb

async def cleanup_temp_files(directory: str = "/tmp", max_age_hours: int = 24):
    """Clean up temporary files older than specified age."""
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old temp file: {filename}")
                    except OSError as e:
                        logger.warning(f"Could not remove temp file {filename}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")

def get_system_info() -> dict:
    """Get system information for monitoring."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "memory_usage_mb": memory_info.rss / (1024 * 1024),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {}

async def monitor_performance():
    """Monitor bot performance and log metrics."""
    while True:
        try:
            system_info = get_system_info()
            logger.info(f"Performance metrics: {system_info}")
            
            # Log warning if memory usage is high
            if system_info.get("memory_usage_mb", 0) > 800:
                logger.warning("High memory usage detected!")
            
            await asyncio.sleep(300)  # Log every 5 minutes
        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}")
            await asyncio.sleep(600)  # Wait longer on error
