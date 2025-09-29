import yfinance as yf
import pandas as pd
import colorama
from colorama import Fore, Style
import xml.etree.ElementTree as ET
from pathlib import Path

colorama.init()  # active les couleurs ANSI sur Windows

def load_tickers_from_xml(path: Path):
    if not path.exists():
        return []
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        out = []
        for t in root.findall("ticker"):
            name = t.findtext("name")
            symbol = t.findtext("symbol")
            if name and symbol:
                out.append((name.strip(), symbol.strip()))
        return out
    except ET.ParseError:
        return []

# charge les tickers depuis tickers.xml situé dans le même dossier que ce script
xml_path = Path(__file__).parent / "tickers.xml"
tickers = load_tickers_from_xml(xml_path)

# fallback si le fichier XML est absent ou invalide
if not tickers:
    tickers = [
        ("THALES", "HO.PA"),
        ("LVMH", "MC.PA"),
        ("Schneider Electric", "SU.PA"),
        ("TotalEnergies", "TTE.PA"),
        ("Sanofi", "SAN.PA"),
        ("L'Oréal", "OR.PA"),
        ("Hermès", "RMS.PA"),
        ("BNP Paribas", "BNP.PA"),
        ("Air Liquide", "AI.PA"),
        ("Danone", "BN.PA"),
        # 10 actions du S&P 500
        ("AAPL", "AAPL"),
        ("Microsoft", "MSFT"),
        ("Amazon", "AMZN"),
        ("Alphabet", "GOOGL"),
        ("Tesla", "TSLA"),
        ("JPMorgan Chase", "JPM"),
        ("Visa", "V"),
        ("Eli Lilly", "LLY"),
        ("Netflix", "NFLX"),
        ("Exxon Mobil", "XOM"),
    ]

def fmt_num(x):
    if x is None or pd.isna(x):
        return "N/A"
    return f"{float(x):.2f}"

def color_ma(ma, last):
    if ma is None or pd.isna(ma) or last is None or pd.isna(last):
        return "N/A"
    s = f"{float(ma):.2f}"
    if ma > last:
        return f"{Fore.RED}{s}{Style.RESET_ALL}"
    elif ma < last:
        return f"{Fore.GREEN}{s}{Style.RESET_ALL}"
    else:
        return s

rows = []

total = len(tickers)
handled = 0
errors = 0

for name, symbol in tickers:
    try:
        tk = yf.Ticker(symbol)
        # historique 1 an pour assurer disponibilité de MA200
        hist = tk.history(period="1y", auto_adjust=True)
    except Exception:
        hist = pd.DataFrame()
        errors += 1

    if hist.empty:
        rows.append([name, symbol, "N/A", "N/A", "N/A", "N/A"])
    else:
        last_close = hist["Close"].iloc[-1]
        ma9 = hist["Close"].rolling(window=9).mean().iloc[-1]
        ma20 = hist["Close"].rolling(window=20).mean().iloc[-1]
        ma200 = hist["Close"].rolling(window=200).mean().iloc[-1]

        rows.append([
            name,
            symbol,
            fmt_num(last_close),
            color_ma(ma9, last_close),
            color_ma(ma20, last_close),
            color_ma(ma200, last_close),
        ])

    handled += 1
    remaining = total - handled
    # affichage sur une seule ligne, écrasée à chaque itération
    msg = f"Progress: total={total} | géré={handled} | restant={remaining} | erreur={errors}"
    print("\r" + msg + " " * 10, end="", flush=True)

# newline après la boucle pour ne pas écraser la sortie suivante
print()

df = pd.DataFrame(rows, columns=["Nom", "Ticker", "Dernier", "MA9", "MA20", "MA200"])
print(df.to_string(index=False))

# >>> COMMANDE D'INSTALLATION REQUISE <<<
# Pour exécuter ce script, installez yfinance, pandas et colorama :
# pip install yfinance pandas colorama
