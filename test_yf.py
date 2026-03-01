import yfinance as yf

for ticker in ['005930.KS', '000660.KS']:
    print(f"Testing {ticker}")
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        print("currentPrice:", info.get('currentPrice'))
        print("marketCap:", info.get('marketCap'))
        print("forwardEps:", info.get('forwardEps'))
        
        estimates = tk.earnings_estimate
        if estimates is not None and not estimates.empty:
            print("Estimates:")
            print(estimates)
        else:
            print("No earnings estimates.")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)
