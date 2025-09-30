import requests
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
from io import StringIO
import yfinance as yf
import time

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CAC40_URL = "https://en.wikipedia.org/wiki/CAC_40"

out_path = Path(__file__).parent / "tickers.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_html_tables(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return pd.read_html(StringIO(resp.text))

def fetch_sp500():
    tables = fetch_html_tables(SP500_URL)
    df = tables[0]
    symbols = df["Symbol"].astype(str).tolist()
    names = df["Security"].astype(str).tolist()
    return list(zip(names, symbols))

def fetch_cac40():
    tables = fetch_html_tables(CAC40_URL)
    # repérer la table contenant la liste des entreprises
    for t in tables:
        cols = [c.lower() for c in t.columns.astype(str)]
        if any("company" in c or "entreprise" in c or "société" in c or "issuer" in c for c in cols):
            df = t
            break
    else:
        df = tables[0]
    # heuristiques pour nom / symbole
    name_col = None
    sym_col = None
    for c in df.columns:
        lc = str(c).lower()
        if any(k in lc for k in ("company", "entreprise", "nom", "societ", "société")) and name_col is None:
            name_col = c
        if any(k in lc for k in ("ticker", "code", "isin", "symbol")) and sym_col is None:
            sym_col = c
    if name_col is None:
        name_col = df.columns[0]
    if sym_col is None:
        for c in df.columns:
            if df[c].astype(str).str.len().mean() < 8:
                sym_col = c
                break
        if sym_col is None:
            sym_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    symbols = df[sym_col].astype(str).tolist()
    names = df[name_col].astype(str).tolist()
    return list(zip(names, symbols))

def write_xml(pairs, path: Path):
    root = ET.Element("tickers")
    for name, symbol, country in pairs:
        t = ET.SubElement(root, "ticker")
        n = ET.SubElement(t, "name")
        n.text = name
        s = ET.SubElement(t, "symbol")
        s.text = symbol
        c = ET.SubElement(t, "country")
        c.text = country if country is not None else ""
    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except Exception:
        pass
    tree.write(path, encoding="utf-8", xml_declaration=True)

def get_country_for_symbol(symbol, pause=0.1):
    try:
        tk = yf.Ticker(symbol)
        info = tk.info or {}
        # tenter plusieurs clés possibles
        country = info.get("country") or info.get("countryOfIncorporation") or info.get("headquartersCountry") or info.get("location") or ""
        # limiter la vitesse pour éviter blocages
        time.sleep(pause)
        return country
    except Exception:
        return ""

def main():
    try:
        sp = fetch_sp500()
        print(f"Récupéré S&P500: {len(sp)} lignes")
    except Exception as e:
        print(f"Erreur récupération S&P500: {e}")
        sp = []
    try:
        cac = fetch_cac40()
        print(f"Récupéré CAC40: {len(cac)} lignes")
    except Exception as e:
        print(f"Erreur récupération CAC40: {e}")
        cac = []
    combined = sp + cac
    seen = set()
    uniq = []
    for n, s in combined:
        key = (n.strip(), s.strip())
        if key not in seen:
            seen.add(key)
            uniq.append(key)

    # enrichir avec la nationalité récupérée via yfinance.info
    enriched = []
    total = len(uniq)
    for i, (name, symbol) in enumerate(uniq, start=1):
        country = get_country_for_symbol(symbol)
        enriched.append((name, symbol, country))
        # affichage simple de progression
        print(f"\rFetching country {i}/{total} for {symbol} -> {country}", end="", flush=True)
    print()  # newline après progression

    write_xml(enriched, out_path)
    print(f"Wrote {len(enriched)} tickers to {out_path}")

if __name__ == "__main__":
    main()