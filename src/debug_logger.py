"""
Moduł loggera debugowania dla CS2 Skin Analyzer.

Zapewnia centralny system logowania z różnymi poziomami,
timestampami i możliwością przekierowania do konsoli debugowania.
"""

import sys
import time
import threading
import traceback
from datetime import datetime
from typing import Callable, Optional, Any
from enum import Enum
from functools import wraps


class LogLevel(Enum):
    """Poziomy logowania."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    HTTP = 4      # Specjalny poziom dla requestów HTTP
    DB = 5        # Operacje na bazie danych
    PERF = 6      # Wydajność / timing


# Kolory dla poziomów (tagi do Text widget)
LOG_COLORS = {
    LogLevel.DEBUG: '#888888',    # Szary
    LogLevel.INFO: '#ffffff',     # Biały
    LogLevel.WARNING: '#ffaa00',  # Pomarańczowy
    LogLevel.ERROR: '#ff4444',    # Czerwony
    LogLevel.HTTP: '#44aaff',     # Niebieski
    LogLevel.DB: '#44ff88',       # Zielony
    LogLevel.PERF: '#ff44ff',     # Magenta
}

LOG_PREFIXES = {
    LogLevel.DEBUG: '[DEBUG]',
    LogLevel.INFO: '[INFO]',
    LogLevel.WARNING: '[WARN]',
    LogLevel.ERROR: '[ERROR]',
    LogLevel.HTTP: '[HTTP]',
    LogLevel.DB: '[DB]',
    LogLevel.PERF: '[PERF]',
}


class DebugLogger:
    """Singleton logger do debugowania aplikacji."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._enabled = False
        self._callbacks: list[Callable[[LogLevel, str, str], None]] = []
        self._log_history: list[tuple[LogLevel, str, str]] = []
        self._max_history = 10000
        self._start_time = time.time()
        self._lock = threading.Lock()
        
        # Statystyki
        self._stats = {
            'http_requests': 0,
            'http_errors': 0,
            'db_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        if value:
            self.info("Debug mode ENABLED")
        else:
            self.info("Debug mode DISABLED")
    
    def register_callback(self, callback: Callable[[LogLevel, str, str], None]):
        """Rejestruje callback wywoływany przy każdym logu."""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[LogLevel, str, str], None]):
        """Usuwa callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _format_timestamp(self) -> str:
        """Formatuje timestamp."""
        now = datetime.now()
        elapsed = time.time() - self._start_time
        return f"[{now.strftime('%H:%M:%S.%f')[:-3]}] (+{elapsed:.2f}s)"
    
    def _log(self, level: LogLevel, message: str, extra_data: Optional[dict] = None):
        """Główna metoda logowania."""
        if not self._enabled and level != LogLevel.ERROR:
            return
        
        timestamp = self._format_timestamp()
        prefix = LOG_PREFIXES.get(level, '[???]')
        
        # Dodaj extra data jeśli jest
        if extra_data:
            extra_str = ' | ' + ' | '.join(f"{k}={v}" for k, v in extra_data.items())
            full_message = f"{timestamp} {prefix} {message}{extra_str}"
        else:
            full_message = f"{timestamp} {prefix} {message}"
        
        # Zapisz do historii
        with self._lock:
            self._log_history.append((level, timestamp, message))
            if len(self._log_history) > self._max_history:
                self._log_history = self._log_history[-self._max_history//2:]
            
            # Wywołaj callbacki
            for callback in self._callbacks:
                try:
                    callback(level, timestamp, message)
                except Exception:
                    pass
        
        # Zawsze printuj błędy
        if level == LogLevel.ERROR:
            print(full_message, file=sys.stderr)
    
    # Metody convenience
    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, kwargs if kwargs else None)
    
    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, kwargs if kwargs else None)
    
    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, kwargs if kwargs else None)
    
    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, kwargs if kwargs else None)
    
    def http(self, method: str, url: str, status: int = None, duration: float = None, **kwargs):
        """Loguje request HTTP."""
        self._stats['http_requests'] += 1
        if status and status >= 400:
            self._stats['http_errors'] += 1
        
        parts = [f"{method} {url[:80]}{'...' if len(url) > 80 else ''}"]
        if status:
            parts.append(f"status={status}")
        if duration:
            parts.append(f"time={duration:.2f}s")
        
        self._log(LogLevel.HTTP, ' | '.join(parts), kwargs if kwargs else None)
    
    def db(self, operation: str, table: str = None, rows: int = None, **kwargs):
        """Loguje operację na bazie danych."""
        self._stats['db_queries'] += 1
        
        parts = [operation]
        if table:
            parts.append(f"table={table}")
        if rows is not None:
            parts.append(f"rows={rows}")
        
        self._log(LogLevel.DB, ' | '.join(parts), kwargs if kwargs else None)
    
    def perf(self, operation: str, duration: float, **kwargs):
        """Loguje pomiar wydajności."""
        self._log(LogLevel.PERF, f"{operation} took {duration:.3f}s", kwargs if kwargs else None)
    
    def cache(self, hit: bool, key: str = None):
        """Loguje trafienie/pudło cache."""
        if hit:
            self._stats['cache_hits'] += 1
            self.debug(f"Cache HIT: {key[:50] if key else '?'}")
        else:
            self._stats['cache_misses'] += 1
            self.debug(f"Cache MISS: {key[:50] if key else '?'}")
    
    def exception(self, message: str = "Exception occurred"):
        """Loguje wyjątek z pełnym traceback."""
        tb = traceback.format_exc()
        self._log(LogLevel.ERROR, f"{message}\n{tb}")
    
    def get_history(self) -> list[tuple[LogLevel, str, str]]:
        """Zwraca historię logów."""
        with self._lock:
            return list(self._log_history)
    
    def get_stats(self) -> dict:
        """Zwraca statystyki."""
        return dict(self._stats)
    
    def clear_history(self):
        """Czyści historię logów."""
        with self._lock:
            self._log_history.clear()
    
    def export_logs(self, filepath: str) -> bool:
        """Eksportuje logi do pliku."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"CS2 Skin Analyzer - Debug Logs\n")
                f.write(f"Exported: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
                
                for level, timestamp, message in self._log_history:
                    prefix = LOG_PREFIXES.get(level, '[???]')
                    f.write(f"{timestamp} {prefix} {message}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("Statistics:\n")
                for key, value in self._stats.items():
                    f.write(f"  {key}: {value}\n")
            
            return True
        except Exception as e:
            self.error(f"Failed to export logs: {e}")
            return False


# Globalny logger
logger = DebugLogger()


# Dekorator do mierzenia czasu wykonania
def timed(func):
    """Dekorator mierzący czas wykonania funkcji."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not logger.enabled:
            return func(*args, **kwargs)
        
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.perf(f"{func.__module__}.{func.__name__}()", duration)
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(f"{func.__module__}.{func.__name__}() failed after {duration:.3f}s: {e}")
            raise
    return wrapper


# Dekorator do logowania wejścia/wyjścia funkcji
def traced(func):
    """Dekorator logujący wywołania funkcji."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not logger.enabled:
            return func(*args, **kwargs)
        
        func_name = f"{func.__module__}.{func.__name__}"
        # Skrócone argumenty
        args_repr = ', '.join(repr(a)[:50] for a in args[:3])
        if len(args) > 3:
            args_repr += ', ...'
        
        logger.debug(f"→ {func_name}({args_repr})")
        
        try:
            result = func(*args, **kwargs)
            result_repr = repr(result)[:100] if result is not None else 'None'
            logger.debug(f"← {func_name} returned {result_repr}")
            return result
        except Exception as e:
            logger.error(f"✗ {func_name} raised {type(e).__name__}: {e}")
            raise
    return wrapper
