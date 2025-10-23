import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import threading
import queue
import sys 
from steam_market import get_cheapest_listings

class MarketApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Skin Analyzer")
        # <--- Dostosowałem szerokość okna do nowego układu --->
        self.root.geometry("750x600") 

        self.result_queue = queue.Queue()
        
        # Opcje jakości
        self.wear_options = [
            "Brak", 
            "(Factory New)", 
            "(Minimal Wear)", 
            "(Field-Tested)", 
            "(Well-Worn)", 
            "(Battle-Scarred)"
        ]
        
        # <--- USUNIĘTA lista 'stattrack_options' --->
        
        # <--- NOWA: Zmienna do przechowywania stanu Checkboxa --->
        self.stattrack_var = tk.BooleanVar()

        # --- Widżety ---
        
        input_frame = ttk.Frame(root, padding="10")
        input_frame.pack(fill='x')

        ttk.Label(input_frame, text="Nazwa:").pack(side='left', padx=(0, 5)) # <--- Zmniejszony lewy padding
        
        self.item_entry = ttk.Entry(input_frame)
        self.item_entry.pack(fill='x', expand=True, side='left', padx=5)
        self.item_entry.insert(0, "AK-47 | Redline")

        # <--- ZASTĄPIONY Combobox przez Checkbutton --->
        # Usunęliśmy etykietę "Wariant:"
        self.stattrack_check = ttk.Checkbutton(
            input_frame,
            text="StatTrak™",         # Tekst obok pola wyboru
            variable=self.stattrack_var, # Powiązanie ze zmienną
            onvalue=True,           # Wartość, gdy zaznaczony
            offvalue=False          # Wartość, gdy odznaczony
        )
        self.stattrack_check.pack(side='left', padx=(10, 10))
        # <--- Koniec nowego widżetu --->

        ttk.Label(input_frame, text="Jakość:").pack(side='left', padx=(5, 5))
        
        self.wear_combobox = ttk.Combobox(
            input_frame, 
            values=self.wear_options, 
            width=18, 
            state='readonly'
        )
        self.wear_combobox.pack(side='left')
        self.wear_combobox.current(3) 

        self.search_button = ttk.Button(input_frame, text="Szukaj", command=self.start_search_thread)
        self.search_button.pack(side='left', padx=(5, 0))

        # Ramka na wyniki
        results_frame = ttk.Frame(root, padding="0 10 10 10")
        results_frame.pack(fill='both', expand=True)

        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, state='disabled', height=10)
        self.results_text.pack(fill='both', expand=True)

        self.process_queue()

    def update_results_text(self, text):
        """Pomocnicza funkcja do bezpiecznej aktualizacji pola tekstowego."""
        self.results_text.config(state='normal')
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.config(state='disabled')

    def start_search_thread(self):
        """
        Uruchamia wyszukiwanie w nowym wątku, aby nie blokować GUI.
        """
        
        # <--- ZMIENIONA LOGIKA: Pobieranie wartości z Checkboxa --->
        base_name = self.item_entry.get().strip()
        selected_wear = self.wear_combobox.get()
        is_stattrack = self.stattrack_var.get() # Zwróci True lub False
        # <--- Koniec pobierania wartości --->
        
        if not base_name:
            self.update_results_text("Wpisz bazową nazwę przedmiotu!")
            return
            
        # --- Budowanie pełnej nazwy (Market Hash Name) ---
        
        full_name_parts = []
        
        # 1. Dodaj wariant (jeśli checkbox zaznaczony)
        if is_stattrack: # <--- ZMIANA
            full_name_parts.append("StatTrak™")
            
        # 2. Dodaj nazwę bazową
        full_name_parts.append(base_name)
        
        # 3. Dodaj jakość (jeśli nie "Brak")
        if selected_wear != "Brak" and selected_wear:
            full_name_parts.append(selected_wear)
            
        # Złącz wszystkie części spacjami
        item_name = " ".join(full_name_parts)
        # <--- Koniec zmienionej logiki --->

        self.search_button.config(state='disabled')
        self.update_results_text(f"Szukanie ofert dla: {item_name}...\nProszę czekać (do 30 sekund)...")
        
        threading.Thread(target=self.run_search, args=(item_name,), daemon=True).start()

    def run_search(self, item_name):
        """
        Ta funkcja działa W TLE (w osobnym wątku).
        """
        try:
            listings = get_cheapest_listings(item_name)
            self.result_queue.put(listings)
        except Exception as e:
            print(f"Krytyczny błąd w wątku: {e}", file=sys.stderr)
            self.result_queue.put(None) 

    def process_queue(self):
        """
        Sprawdza kolejkę co 100ms w poszukiwaniu wyników.
        """
        try:
            listings = self.result_queue.get_nowait()
            self.display_results(listings)
            self.search_button.config(state='normal')

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def display_results(self, listings):
        """Formatuje i wyświetla końcowe wyniki."""
        
        if listings is None:
            self.update_results_text("BŁĄD: Nie udało się pobrać ofert.\nSprawdź konsolę (terminal) aby zobaczyć szczegóły błędu (np. błąd 429, timeout lub zła nazwa przedmiotu).")
        
        elif not listings:
            self.update_results_text("Nie znaleziono żadnych aktywnych ofert dla tego przedmiotu.")
        
        else:
            output = f"Znaleziono {len(listings)} najtańszych ofert:\n\n"
            for i, listing in enumerate(listings):
                output += f"#{i+1:02d} | Cena: {listing['price_pln']:.2f} PLN\n"
                output += f"     ID Oferty: {listing['listing_id']}\n"
                output += f"     ID Przedmiotu: {listing['asset_id']}\n\n"
            
            self.update_results_text(output)