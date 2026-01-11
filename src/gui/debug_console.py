"""
Okno konsoli debugowania dla CS2 Skin Analyzer.

Wyświetla logi w czasie rzeczywistym z kolorowaniem,
filtrowanie, eksport i panel statystyk.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import psutil
from datetime import datetime

from src.debug_logger import logger, LogLevel, LOG_COLORS, LOG_PREFIXES


class DebugConsole(tk.Toplevel):
    """Okno konsoli debugowania."""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.parent = parent
        
        self.title("🔧 CS2 Skin Analyzer - Debug Console")
        self.geometry("1000x700")
        self.minsize(800, 500)
        
        # Kolory tła
        self._bg_color = '#1a1a1a'
        self._fg_color = '#ffffff'
        self._accent_color = '#3d3d3d'
        
        self.configure(bg=self._bg_color)
        
        # Zmienna do auto-scroll
        self._auto_scroll = tk.BooleanVar(value=True)
        
        # Filtry poziomów
        self._level_filters = {level: tk.BooleanVar(value=True) for level in LogLevel}
        
        # Bufor logów do wyświetlenia (thread-safe)
        self._log_buffer = []
        self._log_lock = threading.Lock()
        
        self._setup_ui()
        self._setup_tags()
        self._register_logger()
        
        # Załaduj historię logów
        self._load_history()
        
        # Aktualizacja statystyk co 1s
        self._update_stats()
        
        # Obsługa zamknięcia
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Przetwarzaj bufor logów co 100ms
        self._process_log_buffer()
    
    def _setup_ui(self):
        """Tworzy interfejs użytkownika."""
        # Główny kontener
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # === Górny panel: filtry i przyciski ===
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 5))
        
        # Filtry poziomów
        filter_frame = ttk.LabelFrame(top_frame, text="Filtry")
        filter_frame.pack(side='left', padx=(0, 10))
        
        for i, level in enumerate(LogLevel):
            color = LOG_COLORS.get(level, '#ffffff')
            cb = ttk.Checkbutton(
                filter_frame,
                text=LOG_PREFIXES[level],
                variable=self._level_filters[level],
                command=self._apply_filters
            )
            cb.pack(side='left', padx=3)
        
        # Przyciski akcji
        action_frame = ttk.Frame(top_frame)
        action_frame.pack(side='right')
        
        ttk.Button(action_frame, text="Kopiuj", command=self._copy_logs, width=12).pack(side='left', padx=2)
        ttk.Button(action_frame, text="Eksportuj", command=self._export_logs, width=12).pack(side='left', padx=2)
        ttk.Button(action_frame, text="Wyczyść", command=self._clear_logs, width=12).pack(side='left', padx=2)
        
        # Auto-scroll checkbox
        ttk.Checkbutton(
            action_frame,
            text="Auto-scroll",
            variable=self._auto_scroll
        ).pack(side='left', padx=(10, 0))
        
        # === Środkowy panel: logi ===
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill='both', expand=True)
        
        # Text widget z scrollbarem
        self.log_text = tk.Text(
            log_frame,
            bg='#0d0d0d',
            fg='#cccccc',
            font=('Consolas', 10),
            wrap='none',
            state='disabled',
            cursor='arrow'
        )
        
        # Scrollbary
        y_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        x_scroll = ttk.Scrollbar(log_frame, orient='horizontal', command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        # Pack
        y_scroll.pack(side='right', fill='y')
        x_scroll.pack(side='bottom', fill='x')
        self.log_text.pack(side='left', fill='both', expand=True)
        
        # === Dolny panel: statystyki ===
        stats_frame = ttk.LabelFrame(main_frame, text="Statystyki")
        stats_frame.pack(fill='x', pady=(5, 0))
        
        # Wiersz statystyk
        self._stats_labels = {}
        stats_items = [
            ('http_requests', 'HTTP Requests'),
            ('http_errors', 'HTTP Errors'),
            ('db_queries', 'DB Queries'),
            ('cache_hits', 'Cache Hits'),
            ('cache_misses', 'Cache Misses'),
            ('memory', 'Memory'),
            ('uptime', 'Uptime'),
        ]
        
        for i, (key, label) in enumerate(stats_items):
            frame = ttk.Frame(stats_frame)
            frame.pack(side='left', padx=10, pady=5)
            
            ttk.Label(frame, text=f"{label}:", font=('Segoe UI', 9, 'bold')).pack(side='left')
            value_label = ttk.Label(frame, text="0", font=('Consolas', 9))
            value_label.pack(side='left', padx=(5, 0))
            self._stats_labels[key] = value_label
        
        # === Panel informacji o aplikacji ===
        info_frame = ttk.LabelFrame(main_frame, text="Informacje o środowisku")
        info_frame.pack(fill='x', pady=(5, 0))
        
        info_text = self._get_environment_info()
        info_label = ttk.Label(info_frame, text=info_text, font=('Consolas', 9))
        info_label.pack(anchor='w', padx=5, pady=3)
    
    def _setup_tags(self):
        """Konfiguruje tagi kolorów dla Text widget."""
        for level, color in LOG_COLORS.items():
            self.log_text.tag_configure(level.name, foreground=color)
        
        # Specjalne tagi
        self.log_text.tag_configure('timestamp', foreground='#666666')
        self.log_text.tag_configure('highlight', background='#333300')
    
    def _get_environment_info(self) -> str:
        """Zwraca informacje o środowisku."""
        import platform
        parts = [
            f"Python {sys.version.split()[0]}",
            f"OS: {platform.system()} {platform.release()}",
            f"Arch: {platform.machine()}",
        ]
        
        # Tkinter version
        try:
            parts.append(f"Tk {tk.TkVersion}")
        except:
            pass
        
        # Pillow version
        try:
            from PIL import __version__ as pil_version
            parts.append(f"Pillow {pil_version}")
        except:
            pass
        
        # Requests version
        try:
            import requests
            parts.append(f"Requests {requests.__version__}")
        except:
            pass
        
        return " | ".join(parts)
    
    def _register_logger(self):
        """Rejestruje callback w loggerze."""
        logger.register_callback(self._on_log)
    
    def _unregister_logger(self):
        """Wyrejestrowuje callback z loggera."""
        logger.unregister_callback(self._on_log)
    
    def _on_log(self, level: LogLevel, timestamp: str, message: str):
        """Callback wywoływany przy każdym logu."""
        with self._log_lock:
            self._log_buffer.append((level, timestamp, message))
    
    def _process_log_buffer(self):
        """Przetwarza bufor logów i wyświetla je."""
        try:
            with self._log_lock:
                buffer = self._log_buffer[:]
                self._log_buffer.clear()
            
            if buffer:
                self.log_text.config(state='normal')
                
                for level, timestamp, message in buffer:
                    # Sprawdź filtr
                    if not self._level_filters[level].get():
                        continue
                    
                    prefix = LOG_PREFIXES.get(level, '[???]')
                    
                    # Wstaw timestamp
                    self.log_text.insert('end', f"{timestamp} ", 'timestamp')
                    # Wstaw prefix z kolorem
                    self.log_text.insert('end', f"{prefix} ", level.name)
                    # Wstaw wiadomość
                    self.log_text.insert('end', f"{message}\n")
                
                self.log_text.config(state='disabled')
                
                # Auto-scroll
                if self._auto_scroll.get():
                    self.log_text.see('end')
        except Exception:
            pass
        finally:
            # Kontynuuj przetwarzanie
            if self.winfo_exists():
                self.after(100, self._process_log_buffer)
    
    def _load_history(self):
        """Ładuje historię logów."""
        history = logger.get_history()
        if not history:
            return
        
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"=== Loaded {len(history)} historical logs ===\n\n", 'timestamp')
        
        for level, timestamp, message in history[-500:]:  # Ostatnie 500
            if not self._level_filters[level].get():
                continue
            
            prefix = LOG_PREFIXES.get(level, '[???]')
            self.log_text.insert('end', f"{timestamp} ", 'timestamp')
            self.log_text.insert('end', f"{prefix} ", level.name)
            self.log_text.insert('end', f"{message}\n")
        
        self.log_text.insert('end', f"\n=== Live logs ===\n\n", 'timestamp')
        self.log_text.config(state='disabled')
        self.log_text.see('end')
    
    def _apply_filters(self):
        """Odświeża widok po zmianie filtrów."""
        # Wyczyść i przeładuj
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')
        self._load_history()
    
    def _update_stats(self):
        """Aktualizuje statystyki."""
        try:
            stats = logger.get_stats()
            
            for key, label in self._stats_labels.items():
                if key == 'memory':
                    # Pamięć procesu
                    try:
                        process = psutil.Process()
                        mem_mb = process.memory_info().rss / (1024 * 1024)
                        label.config(text=f"{mem_mb:.1f} MB")
                    except:
                        label.config(text="N/A")
                elif key == 'uptime':
                    # Czas działania
                    import time
                    uptime = time.time() - logger._start_time
                    mins, secs = divmod(int(uptime), 60)
                    hours, mins = divmod(mins, 60)
                    label.config(text=f"{hours:02d}:{mins:02d}:{secs:02d}")
                else:
                    value = stats.get(key, 0)
                    label.config(text=str(value))
        except Exception:
            pass
        finally:
            if self.winfo_exists():
                self.after(1000, self._update_stats)
    
    def _copy_logs(self):
        """Kopiuje logi do schowka."""
        try:
            content = self.log_text.get('1.0', 'end-1c')
            self.clipboard_clear()
            self.clipboard_append(content)
            logger.info("Logi skopiowane do schowka")
        except Exception as e:
            logger.error(f"Błąd kopiowania logów: {e}")
    
    def _export_logs(self):
        """Eksportuje logi do pliku."""
        try:
            filepath = filedialog.asksaveasfilename(
                parent=self,
                title="Eksportuj logi",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"cs2_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if filepath:
                if logger.export_logs(filepath):
                    logger.info(f"Logi wyeksportowane do: {filepath}")
                    messagebox.showinfo("Eksport", f"Logi zapisane do:\n{filepath}", parent=self)
        except Exception as e:
            logger.error(f"Błąd eksportu logów: {e}")
    
    def _clear_logs(self):
        """Czyści logi."""
        if messagebox.askyesno("Wyczyść logi", "Czy na pewno wyczyścić wszystkie logi?", parent=self):
            self.log_text.config(state='normal')
            self.log_text.delete('1.0', 'end')
            self.log_text.config(state='disabled')
            logger.clear_history()
            logger.info("Logi wyczyszczone")
    
    def _on_close(self):
        """Obsługa zamknięcia okna."""
        self._unregister_logger()
        self.destroy()
        
        # Poinformuj kontroler
        if hasattr(self.controller, '_debug_console'):
            self.controller._debug_console = None


class DebugManager:
    """Manager trybu debugowania."""
    
    def __init__(self, controller):
        self.controller = controller
        self._debug_console = None
        self._enabled = False
        self._original_title = None
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def toggle(self):
        """Przełącza tryb debugowania."""
        if self._enabled:
            self.disable()
        else:
            self.enable()
    
    def enable(self):
        """Włącza tryb debugowania."""
        self._enabled = True
        logger.enabled = True
        
        # Zapisz oryginalny tytuł
        self._original_title = self.controller.root.title()
        
        # Zaktualizuj tytuł
        self._update_title()
        
        # Otwórz konsolę
        self._open_console()
        
        logger.info("=== DEBUG MODE ENABLED ===")
        logger.info(f"Application: CS2 Skin Analyzer")
        logger.info(f"User: {self.controller.steam_name}")
        logger.info(f"Logged in: {bool(self.controller.login_cookie)}")
        logger.info(f"Currency: {self.controller.currency}")
    
    def disable(self):
        """Wyłącza tryb debugowania."""
        logger.info("=== DEBUG MODE DISABLED ===")
        
        self._enabled = False
        logger.enabled = False
        
        # Przywróć tytuł
        if self._original_title:
            self.controller.root.title(self._original_title)
        
        # Zamknij konsolę
        self._close_console()
    
    def _update_title(self):
        """Aktualizuje tytuł okna z informacją o debug mode."""
        base = self._original_title or "CS2 Skin Analyzer"
        self.controller.root.title(f"{base} [🔧 DEBUG]")
    
    def _open_console(self):
        """Otwiera okno konsoli debugowania."""
        if self._debug_console is None or not self._debug_console.winfo_exists():
            self._debug_console = DebugConsole(self.controller.root, self.controller)
            self._debug_console.focus_set()
    
    def _close_console(self):
        """Zamyka okno konsoli debugowania."""
        if self._debug_console and self._debug_console.winfo_exists():
            self._debug_console.destroy()
        self._debug_console = None
    
    def show_console(self):
        """Pokazuje konsolę (jeśli ukryta) lub tworzy nową."""
        if self._enabled:
            self._open_console()
