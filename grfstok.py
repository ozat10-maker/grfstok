import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# =========================================================
# ⚙️ חלק 1: הגדרות דף ותשתית האפליקציה
# =========================================================
st.set_page_config(page_title="מנוע ניתוח משולב", layout="wide")
st.title("🎯 מנוע סריקה משולב ומחשבון ניהול סיכונים")
st.write("מערכת חכמה המשלבת ניתוח טכני מהכתבה יחד עם מחשבון ניהול סיכונים אופרטיבי לקבלת החלטות.")

# --- סרגל צדי (Sidebar) ---
st.sidebar.header("💰 הגדרות תקציב וסיכונים")
investment_amount = st.sidebar.number_input("סכום להשקעה פנויה ($):", min_value=100, value=10000, step=500)
risk_percent = st.sidebar.slider("אחוז סיכון מקסימלי מהתיק (%):", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("🔍 בחירת מניות לסריקה")
ticker_1 = st.sidebar.text_input("מניה ראשונה:", value="AAPL").upper()
ticker_2 = st.sidebar.text_input("מניה שנייה:", value="NVDA").upper()

end_date = datetime.today()
start_date = end_date - timedelta(days=365 * 2)

# =========================================================
# 🧠 חלק 2: פונקציות הניתוח והלוגיקה האלגוריתמית
# =========================================================
@st.cache_data(ttl=3600)
def load_stock_data(ticker_symbol, start, end):
    """משיכת נתונים מ-Yahoo Finance עם הגנה מפני שגיאות"""
    try:
        stock_obj = yf.Ticker(ticker_symbol)
        hist_df = stock_obj.history(start=start, end=end)
        info_dict = stock_obj.info
        if hist_df.empty or len(hist_df) < 200:
            return None, None
        return hist_df, info_dict
    except:
        return None, None

def analyze_ticker(df, info, investment_amount, risk_percent):
    """מנוע הניתוח הטכני, הניקוד וניהול הסיכונים"""
    # 1. חישוב ממוצעים נעים (SMA50, SMA200)
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()

    # 2. חישוב מדד RSI (14 ימים)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 3. חישוב רמות פיבונאצ'י שנתיות
    df_last_year = df.iloc[-252:]
    highest_high = df_last_year['High'].max()
    lowest_low = df_last_year['Low'].min()
    price_range = highest_high - lowest_low

    fib_levels = {
        '0.0%': highest_high,
        '23.6%': highest_high - (0.236 * price_range),
        '38.2%': highest_high - (0.382 * price_range),
        '50.0%': highest_high - (0.500 * price_range),
        '61.8%': highest_high - (0.618 * price_range),
        '100.0%': lowest_low
    }

    current_price = df['Close'].iloc[-1]
    current_rsi = df['RSI'].iloc[-1]
    ma200_curr = df['MA200'].iloc[-1]

    # 4. מנוע ניקוד (Score) והחלטה טכנית בשורה התחתונה
    score = 0
    if current_price > ma200_curr:
        score += 1
    else:
        score -= 1

    if current_rsi > 70:
        score -= 2
    elif current_rsi < 30:
        score += 2

    if score >= 2:
        verdict = "🟢 הזדמנות קנייה (Buy)"
    elif score <= -1:
        verdict = "🔴 להמתין לירידה (Wait)"
    else:
        verdict = "🟡 ניטרלי / החזק (Hold)"

    # 5. מציאת רמת התמיכה הקרובה ביותר מתחת למחיר הנוכחי (לפקודת הלימיט)
    waiting_target = fib_levels['61.8%']
    for level_name, level_val in sorted(fib_levels.items(), key=lambda x: x):
        if level_val < current_price:
            waiting_target = level_val

    # 6. מחשבון ניהול סיכונים ותקציב (חוק ה-1%-2% קביעת גודל פוזיציה)
    stop_loss_price = waiting_target * 0.97
    allowed_loss_usd = investment_amount * (risk_percent / 100)
    risk_per_share = current_price - stop_loss_price
    
    if risk_per_share <= 0:
        risk_per_share = current_price * 0.05
        stop_loss_price = current_price * 0.95

    total_shares_to_buy = int(allowed_loss_usd / risk_per_share)
    if (total_shares_to_buy * current_price) > investment_amount:
        total_shares_to_buy = int(investment_amount / current_price)

    # חלוקה אסטרטגית לפיצול קניות (60% מיידי, 40% לימיט בתמיכה)
    shares_p1 = int(total_shares_to_buy * 0.60)
    shares_p2 = total_shares_to_buy - shares_p1

    return {
        "df": df, "info": info, "verdict": verdict, "current_price": current_price,
        "current_rsi": current_rsi, "waiting_target": waiting_target,
        "stop_loss_price": stop_loss_price, "allowed_loss_usd": allowed_loss_usd,
        "total_shares_to_buy": total_shares_to_buy, "shares_p1": shares_p1,
        "shares_p2": shares_p2, "cost_p1": shares_p1 * current_price,
        "cost_p2": shares_p2 * waiting_target
    }

# =========================================================
# 📺 חלק 3: ממשק המשתמש והצגת הנתונים (Streamlit UI)
# =========================================================
with st.spinner('מריץ סריקה וניתוח נתונים במקביל...'):
    df1, info1 = load_stock_data(ticker_1, start_date, end_date)
    df2, info2 = load_stock_data(ticker_2, start_date, end_date)

if not df1 or not df2:
    st.error("שגיאה: אחד או שניים מסימולי המניות אינם תקינים או שחסרים נתונים היסטוריים.")
else:
    # הרצת הניתוח באמצעות הפונקציות המובנות
    res1 = analyze_ticker(df1, info1, investment_amount, risk_percent)
    res2 = analyze_ticker(df2, info2, investment_amount, risk_percent)

    # --- א. טבלת השוואה וסריקה מהירה ---
    st.subheader("📋 לוח סריקה והשוואה מהירה")
    summary_table = {
        "פרמטר": ["שם החברה", "מחיר נוכחי", "מדד מומנטום RSI", "המלצה טכנית", "יעד כניסה/תמיכה"],
        ticker_1: [res1['info'].get('longName', ticker_1), f"${res1['current_price']:.2f}", f"{res1['current_rsi']:.1f}", res1['verdict'], f"${res1['waiting_target']:.2f}"],
        ticker_2: [res2['info'].get('longName', ticker_2), f"${res2['current_price']:.2f}", f"{res2['current_rsi']:.1f}", res2['verdict'], f"${res2['waiting_target']:.2f}"]
    }
    st.table(pd.DataFrame(summary_table).set_index("פרמטר"))

    # --- ב. תצוגת מחשבון ניהול הסיכונים (טאבים) ---
    st.markdown("---")
    st.subheader("🧮 מחשבון ניהול סיכונים והנחיות חלוקת תקציב")
    
    def show_ui_metrics(res, ticker_name):
        col1, col2, col3 = st.columns(3)
        col1.metric("סך מניות מומלץ לקנייה", f"{res['total_shares_to_buy']} יחידות")
        col2.metric("תקציב מנוצל בפועל", f"${(res['cost_p1'] + res['cost_p2']):,.2f}")
        col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
        
        st.markdown(f"""
        🧱 **מתווה פיצול הקניות האופטימלי עבור {ticker_name}:**
        * **שלב א' (כניסה מיידית - 60%):** קנה **{res['shares_p1']}** מניות במחיר נוכחי (**${res['current_price']:.2f}**). שווי: `${res['cost_p1']:,.2f}`.
        * **שלב B' (המתנה לירידה - 40%):** הגדר פקודת Limit של **{res['shares_p2']}** מניות בתמיכה (**${res['waiting_target']:.2f}**). שווי: `${res['cost_p2']:,.2f}`.
        * **⚠️ רמת בטיחות:** יציאה בתוך הפסד ב-**${res['stop_loss_price']:.2f}**. סיכון תיק מוגן על: `${res['allowed_loss_usd']:.2f}`.
        """)

    t1, t2 = st.tabs([f"💰 תוכנית מסחר {ticker_1}", f"💰 תוכנית מסחר {ticker_2}"])
    with t1: show_ui_metrics(res1, ticker_1)
    with t2: show_ui_metrics(res2, ticker_2)

    # --- ג. גרפים טכניים בתחתית הדף ---
    st.markdown("---")
    st.subheader("📉 גרפים טכניים להרחבה ומעקב")
    
    def plot_graph(res):
        df = res['df']
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='orange', width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='red', width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.2)), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=350, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    cg1, cg2 = st.columns(2)
    with cg1: plot_graph(res1)
    with cg2: plot_graph(res2)
