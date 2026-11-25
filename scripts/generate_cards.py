#!/usr/bin/env python3
"""
Generátor fondu promo karet → CSV (volitelně i QR PNG).

Vygeneruje N unikátních náhodných 4místných kódů a zapíše je do CSV
připraveného pro hromadnou sazbu karet (InDesign data merge nebo Python→PDF).

Použití:
    python generate_cards.py                      # 1000 kódů → karticky.csv
    python generate_cards.py -n 1000 --qr         # + vygeneruje QR PNG do ./qr/
    python generate_cards.py --prefix "" --out fond.csv

CSV sloupce:
    code        zero-padded 4místný kód (např. "0473")  -> tiskne se na kartu jako PIN záloha
    qr_payload  řetězec zakódovaný v QR (např. "PROMO-0473") -> InDesign umí QR z datového pole
    qr_path     cesta k PNG (jen s --qr)                   -> pro data merge přes obrázkové pole
"""
import csv
import os
import random
import argparse


def generate_codes(n, low=1000, high=9999):
    population = high - low + 1
    if n > population:
        raise ValueError(f"Nelze vygenerovat {n} unikátních kódů z rozsahu {low}-{high} ({population} hodnot).")
    return [f"{c:04d}" for c in random.sample(range(low, high + 1), n)]


def main():
    ap = argparse.ArgumentParser(description="Generátor fondu promo karet")
    ap.add_argument("-n", type=int, default=1000, help="počet karet (default 1000)")
    ap.add_argument("--low", type=int, default=1000, help="dolní mez kódu (default 1000)")
    ap.add_argument("--high", type=int, default=9999, help="horní mez kódu (default 9999)")
    ap.add_argument("--prefix", default="PROMO", help='prefix v QR payloadu, "" = jen kód')
    ap.add_argument("--out", default="karticky.csv", help="výstupní CSV")
    ap.add_argument("--qr", action="store_true", help="vygenerovat i QR PNG")
    ap.add_argument("--qrdir", default="qr", help="složka pro QR PNG")
    args = ap.parse_args()

    codes = generate_codes(args.n, args.low, args.high)

    if args.qr:
        import qrcode
        os.makedirs(args.qrdir, exist_ok=True)

    rows = []
    for code in codes:
        payload = f"{args.prefix}-{code}" if args.prefix else code
        qr_path = ""
        if args.qr:
            qr_path = os.path.join(args.qrdir, f"{code}.png")
            qrcode.make(payload).save(qr_path)
        rows.append({"code": code, "qr_payload": payload, "qr_path": qr_path})

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "qr_payload", "qr_path"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Vygenerováno {len(rows)} unikátních kódů → {args.out}"
          + (f" (+ QR PNG ve složce {args.qrdir}/)" if args.qr else ""))


if __name__ == "__main__":
    main()
