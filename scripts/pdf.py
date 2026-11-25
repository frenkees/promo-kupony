import csv
import os
from fpdf import FPDF

# --- KONFIGURACE ---
CSV_FILE = 'karticky.csv'      # Zadej název tvého CSV souboru
OUTPUT_PDF = 'arch_karet.pdf'  # Název výsledného PDF dokumentu

# Rozměry pro A4 v milimetrech (210 x 297)
MARGIN_X = 15
MARGIN_Y = 15
COLUMNS = 2
ROWS = 3

PDF_WIDTH = 210
PDF_HEIGHT = 297

# Dynamický výpočet buněk, aby přesně seděly na papír
COL_WIDTH = (PDF_WIDTH - 2 * MARGIN_X) / COLUMNS
ROW_HEIGHT = (PDF_HEIGHT - 2 * MARGIN_Y) / ROWS
QR_SIZE = 45  # Velikost QR kódu v mm

def main():
    # Inicializace A4 dokumentu na výšku (Portrait)
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    
    # Načtení dat z CSV
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        kody = list(reader)
        
    for i, row_data in enumerate(kody):
        # Pokud se naplnilo 6 pozic (2 sloupce * 3 řádky), přidej novou stránku
        if i % (COLUMNS * ROWS) == 0:
            pdf.add_page()
            
        # Výpočet indexu na aktuální straně (0 až 5)
        pozice_na_strane = i % (COLUMNS * ROWS)
        sloupec = pozice_na_strane % COLUMNS
        radek = pozice_na_strane // COLUMNS
        
        # Absolutní X/Y souřadnice levého horního rohu aktuální "buňky" na papíře
        cell_x = MARGIN_X + sloupec * COL_WIDTH
        cell_y = MARGIN_Y + radek * ROW_HEIGHT
        
        # 1. VLOŽENÍ QR KÓDU (vycentrování v buňce)
        qr_path = row_data['qr_path']
        qr_x = cell_x + (COL_WIDTH - QR_SIZE) / 2
        qr_y = cell_y + 15
        
        if os.path.exists(qr_path):
            pdf.image(qr_path, x=qr_x, y=qr_y, w=QR_SIZE)
        else:
            # Pokud PNG chybí, nakreslí alespoň kontrolní obdélník a upozorní v konzoli
            pdf.rect(qr_x, qr_y, QR_SIZE, QR_SIZE)
            print(f"Varování: Nenalezen obrázek {qr_path}")
            
        # 2. VLOŽENÍ HLAVNÍHO KÓDU POD OBRÁZEK
        pdf.set_font("helvetica", "B", 24)
        text_code = row_data['code']
        
        # Změříme šířku textu, abychom ho mohli vycentrovat do středu sloupce
        text_width = pdf.get_string_width(text_code)
        text_x = cell_x + (COL_WIDTH - text_width) / 2
        text_y = qr_y + QR_SIZE + 12
        pdf.text(x=text_x, y=text_y, text=text_code)
        
        # 3. VLOŽENÍ POPISU / PAYLOADU (Drobnější text úplně dole)
        pdf.set_font("helvetica", "", 12)
        pdf.set_text_color(100, 100, 100) # Šedá barva
        text_payload = row_data['qr_payload']
        
        payload_width = pdf.get_string_width(text_payload)
        payload_x = cell_x + (COL_WIDTH - payload_width) / 2
        payload_y = text_y + 6
        pdf.text(x=payload_x, y=payload_y, text=text_payload)
        
        # Vrácení barvy textu na černou pro další průchody
        pdf.set_text_color(0, 0, 0)
        
    # Finální uložení
    pdf.output(OUTPUT_PDF)
    print(f"Vygenerováno {len(kody)} karet.")
    print(f"Hotovo! PDF bylo úspěšně uloženo jako: {OUTPUT_PDF}")

if __name__ == "__main__":
    main()