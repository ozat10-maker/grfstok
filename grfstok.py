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
st.title("🎯 מנוע ניתוח טכני ומחשבון ניהול סיכונים")
st.write("המערכת מנתחת מניה בודדת או משווה בין שתיים, ומפיקה תוכנית מסחר מוגדרת סיכונים.")

# --- סרגל צדי (Sidebar) ---
st.sidebar.header("💰 הגדרות תקציב וסיכונים")
investment_amount = st.sidebar.number_input("סכום להשקעה פנויה ($):", min_value=100, value=10000, step=500)
risk_percent = st.sidebar.slider("אחוז סיכון מקסימלי מהתיק (%):", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("🔍 בחירת מניות לסריקה")
ticker_1 = st.sidebar.text_input("מניה ראשונה (חובה):", value="AAPL").upper().strip()
ticker_2 = st.sidebar.text_input("מניה שנייה (אופציונלי - השאר ריק למניה בודדת):", value="").upper().strip()

end_date = datetime.today()
start_date = end_date - timedelta(days=365 * 2)

# =========================================================
# 🧠 חלק 2: פונקציות הניתוח והלוגיקה האלגוריתמית
# =========================================================
def load_stock_data(ticker_symbol, start, end):
    """משיכת נתונים מ-Yahoo Finance עם הגנה מפני שגיאות"""
    if not ticker_symbol:
        return pd.DataFrame(), {}
    try:
        stock_obj = yf.Ticker(ticker_symbol)
        hist_df = stock_obj.history(start=start, end=end)
        info_dict = stock_obj.info
        return hist_df, info_dict
    except:
        return pd.DataFrame(), {}

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
        verdict_type = "BUY"
    elif score <= -1:
        verdict = "🔴 להמתין לירידה (Wait)"
        verdict_type = "WAIT"
    else:
        verdict = "🟡 ניטרלי / החזק (Hold)"
        verdict_type = "HOLD"

    # 5. מציאת רמת התמיכה הקרובה ביותר מתחת למחיר הנוכחי (לפקודת הלימיט)
    waiting_target = fib_levels['61.8%']
    for level_name, level_val in sorted(fib_levels.items(), key=lambda x: x):
        if level_val < current_price:
            waiting_target = level_val

    # 6. מחשבון ניהול סיכונים ותקציב
    stop_loss_price = waiting_target * 0.97
    allowed_loss_usd = investment_amount * (risk_percent / 100)
    risk_per_share = current_price - stop_loss_price
    
    if risk_per_share <= 0:
        risk_per_share = current_price * 0.05
        stop_loss_price = current_price * 0.95

    total_shares_to_buy = int(allowed_loss_usd / risk_per_share)
    if (total_shares_to_buy * current_price) > investment_amount:
        total_shares_to_buy = int(investment_amount / current_price)

    # חלוקה אסטרטגית לפיצול קניות (משתנה דינמית לפי ה-Verdict)
    shares_p1 = int(total_shares_to_buy * 0.60)
    shares_p2 = total_shares_to_buy - shares_p1

    return {
        "df": df, "info": info, "verdict": verdict, "verdict_type": verdict_type,
        "current_price": current_price, "current_rsi": current_rsi, "waiting_target": waiting_target,
        "stop_loss_price": stop_loss_price, "allowed_loss_usd": allowed_loss_usd,
        "total_shares_to_buy": total_shares_to_buy, "shares_p1": shares_p1,
        "shares_p2": shares_p2, "cost_p1": shares_p1 * current_price,
        "cost_p2": shares_p2 * waiting_target
    }
# =========================================================
# 📺 חלק 3: ממשק המשתמש והצגת הנתונים (Streamlit UI)
# =========================================================
if not ticker_1:
    st.warning("אנא הזן סימול מניה בשדה החובה בסרגל הצדי.")
else:
    with st.spinner('מנתח נתוני שוק בשרת...'):
        df1, info1 = load_stock_data(ticker_1, start_date, end_date)
        df2, info2 = load_stock_data(ticker_2, start_date, end_date) if ticker_2 else (pd.DataFrame(), {})

    # בדיקת תקינות למניה הראשונה (חובה)
    if df1.empty or len(df1) < 200:
        st.error(f"שגיאה: סימול המניה {ticker_1} אינו תקין או שחסרים נתונים היסטוריים מספיקים בשרת.")
    else:
        res1 = analyze_ticker(df1, info1, investment_amount, risk_percent)
        has_second_stock = not df2.empty and len(df2) >= 200
        
        if has_second_stock:
            res2 = analyze_ticker(df2, info2, investment_amount, risk_percent)

        # --- א. תצוגת טבלת השוואה (רק אם יש שתי מניות) ---
        if has_second_stock:
            st.subheader("📋 לוח סריקה והשוואה מהירה")
            summary_table = {
                "פרמטר": ["שם החברה", "מחיר נוכחי", "מדד מומנטום RSI", "המלצה טכנית", "יעד כניסה/תמיכה"],
                ticker_1: [res1['info'].get('longName', ticker_1), f"${res1['current_price']:.2f}", f"{res1['current_rsi']:.1f}", res1['verdict'], f"${res1['waiting_target']:.2f}"],
                ticker_2: [res2['info'].get('longName', ticker_2), f"${res2['current_price']:.2f}", f"{res2['current_rsi']:.1f}", res2['verdict'], f"${res2['waiting_target']:.2f}"]
            }
            st.table(pd.DataFrame(summary_table).set_index("פרמטר"))
        else:
            # תצוגת כותרת קומפקטית למניה בודדת
            st.subheader(f"📊 דוח ניתוח ממוקד: {res1['info'].get('longName', ticker_1)} ({ticker_1})")
            c1, c2, c3 = st.columns(3)
            c1.metric("מחיר נוכחי", f"${res1['current_price']:.2f}")
            c2.metric("מדד RSI", f"{res1['current_rsi']:.1f}")
            c3.metric("סטטוס מערכת", res1['verdict'])

        # --- ב. תצוגת מחשבון ניהול הסיכונים (טאבים או תצוגה ישירה) ---
        st.markdown("---")
        st.subheader("🧮 מחשבון ניהול סיכונים והנחיות פעולה לתקציב")
        
        def show_ui_metrics(res, ticker_name):
            col1, col2, col3 = st.columns(3)
            
            # אם הסטטוס הוא להמתין, כמות המניות המיידית צריכה להיות 0
            if res['verdict_type'] == "WAIT":
                col1.metric("סך מניות לקנייה מיידית", "0 יחידות")
                col2.metric("תקציב מנוצל כרגע", "$0.00")
                col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
                
                st.error(f"🛑 **אסטרטגיית פעולה ל-{ticker_name} (להמתין לירידה):**")
                st.markdown(f"""
                * **אין לבצע קנייה במחיר השוק הנוכחי (${res['current_price']:.2f}).** הנכס נמצא כרגע בסיכון גבוה או קניית יתר.
                * **פקודת לימיט עתידית (Limit Order):** מומלץ למקם פקודת רכש עבור **{res['total_shares_to_buy']}** יחידות רק כשהמחיר ירד לרמת התמיכה ב-**${res['waiting_target']:.2f}**.
                * **שווי העסקה הכולל המתוכנן:** `${(res['total_shares_to_buy'] * res['waiting_target']):,.2f}`.
                * **ניהול סיכונים:** במידה והפקודה תתממש והמחיר ימשיך לקרוס מתחת ל-**${res['stop_loss_price']:.2f}**, יש להפעיל סטופ לוס.
                """)
                
            elif res['verdict_type'] == "HOLD":
                col1.metric("סך מניות מומלץ (פוזיציית בסיס)", f"{res['shares_p1']} יחידות")
                col2.metric("תקציב מנוצל ראשוני", f"${res['cost_p1']:,.2f}")
                col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
                
                st.warning(f"🟡 **אסטרטגיית פעולה ל-{ticker_name} (מצב ניטרלי/דשדוש):**")
                st.markdown(f"""
                * המצב בשוק דורש משנה זהירות. אם בכל זאת ברצונך להיכנס, מומלץ לפצל פוזיציה בזהירות:
                * **שלב א' (כניסה חלקית מיידית):** קנה רק **{res['shares_p1']}** יחידות במחיר הנוכחי (**${res['current_price']:.2f}**).
                * **שלב ב' (המתנה לתמיכה):** שים פקודת לימיט ל-**{res['shares_p2']}** היחידות הנותרות בקו התמיכה (**${res['waiting_target']:.2f}**).
                """)
                
            else: # BUY
                col1.metric("סך מניות מומלץ לקנייה", f"{res['total_shares_to_buy']} יחידות")
                col2.metric("תקציב מנוצל בפועל", f"${(res['cost_p1'] + res['cost_p2']):,.2f}")
                col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
                
                st.success(f"🟢 **אסטרטגיית פעולה ל-{ticker_name} (אות קנייה):**")
                st.markdown(f"""
                * הפרמטרים תומכים בכניסה לעסקה. ניתן לבצע רכישה מפוצלת או מלאה:
                * **שלב א' (כניסה מיידית):** קנה **{res['shares_p1']}** מניות במחיר נוכחי (**${res['current_price']:.2f}**).
                * **שלב ב' (חיזוק בתמיכה):** הצב פקודת לימיט ל-**{res['shares_p2']}** מניות בשער **${res['waiting_target']:.2f}**.
                """)

        if has_second_stock:
            t1, t2 = st.tabs([f"💰 תוכנית מסחר {ticker_1}", f"💰 תוכנית מסחר {ticker_2}"])
            with t1: show_ui_metrics(res1, ticker_1)
            with t2: show_ui_metrics(res2, ticker_2)
        else:
            show_ui_metrics(res1, ticker_1)

        # --- ג. גרפים טכניים בתחתית הדף ---
        st.markdown("---")
        st.subheader("📉 גרפים טכניים ומעקב מגמות")
        
        def plot_graph(res):
            df = res['df']
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='orange', width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='red', width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.2)), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=380, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        if has_second_stock:
            cg1, cg2 = st.columns(2)
            with cg1: 
                st.caption(f"גרף {ticker_1}")
                plot_graph(res1)
            with cg2: 
                st.caption(f"גרף {ticker_2}")
                plot_graph(res2)
        else:
            plot_graph(res1)
