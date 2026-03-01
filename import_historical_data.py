import pandas as pd
from datetime import datetime, timedelta
import os
import json

def excel_date_to_datetime(excel_date):
    """Convert Excel serial date (e.g. 45149) into Python datetime."""
    try:
        excel_date = float(excel_date)
        return datetime(1899, 12, 30) + timedelta(days=excel_date)
    except:
        return None

def main():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    HIST_FILE = os.path.join(SCRIPT_DIR, "College_Global_Scouter_20230811.xlsb")
    DB_FILE = os.path.join(SCRIPT_DIR, "Global_NTM_Master_DB.xlsx")
    
    print("Loading historical file (this might take a moment)...")
    # Read required sheets (using engine='pyxlsb')
    df_num = pd.read_excel(HIST_FILE, sheet_name='3. NUM', engine='pyxlsb')
    df_eps = pd.read_excel(HIST_FILE, sheet_name='2. EPS', engine='pyxlsb')
    
    # ---------------------------------------------------------
    # 1. Parsing Historical Prices from [3. NUM]
    # ---------------------------------------------------------
    # The first row contains the column labels/dates, the second row contains sub-headers like 'Date', 'Ticker'
    headers_row_0 = df_num.iloc[0].values
    headers_row_1 = df_num.iloc[1].values
    
    date_cols_num = []
    # Identify which columns represent historical dates based on Row 1 having integer-like excel dates
    for i, val in enumerate(headers_row_1):
        if str(val).isdigit() and int(val) > 40000:
            date_cols_num.append((i, int(val)))
            
    print(f"Found {len(date_cols_num)} historical date snapshots for Pricing.")
    
    # We also need to find the Ticker column index. Row 1 has 'Ticker' text
    ticker_col_idx = -1
    for i, val in enumerate(headers_row_1):
        if str(val) == 'Ticker':
            ticker_col_idx = i
            break
            
    if ticker_col_idx == -1:
        print("Could not find 'Ticker' column in 3. NUM")
        return

    price_records = []
    for row_idx in range(2, len(df_num)):
        row = df_num.iloc[row_idx]
        ticker = row.iloc[ticker_col_idx]
        if pd.isna(ticker) or str(ticker).strip() == "":
            continue
            
        for col_idx, excel_date in date_cols_num:
            price = row.iloc[col_idx]
            if pd.notna(price) and str(price).strip() not in ('', '-', '#N/A', 'N/A', '#VALUE!'):
                dt = excel_date_to_datetime(excel_date)
                if dt:
                    try:
                        price_float = float(price)
                        price_records.append({
                            'Date': dt.strftime("%Y-%m-%d"),
                            'Ticker': str(ticker).strip(),
                            'Price': price_float
                        })
                    except ValueError:
                        # Skip if price cannot be parsed as a float (e.g., '0x17')
                        pass

    df_price_hist = pd.DataFrame(price_records).drop_duplicates()
    
    # ---------------------------------------------------------
    # 2. Parsing Historical EPS from [2. EPS]
    # ---------------------------------------------------------
    headers_eps_row_1 = df_eps.iloc[1].values
    date_cols_eps = []
    # EPS dates are located on different columns, usually labeled by excel date or '1개월전' etc.
    # We will search row 0 and row 1 for excel dates > 40000 or header texts mapped to dates.
    # In [2. EPS], row 0 is actually parsed as df_eps.columns by default.
    headers_eps_row_top = df_eps.columns.values
    for i, val in enumerate(headers_eps_row_top):
        # some columns are integers or float representations of dates
        str_val = str(val).split('.')[0] # handle '45149.0' or '45149'
        if str_val.isdigit():
             num = int(str_val)
             if num > 40000:
                 # In this format, the EPS column is sometimes under this date, 
                 # or the specific forward EPS might be in cell below. Let's just 
                 # assume the column itself contains the 'EPS (Fwd.12M)' value further down.
                 # Let's verify by looking at row 1 (which is index 0 in dataframe using header=0)
                 header_text = str(df_eps.iloc[0, i]) 
                 if 'EPS' in header_text or 'Fwd' in header_text:
                     date_cols_eps.append((i, num))
                 elif 'EPS' in str(df_eps.iloc[1, i]):
                     date_cols_eps.append((i, num))
                     
    # Often, columns to the left form a group. So if row 0 has date, row 1 has 'EPS'
    print(f"Found {len(date_cols_eps)} historical date snapshots for EPS.")
    
    eps_records = []
    for row_idx in range(2, len(df_eps)):
        row = df_eps.iloc[row_idx]
        ticker = row.iloc[ticker_col_idx] # Assuming ticker is same index, wait let's find it.
        
        # Find Ticker col for EPS sheet
        eps_ticker_col = -1
        for i, val in enumerate(headers_eps_row_1):
            if str(val) == '종목코드' or str(val) == 'Ticker':
                eps_ticker_col = i
                break
        
        if eps_ticker_col == -1: 
            eps_ticker_col = 1 # Usually B column
            
        ticker = row.iloc[eps_ticker_col]
        if pd.isna(ticker) or str(ticker).strip() == "":
            continue
            
        for col_idx, excel_date in date_cols_eps:
            eps_val = row.iloc[col_idx]
            if pd.notna(eps_val) and str(eps_val).strip() != '-' and eps_val != '':
                try:
                    dt = excel_date_to_datetime(excel_date)
                    if dt:
                        eps_records.append({
                            'Date': dt.strftime("%Y-%m-%d"),
                            'Ticker': str(ticker).strip(),
                            'NTM_EPS': float(eps_val)
                        })
                except Exception:
                    pass

    df_eps_hist = pd.DataFrame(eps_records).drop_duplicates()
    
    # ---------------------------------------------------------
    # 3. Merge Price and EPS
    # ---------------------------------------------------------
    df_merged = pd.merge(df_price_hist, df_eps_hist, on=['Date', 'Ticker'], how='outer')
    print(f"Total merged historical records: {len(df_merged)}")
    
    # Cleanup US tickers (AAPL-US -> AAPL)
    df_merged['Ticker'] = df_merged['Ticker'].apply(lambda x: str(x).replace('-US', '').strip())
    # Add dummy/missing columns to match Master DB schema
    df_merged['Name'] = 'Historical'
    df_merged['Sector'] = 'Historical'
    df_merged['Analyst_Count'] = 0
    df_merged['Market_Cap'] = 0
    df_merged['NTM_PER'] = df_merged.apply(lambda row: (row['Price'] / row['NTM_EPS']) if pd.notna(row['Price']) and pd.notna(row['NTM_EPS']) and row['NTM_EPS'] > 0 else 0, axis=1)
    df_merged['Implied_Net_Income'] = 0
    df_merged['Status'] = 'Historical Backfill'
    df_merged['Country'] = df_merged['Ticker'].apply(lambda x: 'KOR' if str(x).endswith('.KS') else 'USA')
    
    df_merged = df_merged[['Date', 'Ticker', 'Name', 'Sector', 'Price', 'Analyst_Count', 'Market_Cap', 'NTM_EPS', 'NTM_PER', 'Implied_Net_Income', 'Status', 'Country']]
    
    # ---------------------------------------------------------
    # 4. Append to Global_NTM_Master_DB.xlsx
    # ---------------------------------------------------------
    print("Appending to Master DB...")
    xls = pd.ExcelFile(DB_FILE)
    df_usa_master = pd.read_excel(xls, sheet_name='USA_Stocks')
    df_kor_master = pd.read_excel(xls, sheet_name='KOR_Stocks')
    
    df_usa_hist = df_merged[df_merged['Country'] == 'USA']
    df_kor_hist = df_merged[df_merged['Country'] == 'KOR']
    
    df_usa_final = pd.concat([df_usa_hist, df_usa_master], ignore_index=True)
    df_kor_final = pd.concat([df_kor_hist, df_kor_master], ignore_index=True)
    
    # Remove duplicate records by date and ticker (preferring master over hist if clash)
    df_usa_final = df_usa_final.drop_duplicates(subset=['Date', 'Ticker'], keep='last')
    df_kor_final = df_kor_final.drop_duplicates(subset=['Date', 'Ticker'], keep='last')
    
    # Sort by Ticker and Date
    df_usa_final = df_usa_final.sort_values(by=['Ticker', 'Date'])
    df_kor_final = df_kor_final.sort_values(by=['Ticker', 'Date'])
    
    # Write back
    with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df_usa_final.to_excel(writer, sheet_name='USA_Stocks', index=False)
        df_kor_final.to_excel(writer, sheet_name='KOR_Stocks', index=False)
        
    print(f"Backfill Complete! Added {len(df_usa_hist)} US records, {len(df_kor_hist)} KOR records.")
    
if __name__ == "__main__":
    main()
