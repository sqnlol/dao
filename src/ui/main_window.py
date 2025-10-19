# src/ui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from api.alt_api import get_price_data

def create_main_window():
    window = tk.Tk()
    window.title("CS2 Skin Analyzer – Wersja testowa")
    window.geometry("800x450")
    window.resizable(True, True)

    label = tk.Label(window, text="Dane cenowe skina (próbne źródła: Steam / Skinport)",
                     font=("Segoe UI", 12, "bold"))
    label.pack(pady=8)

    # Pole do wpisania nazwy skina i przycisk
    top_frame = tk.Frame(window)
    top_frame.pack(fill="x", padx=12)

    tk.Label(top_frame, text="Nazwa skina:").pack(side="left")
    entry = tk.Entry(top_frame, width=60)
    entry.insert(0, "AK-47 | Redline (Field-Tested)")
    entry.pack(side="left", padx=6)

    def on_fetch():
        skin = entry.get().strip()
        if not skin:
            messagebox.showwarning("Uwaga", "Podaj nazwę skina")
            return
        try:
            data = get_price_data(skin)
        except Exception as e:
            messagebox.showerror("Nie udało się pobrać danych", str(e))
            return

        # Wyczyść drzewko
        for i in tree.get_children():
            tree.delete(i)
        # Wstaw dane
        for row in data[:100]:
            date = row.get("date")
            price = row.get("price")
            vol = row.get("volume")
            src = row.get("source", "")
            tree.insert("", tk.END, values=(date, price, vol, src))

    btn = tk.Button(top_frame, text="Pobierz dane", command=on_fetch)
    btn.pack(side="left", padx=6)

    # Tabela
    columns = ("date", "price", "volume", "source")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=18)
    tree.heading("date", text="Data / Okres")
    tree.heading("price", text="Cena")
    tree.heading("volume", text="Ilość")
    tree.heading("source", text="Źródło")
    tree.pack(fill="both", expand=True, padx=12, pady=10)

    # Przy starcie automatycznie pobierz domyślny skin
    try:
        on_fetch()
    except Exception:
        pass

    window.mainloop()
