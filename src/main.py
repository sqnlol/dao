import tkinter as tk
from tkinter import ttk
import sys
import database 
import random # <-- DODANY IMPORT DO GENEROWANIA LOSOWYCH ID

def log_to_gui(widget, message):
    """
    Pomocnicza funkcja do dodawania tekstu do widżetu Text w GUI.
    """
    widget.config(state=tk.NORMAL)
    widget.insert(tk.END, message + "\n")
    widget.config(state=tk.DISABLED)
    widget.see(tk.END)


def fetch_and_save_data(log_widget, name_entry, quality_combo, stattrak_var, tree_widget):
    """
    Logika pobierania i zapisywania danych.
    """
    
    log_widget.config(state=tk.NORMAL)
    log_widget.delete('1.0', tk.END)
    log_widget.config(state=tk.DISABLED)
    log_to_gui(log_widget, "Rozpoczynam nowy cykl...")

    skin_name = name_entry.get()
    skin_quality = quality_combo.get()
    is_stattrak_bool = stattrak_var.get()
    skin_stattrak = 1 if is_stattrak_bool else 0

    if not skin_name or not skin_quality:
        log_to_gui(log_widget, "BŁĄD: Musisz podać nazwę skina i wybrać jakość.")
        return

    log_to_gui(log_widget, f"Przetwarzanie dla: {skin_name} | {skin_quality} (Stattrak: {'Tak' if skin_stattrak else 'Nie'})")

    try:
        skin_type_id = database.get_or_create_skin(
            name=skin_name,
            quality=skin_quality,
            stattrak=skin_stattrak,
            weapon_type=None
        )
        if skin_type_id is None:
            log_to_gui(log_widget, "KRYTYCZNY BŁĄD: Nie udało się pobrać ID typu skina.")
            return
        log_to_gui(log_widget, f"Używam skin_type_id: {skin_type_id} (pobrane z bazy lub nowe)")
    except Exception as e:
        log_to_gui(log_widget, f"Wystąpił błąd podczas get_or_create_skin: {e}")
        return

    # 5. SYMULACJA POBRANIA 10 REKORDÓW
    #
    # --- ZMIANA: Dodajemy losowy prefix do ID, aby uniknąć duplikatów ---
    #
    log_to_gui(log_widget, "Symuluję pobieranie 10 rekordów z rynku...")
    try:
        # Generujemy losowy "prefix" dla ID, aby każda paczka danych była unikalna
        random_prefix = str(random.randint(100000, 999999))
        
        listings_data = [
            {'market_id': f'{random_prefix}_3456789001', 'price': 15.50, 'float': 0.1834, 'stickers': ['Sticker | Fnatic']},
            {'market_id': f'{random_prefix}_3456789002', 'price': 16.20, 'float': 0.2231, 'stickers': []},
            {'market_id': f'{random_prefix}_3456789003', 'price': 15.85, 'float': 0.1999, 'stickers': ['Sticker | NIP']},
            {'market_id': f'{random_prefix}_3456789004', 'price': 17.00, 'float': 0.2401, 'stickers': []},
            {'market_id': f'{random_prefix}_3456789005', 'price': 15.45, 'float': 0.1805, 'stickers': ['Sticker | Titan (Holo)']},
            {'market_id': f'{random_prefix}_3456789006', 'price': 16.10, 'float': 0.2112, 'stickers': []},
            {'market_id': f'{random_prefix}_3456789007', 'price': 16.30, 'float': 0.2250, 'stickers': []},
            {'market_id': f'{random_prefix}_3456789008', 'price': 15.90, 'float': 0.2000, 'stickers': ['Sticker | iBUYPOWER (Holo)']},
            {'market_id': f'{random_prefix}_3456789009', 'price': 16.05, 'float': 0.2050, 'stickers': []},
            {'market_id': f'{random_prefix}_3456789010', 'price': 15.75, 'float': 0.1950, 'stickers': []}
        ]
        # --- KONIEC ZMIANY ---
        
        log_to_gui(log_widget, f"Pobrano {len(listings_data)} nowych ofert.")
    
    except Exception as e:
        log_to_gui(log_widget, f"Błąd podczas pobierania danych z rynku: {e}")
        return

    # 6. Zapisywanie do bazy
    log_to_gui(log_widget, "Rozpoczynam zapisywanie ofert do bazy danych...")
    log_to_gui(log_widget, "\n--- POBRANE DANE (zapisywane w bazie) ---")
    
    saved_count = 0
    skipped_count = 0
    for i, listing in enumerate(listings_data):
        
        stickers_str = ", ".join(listing['stickers']) if listing['stickers'] else "Brak"
        log_message = f"Oferta {i+1}: ID: {listing['market_id']}, Cena: {listing['price']:.2f}, Float: {listing['float']:.4f}, Naklejki: {stickers_str}"
        
        try:
            success = database.add_market_listing(
                skin_type_id=skin_type_id,
                market_listing_id=listing['market_id'],
                price=listing['price'],
                float_value=listing['float'],
                stickers_list=listing['stickers']
            )
            
            if success:
                log_to_gui(log_widget, log_message)
                saved_count += 1
            else:
                log_to_gui(log_widget, f"Pominięto (duplikat): ID {listing['market_id']}")
                skipped_count += 1
                
        except Exception as e:
            log_to_gui(log_widget, f"Błąd podczas zapisu listingu {listing}: {e}")
            skipped_count += 1

    log_to_gui(log_widget, "\n--- ZAKOŃCZONO ---")
    log_to_gui(log_widget, f"Pomyślnie zapisano {saved_count} nowych ofert.")
    log_to_gui(log_widget, f"Pominięto {skipped_count} ofert (duplikaty lub błędy).")
    
    # Automatyczne odświeżenie tabeli
    log_to_gui(log_widget, "Automatycznie odświeżam widok bazy danych...")
    try:
        populate_data_tab(tree_widget)
        log_to_gui(log_widget, "Widok bazy danych odświeżony.")
    except Exception as e:
        log_to_gui(log_widget, f"Błąd podczas odświeżania widoku bazy: {e}")


def populate_data_tab(tree):
    """
    Czyści tabelę (Treeview) i wypełnia ją świeżymi danymi z bazy.
    (bez zmian)
    """
    for item in tree.get_children():
        tree.delete(item)
        
    all_listings = database.get_all_listings_with_skin_details()
    
    for i, row in enumerate(all_listings):
        market_id_str = row[0]
        full_name = f"{row[1]} ({row[2]})"
        stattrak_str = "Tak" if row[3] == 1 else "Nie"
        price_str = f"{row[4]:.2f}"
        float_str = f"{row[5]}" 
        date_str = row[6]
        
        tree.insert(
            parent="", 
            index="end", 
            iid=i, 
            values=(market_id_str, full_name, stattrak_str, price_str, float_str, date_str)
        )

# --------------------------------------------------
# GŁÓWNA FUNKCJA APLIKACJI (main)
# (bez zmian)
# --------------------------------------------------
def main():
    """
    Główna funkcja aplikacji.
    """
    
    print("Inicjalizuję bazę danych (plik 'csgo_market.db')...")
    database.init_db()
    print("Inicjalizacja bazy danych zakończona.")

    root = tk.Tk()
    root.title("Analizator Rynku CS2 (DAO)")
    root.geometry("800x600")

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    
    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, padx=10, fill="both", expand=True)

    tab_fetch = ttk.Frame(notebook, padding="10")
    tab_db_view = ttk.Frame(notebook, padding="10")

    notebook.add(tab_fetch, text='Pobieranie Danych')
    notebook.add(tab_db_view, text='Podgląd Bazy Danych')

    # --------------------------------------------------
    # Zakładka 1: POBIERANIE DANYCH
    # --------------------------------------------------
    
    tab_fetch.rowconfigure(3, weight=1) 
    tab_fetch.columnconfigure(0, weight=1)

    options_frame = ttk.LabelFrame(tab_fetch, text="Opcje Wyszukiwania", padding=15)
    options_frame.grid(row=1, column=0, pady=10, sticky="ew")
    options_frame.columnconfigure(1, weight=1) 

    name_label = ttk.Label(options_frame, text="Nazwa skina:")
    name_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    name_entry = ttk.Entry(options_frame, width=40)
    name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    name_entry.insert(0, "AK-47 | Redline") 

    quality_label = ttk.Label(options_frame, text="Jakość:")
    quality_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    quality_values = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
    quality_combo = ttk.Combobox(options_frame, values=quality_values, state="readonly")
    quality_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    quality_combo.set("Field-Tested")

    stattrak_var = tk.BooleanVar() 
    stattrak_check = ttk.Checkbutton(options_frame, text="Stattrak™", variable=stattrak_var, onvalue=True, offvalue=False)
    stattrak_check.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="w")

    fetch_button = ttk.Button(tab_fetch, text="Pobierz dane")
    fetch_button.grid(row=2, column=0, pady=10, ipady=10, sticky="ew")

    log_frame = ttk.LabelFrame(tab_fetch, text="Konsola Logów / Wyniki", padding=10)
    log_frame.grid(row=3, column=0, pady=(10, 0), sticky="nsew") 
    log_frame.rowconfigure(0, weight=1)
    log_frame.columnconfigure(0, weight=1)

    log_text_widget = tk.Text(log_frame, wrap="word", state=tk.DISABLED, height=10)
    log_text_widget.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text_widget.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    log_text_widget.config(yscrollcommand=scrollbar.set)
    
    log_to_gui(log_text_widget, "Aplikacja gotowa. Wybierz skina i naciśnij 'Pobierz dane'.")

    # --------------------------------------------------
    # Zakładka 2: PODGLĄD BAZY DANYCH
    # --------------------------------------------------
    
    tab_db_view.rowconfigure(1, weight=1)
    tab_db_view.columnconfigure(0, weight=1)

    refresh_button = ttk.Button(tab_db_view, text="Odśwież dane z bazy")
    refresh_button.grid(row=0, column=0, pady=10, sticky="ew")
    
    columns = ('market_id', 'name', 'stattrak', 'price', 'float', 'date')
    tree = ttk.Treeview(tab_db_view, columns=columns, show='headings')
    
    tree.heading('market_id', text='ID Oferty (Rynkowe)')
    tree.heading('name', text='Nazwa Skina')
    tree.heading('stattrak', text='Stattrak')
    tree.heading('price', text='Cena ($)')
    tree.heading('float', text='Float')
    tree.heading('date', text='Data Pobrania')

    tree.column('market_id', width=120, anchor='center')
    tree.column('name', width=250)
    tree.column('stattrak', width=60, anchor='center')
    tree.column('price', width=80, anchor='e')
    tree.column('float', width=100, anchor='w')
    tree.column('date', width=150)

    tree.grid(row=1, column=0, sticky='nsew')
    
    tree_scrollbar = ttk.Scrollbar(tab_db_view, orient="vertical", command=tree.yview)
    tree_scrollbar.grid(row=1, column=1, sticky='ns')
    tree.configure(yscrollcommand=tree_scrollbar.set)

    # --------------------------------------------------
    # KONFIGURACJA KOMEND
    # --------------------------------------------------
    fetch_button.config(command=lambda: fetch_and_save_data(
        log_text_widget, 
        name_entry, 
        quality_combo, 
        stattrak_var,
        tree
    ))
    
    refresh_button.config(command=lambda: populate_data_tab(tree))
    
    # --------------------------------------------------
    # Uruchomienie aplikacji
    # --------------------------------------------------
    populate_data_tab(tree)
    root.mainloop()


if __name__ == "__main__":
    main()