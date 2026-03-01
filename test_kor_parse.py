import sys
import os

# Add the directory to sys.path to easily import functions if needed
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from stock_ntm_master import analyze_ntm_data_robust

tickers = ['005930.KS', '000660.KS', '373220.KS']
df = analyze_ntm_data_robust(tickers)
print("DF RESULT:")
print(df)
