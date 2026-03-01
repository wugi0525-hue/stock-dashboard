import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_excel('Global_NTM_Master_DB.xlsx', sheet_name='EPS_Trend')
print(df.head(10).to_string())
