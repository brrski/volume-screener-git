import streamlit as st
import yfinance as yf
import pandas as pd

# --- Configuration ---
st.set_page_config(page_title="Stock Volume Screener", layout="wide")

st.title("📊 Real-Time Volume Spike Screener")
st.markdown("""
This app monitors a list of stocks for **unusual volume activity**. 
It calculates **Relative Volume (RVol)** by comparing the current volume 
to the 20-day average.
""")

# --- Sidebar: User Inputs ---
st.sidebar.header("Settings")

# Default list from your request 
default_tickers = "AMD, NVDA, CRWV, APLD, SNDK, MU, TSLA, GOOG, META, SPY"
ticker_input = st.sidebar.text_area("Ticker List (comma separated)", default_tickers, height=150)

# Parse tickers
tickers = [x.strip().upper() for x in ticker_input.split(",") if x.strip()]

# Threshold for highlighting
vol_threshold = st.sidebar.slider("Highlight RVol Threshold", 1.0, 5.0, 1.5, 0.1)

# --- Data Fetching Function ---
@st.cache_data(ttl=60) # Cache data for 1 min to prevent spamming Yahoo
def get_volume_data(ticker_list):
    data = []
    
    # Download batch data (3 months to get good averages)
    # auto_adjust=True fixes issues with splits/dividends
    try:
        df = yf.download(ticker_list, period="3mo", group_by='ticker', progress=False, auto_adjust=True)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

    for ticker in ticker_list:
        try:
            # Handle cases where yfinance returns MultiIndex or Single Index
            if len(ticker_list) > 1:
                stock_df = df[ticker]
            else:
                stock_df = df
            
            # clean data
            stock_df = stock_df.dropna(how='all')
            
            if stock_df.empty:
                continue

            # Get latest day and volume
            latest_day = stock_df.iloc[-1]
            current_vol = latest_day['Volume']
            current_price = latest_day['Close']
            
            # Calculate 20-Day Average Volume (excluding today to be accurate)
            # We take the last 21 days, exclude the last row (current partial day), then average
            avg_vol_20d = stock_df['Volume'].iloc[-21:-1].mean()
            
            # Calculate Relative Volume (RVol)
            if avg_vol_20d > 0:
                rvol = current_vol / avg_vol_20d
            else:
                rvol = 0

            # Price Change %
            prev_close = stock_df['Close'].iloc[-2]
            pct_change = ((current_price - prev_close) / prev_close) * 100

            data.append({
                "Ticker": ticker,
                "Price": current_price,
                "Change %": pct_change,
                "Current Vol": current_vol,
                "Avg Vol (20D)": avg_vol_20d,
                "RVol": rvol
            })
            
        except KeyError:
            # Ticker might be delisted or erroneous
            continue

    return pd.DataFrame(data)

# --- Main App Logic ---

if st.button("Refresh Data"):
    st.cache_data.clear() # Clear cache to force new download

if tickers:
    with st.spinner('Fetching volume data...'):
        results = get_volume_data(tickers)

    if not results.empty:
        # Sort by Relative Volume (Descending) so spikes appear at top
        results = results.sort_values(by="RVol", ascending=False)

        # Formatting for display
        def highlight_spike(val):
            color = 'lightgreen' if val > vol_threshold else 'white'
            if val > vol_threshold * 2: color = '#ffcccb' # Red highlight for massive spikes
            return f'background-color: {color}; color: black'

        # Create display dataframe
        display_df = results.copy()
        
        # Apply formatting
        st.subheader(f"Top Volume Spikes (Threshold: >{vol_threshold}x)")
        
        # Use Streamlit's dataframe display which allows sorting/interaction
        st.dataframe(
            display_df.style.map(highlight_spike, subset=['RVol'])
            .format({
                "Price": "${:.2f}",
                "Change %": "{:+.2f}%",
                "Current Vol": "{:,.0f}",
                "Avg Vol (20D)": "{:,.0f}",
                "RVol": "{:.2f}x"
            }),
            use_container_width=True,
            height=500
        )
    else:
        st.warning("No data found. Please check ticker symbols.")
else:
    st.info("Enter tickers in the sidebar to begin.")
