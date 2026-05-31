import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# הגדרת תצורת הדף ב-Streamlit למסך רחב
st.set_page_config(page_title="מערכת ניתוח טכני", layout="wide", initial_sidebar_state="expanded")

st.title("📈 מערכת לניתוח טכני ונתוני מניות")
st.write("ברוכים הבאים לאפליקציה שלכם. כאן נתחיל לייבא נתונים ולנתח אותם בהמשך.")

# --- סרגל צדי (Sidebar) לבחירת המשתמש ---
st.sidebar.header("הגדרות חיפוש")

# 1. תיבת טקסט להזנת טיקר המניה (למשל: AAPL, TSLA, MSFT)
ticker = st.sidebar.text_input("הכנס סימול מניה (Ticker):", value="AAPL").upper()

# 2. בחירת טווח זמנים מוגדר מראש לגרף
time_options = {
    "חודש אחרון": 30,
    "3 חודשים אחרונים": 90,
    "חצי שנה אחרונה": 180,
    "שנה אחרונה": 365,
    "3 שנים אחרונות": 365 * 3
}
selected_time_label = st.sidebar.selectbox("בחר טווח זמנים לגרף:", list(time_options.keys()), index=3)
days_back = time_options[selected_time_label]

# חישוב תאריכי התחלה וסיום
end_date = datetime.today()
start_date = end_date - timedelta(days=days_back)

# --- משיכת הנתונים באמצעות yfinance ---
@st.cache_data(ttl=3600)  # שמירה בזיכרון מטמון למשך שעה כדי למנוע קריאות כפולות ואיטיות
def load_stock_data(ticker_symbol, start, end):
    stock_obj = yf.Ticker(ticker_symbol)
    # משיכת נתוני מחיר היסטוריים (DataFrame)
    hist_df = stock_obj.history(start=start, end=end)
    # משיכת מידע כללי על החברה (Dictionary)
    info_dict = stock_obj.info
    return hist_df, info_dict

try:
    with st.spinner('מושך נתונים מ-Yahoo Finance...'):
        df, info = load_stock_data(ticker, start_date, end_date)

    if df.empty:
        st.error(f"לא נמצאו נתונים עבור הסימול {ticker}. אנא ודא שהקשבת סימול נכון (למשל: NVDA).")
    else:
        # --- חלק א': הצגת מידע כללי על המניה ---
        company_name = info.get('longName', ticker)
        sector = info.get('sector', 'לא צוין')
        industry = info.get('industry', 'לא צוין')
        
        st.subheader(f"🏢 {company_name} ({ticker})")
        st.caption(f"סרקטור: {sector} | תעשייה: {industry}")
        
        # כרטיסי מידע מהיר (Metrics)
        current_price = info.get('currentPrice', df['Close'].iloc[-1])
        prev_close = info.get('previousClose', df['Close'].iloc[-2] if len(df) > 1 else current_price)
        price_change = current_price - prev_close
        price_change_pct = (price_change / prev_close) * 100
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("מחיר נוכחי", f"${current_price:,.2f}", f"{price_change_pct:+.2f}%")
        col2.metric("שווי שוק", f"${info.get('marketCap', 0):,}")
        col3.metric("מכפיל רווח (P/E)", f"{info.get('trailingPE', 'N/A')}")
        col4.metric("מחזור מסחר ממוצע", f"{info.get('averageVolume', 0):,}")

        # --- חלק ב': הצגת הגרף הטכני (נרות יפניים) ---
        st.subheader("📊 גרף מחיר היסטורי אינטראקטיבי")
        
        fig = go.Figure()
        
        # הוספת נרות יפניים לגרף
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=ticker
        ))
        
        # עיצוב חלון הגרף והסרת סליידר הזמן התחתון המובנה (לשיפור הנראות)
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            template="plotly_dark",  # מראה כהה ומקצועי שמתאים לגרפים
            margin=dict(l=10, r=10, t=20, b=20),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- חלק ג': נתונים פונדמנטליים מורחבים בתחתית ---
        with st.expander("📄 לחץ לצפייה בתיאור החברה ונתונים מורחבים"):
            st.write("**תיאור העסק:**")
            st.write(info.get('longBusinessSummary', 'אין תיאור זמין.'))
            
            # הצגת טבלת הנתונים הגולמיים במידה והמשתמש רוצה לחקור אותה
            st.write("**טבלת המחירים ההיסטורית (נתונים גולמיים):**")
            st.dataframe(df.tail(10))

except Exception as e:
    st.error(f"התרחשה שגיאה בטעינת הנתונים: {e}")
    st.info("טיפ: ודא שיש לך חיבור אינטרנט תקין ושסימול המניה נכון.")
