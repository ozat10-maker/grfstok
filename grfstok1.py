import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =========================================================
# ⚙️ חלק 1: הגדרות דף ותשתית האפליקציה
# =========================================================
st.set_page_config(page_title="מנוע ניתוח משולב", layout="wide")
st.title("🎯 מנוע ניתוח טכני ומחשבון ניהול סיכונים")
st.write("המערכת מנתחת מניה בודדת או משווה בין שתיים, ומפיקה תוכנית מסחר המבוססת על רצועות בולינגר ותבניות נרות.")

# --- סרגל צדי (Sidebar) ---
st.sidebar.header("👤 פרופיל משקיע ורמת סיכון")
risk_profile = st.sidebar.selectbox(
    "בחר את רמת הסיכון המתאימה לך:",
    ["סולידי (Conservative)", "מאוזן (Moderate)", "אגרסיבי (Aggressive)"],
    index=1
)

st.sidebar.markdown("---")
st.sidebar.header("💰 הגדרות תקציב וסיכונים")
investment_amount = st.sidebar.number_input("סכום להשקעה פנויה ($):", min_value=100, value=10000, step=500)
risk_percent = st.sidebar.slider("אחוז סיכון מקסימלי מהתיק (%):", min_value=0.5, max_value=5.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.header("💼 תיק ההשקעות הנוכחי שלך (אופציונלי)")
portfolio_input = st.sidebar.text_input("הזן מניות וכמויות (למשל: AAPL:10, NVDA:5):", value="")

st.sidebar.markdown("---")
st.sidebar.header("🔍 בחירת מניות לסריקה")
ticker_1 = st.sidebar.text_input("מניה ראשונה (חובה):", value="AAPL").upper().strip()
ticker_2 = st.sidebar.text_input("מניה שנייה (אופציונלי):", value="").upper().strip()

end_date = datetime.today()
start_date = end_date - timedelta(days=365 * 2)

# =========================================================
# 🧠 חלק 2: פונקציות הניתוח והלוגיקה האלגוריתמית
# =========================================================
def load_stock_data(ticker_symbol, start, end):
    """משיכת נתונים מ-Yahoo Finance עם הגנה מפני שגיאות והתאמת ספליטים"""
    if not ticker_symbol:
        return pd.DataFrame(), {}
    try:
        stock_obj = yf.Ticker(ticker_symbol)
        hist_df = stock_obj.history(start=start, end=end, auto_adjust=True)
        info_dict = stock_obj.info
        return hist_df, info_dict
    except:
        return pd.DataFrame(), {}

def parse_portfolio(portfolio_str):
    """תרגום מחרוזת הטקסט של התיק למילון פייתון קריא"""
    portfolio = {}
    if not portfolio_str:
        return portfolio
    try:
        parts = portfolio_str.split(",")
        for part in parts:
            if ":" in part:
                tick, qty = part.split(":")
                portfolio[tick.upper().strip()] = float(qty.strip())
    except:
        st.sidebar.error("פורמט הזנת התיק שגוי. השתמש בפורמט TICKER:QTY")
    return portfolio

def calculate_portfolio_value(portfolio):
    """חישוב השווי הכולל של התיק הקיים בזמן אמת"""
    total_val = 0.0
    shares_values = {}
    for tick, qty in portfolio.items():
        df, _ = load_stock_data(tick, datetime.today() - timedelta(days=5), datetime.today())
        if not df.empty:
            price = df['Close'].iloc[-1]
            current_value = price * qty
            total_val += current_value
            shares_values[tick] = current_value
    return total_val, shares_values

def analyze_ticker(df, info, investment_amount, risk_percent, ticker_name, portfolio_total_value, current_holding_value, selected_risk_profile):
    """מנוע הניתוח הטכני המשודרג הכולל רצועות בולינגר וזיהוי תבניות נרות יפניים"""
    # 1. חישוב אינדיקטורים קלאסיים (ממוצעים ו-RSI)
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 2. חישוב רצועות בולינגר (Bollinger Bands - 20 יום, 2 סטיות תקן)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])

    # 3. זיהוי מתמטי של תבניות נרות (עבור הנר האחרון בגרף)
    open_p = df['Open'].iloc[-1]
    high_p = df['High'].iloc[-1]
    low_p = df['Low'].iloc[-1]
    close_p = df['Close'].iloc[-1]
    
    body_size = abs(close_p - open_p)
    total_range = high_p - low_p if (high_p - low_p) > 0 else 0.01
    lower_shade = (open_p - low_p) if close_p >= open_p else (close_p - low_p)
    upper_shade = (high_p - close_p) if close_p >= open_p else (high_p - open_p)

    is_doji = body_size <= (total_range * 0.10)
    is_hammer = (lower_shade >= (body_size * 2)) and (upper_shade <= (body_size * 0.5))

    # 4. חישוב רמות פיבונאצ'י
    df_last_year = df.iloc[-252:]
    highest_high = df_last_year['High'].max()
    lowest_low = df_last_year['Low'].min()
    price_range = highest_high - lowest_low
    fib_618 = highest_high - (0.618 * price_range)

    current_price = df['Close'].iloc[-1]
    current_rsi = df['RSI'].iloc[-1]
    ma50_curr = df['MA50'].iloc[-1]
    ma200_curr = df['MA200'].iloc[-1]
    bb_lower_curr = df['BB_Lower'].iloc[-1]
    bb_upper_curr = df['BB_Upper'].iloc[-1]

    analysis_reasons = []
    score = 0
    
    # שיקולי מגמה ומומנטום
    if current_price > ma200_curr:
        score += 1
        analysis_reasons.append(f"המניה במגמה ראשית עולה (מעל ממוצע נע 200 השוכן ב-${ma200_curr:.2f}).")
    else:
        score -= 1
        analysis_reasons.append(f"המניה במגמת ירידה ארוכת טווח (מתחת לממוצע נע 200 השוכן ב-${ma200_curr:.2f}).")

    if current_rsi > 70:
        score -= 2
        analysis_reasons.append(f"מדד ה-RSI עומד על {current_rsi:.1f} - מצב קניית-יתר.")
    elif current_rsi < 30:
        score += 2
        analysis_reasons.append(f"מדד ה-RSI עומד על {current_rsi:.1f} - מצב מכירת-יתר.")

    # 🛑 שילוב רצועות בולינגר ותבניות נרות במנוע הניקוד
    candle_pattern_detected = "אין תבנית מיוחדת"
    if current_price <= (bb_lower_curr * 1.02):
        score += 1
        analysis_reasons.append(f"המחיר קרוב מאוד לרצועת בולינגר התחתונה (${bb_lower_curr:.2f}), מה שמסמן רמת מחיר זולה סטטיסטית.")
        if is_hammer:
            score += 2
            candle_pattern_detected = "🔨 נר פטיש שורי (Hammer) על רצועת בולינגר התחתונה"
            analysis_reasons.append("🔥 איתות חזק: זוהה נר פטיש (Hammer) שורי על רצועת בולינגר התחתונה, המעיד על היפוך מגמה קרוב כלפי מעלה.")
        elif is_doji:
            score += 1
            candle_pattern_detected = "⭐ נר דוג'י (Doji) על רצועת בולינגר התחתונה"
            analysis_reasons.append("זוהה נר דוג'י (Doji) ברמת שפל, המעיד על בלימת לחץ המוכרים והתעוררות מאבק קונים.")
    elif current_price >= (bb_upper_curr * 0.98):
        score -= 1
        analysis_reasons.append(f"המחיר הגיע לרצועת בולינגר העליונה (${bb_upper_curr:.2f}), נחשב ליקר סטטיסטית בטווח הקצר.")
    else:
        if is_hammer: candle_pattern_detected = "נר פטיש (Hammer) באמצע הטווח"
        elif is_doji: candle_pattern_detected = "נר דוג'י (Doji) באמצע הטווח"

    # שיקולי חשיפת יתר בתיק
    total_capital = investment_amount + portfolio_total_value
    exposure_warning = False
    exposure_factor = 1.0
    if total_capital > 0:
        current_exposure_pct = (current_holding_value / total_capital) * 100
        if current_exposure_pct > 25.0:
            score -= 1
            exposure_warning = True
            exposure_factor = 0.5
            analysis_reasons.append("נמצאה חשיפת יתר של מניה זו בתיק שלך (מעל 25%), כמויות הקנייה הופחתו.")

    # קביעת סף לפי פרופיל סיכון
    if "סולידי" in selected_risk_profile:
        buy_threshold, sl_multiplier = 2, 0.98
    elif "אגרסיבי" in selected_risk_profile:
        buy_threshold, sl_multiplier = 0, 0.94
    else:
        buy_threshold, sl_multiplier = 1, 0.96

    if score >= buy_threshold:
        verdict, verdict_type = "🟢 הזדמנות קנייה (Buy)", "BUY"
    elif score < 0:
        verdict, verdict_type = "🔴 להמתין לירידה (Wait)", "WAIT"
    else:
        verdict, verdict_type = "🟡 ניטרלי / החזק (Hold)", "HOLD"

    # קביעת יעד המתנה
    waiting_target = bb_lower_curr if pd.notna(bb_lower_curr) else current_price * 0.95
    if (current_price - waiting_target) / current_price > 0.20 and pd.notna(ma50_curr):
        waiting_target = ma50_curr
        analysis_reasons.append(f"התמיכה הטכנית הריאלית נקבעה על ממוצע נע 50 (${ma50_curr:.2f}).")

    stop_loss_price = waiting_target * sl_multiplier
    allowed_loss_usd = investment_amount * (risk_percent / 100)
    risk_per_share = current_price - stop_loss_price
    if risk_per_share <= 0:
        risk_per_share = current_price * 0.05
        stop_loss_price = current_price * 0.95

    total_shares_to_buy = int((allowed_loss_usd / risk_per_share) * exposure_factor)
    if (total_shares_to_buy * current_price) > investment_amount:
        total_shares_to_buy = int(investment_amount / current_price)

    shares_p1 = int(total_shares_to_buy * 0.60)
    shares_p2 = total_shares_to_buy - shares_p1

    return {
        "df": df, "info": info, "verdict": verdict, "verdict_type": verdict_type,
        "current_price": current_price, "current_rsi": current_rsi, "waiting_target": waiting_target,
        "stop_loss_price": stop_loss_price, "allowed_loss_usd": allowed_loss_usd,
        "total_shares_to_buy": total_shares_to_buy, "shares_p1": shares_p1,
        "shares_p2": shares_p2, "cost_p1": shares_p1 * current_price,
        "cost_p2": shares_p2 * waiting_target, "exposure_warning": exposure_warning,
        "analysis_reasons": analysis_reasons, "candle_pattern": candle_pattern_detected
    }
# =========================================================
# 📺 חלק 3: ממשק המשתמש והצגת הנתונים (Streamlit UI)
# =========================================================
user_portfolio = parse_portfolio(portfolio_input)
portfolio_val = 0.0
holdings_distribution = {}

if user_portfolio:
    with st.spinner('מחשב את ערך תיק ההשקעות הקיים שלך...'):
        portfolio_val, holdings_distribution = calculate_portfolio_value(user_portfolio)
    st.info(f"💼 שווי תיק המניות הנוכחי שלך בענן: **${portfolio_val:,.2f}**")

if not ticker_1:
    st.warning("אנא הזן סימול מניה בשדה החובה בסרגל הצדי.")
else:
    with st.spinner('מנתח נתוני שוק בשרת...'):
        df1, info1 = load_stock_data(ticker_1, start_date, end_date)
        df2, info2 = load_stock_data(ticker_2, start_date, end_date) if ticker_2 else (pd.DataFrame(), {})

    if df1.empty or len(df1) < 200:
        st.error(f"שגיאה: סימול המניה {ticker_1} אינו תקין או שאין מספיק נתונים היסטוריים.")
    else:
        val_held_1 = holdings_distribution.get(ticker_1, 0.0)
        res1 = analyze_ticker(df1, info1, investment_amount, risk_percent, ticker_1, portfolio_val, val_held_1, risk_profile)
        
        has_second_stock = not df2.empty and len(df2) >= 200
        if has_second_stock:
            val_held_2 = holdings_distribution.get(ticker_2, 0.0)
            res2 = analyze_ticker(df2, info2, investment_amount, risk_percent, ticker_2, portfolio_val, val_held_2, risk_profile)

        # --- א. טבלת השוואה מהירה ---
        if has_second_stock:
            st.subheader("📋 לוח סריקה והשוואה מהירה")
            summary_table = {
                "פרמטר": ["שם החברה", "מחיר נוכחי", "תבנית נר", "המלצה טכנית", "יעד כניסה/תמיכה"],
                ticker_1: [res1['info'].get('longName', ticker_1), f"${res1['current_price']:.2f}", res1['candle_pattern'], res1['verdict'], f"${res1['waiting_target']:.2f}"],
                ticker_2: [res2['info'].get('longName', ticker_2), f"${res2['current_price']:.2f}", res2['candle_pattern'], res2['verdict'], f"${res2['waiting_target']:.2f}"]
            }
            st.table(pd.DataFrame(summary_table).set_index("פרמטר"))
        else:
            st.subheader(f"📊 דוח ניתוח ממוקד: {res1['info'].get('longName', ticker_1)} ({ticker_1})")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("מחיר נוכחי", f"${res1['current_price']:.2f}")
            c2.metric("מדד RSI", f"{res1['current_rsi']:.1f}")
            c3.metric("תבנית נר שזוהתה", res1['candle_pattern'])
            c4.metric("סטטוס מערכת", res1['verdict'])

        if res1['exposure_warning']:
            st.warning(f"⚠️ **שים לב חשיפת יתר!** מניית {ticker_1} תופסת נתח משמעותי מתיק ההשקעות שלך.")

        # --- ב. סיכום תהליך הניתוח ---
        st.write("### 📝 סיכום תהליך הניתוח והממצאים הטכניים")
        st.write(f"הדוח מותאם אישית עבור פרופיל משקיע: **{risk_profile}**.")
        for reason in res1['analysis_reasons']: st.write(f"🔹 {reason}")
        if has_second_stock:
            st.write(f"**עבור מניית {ticker_2}:**")
            for reason in res2['analysis_reasons']: st.write(f"🔹 {reason}")

        # --- ג. תצוגת מחשבון ניהול הסיכונים ---
        st.markdown("---")
        st.subheader("🧮 מחשבון ניהול סיכונים והנחיות פעולה לתקציב")
        
        def show_ui_metrics(res, ticker_name):
            col1, col2, col3 = st.columns(3)
            if res['verdict_type'] == "WAIT":
                col1.metric("סך מניות לקנייה מיידית", "0 יחידות")
                col2.metric("תקציב מנוצל כרגע", "$0.00")
                col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
                st.error(f"🛑 **אסטרטגיית פעולה ל-{ticker_name} (להמתין לירידה):**")
                st.markdown(f"* **אין לבצע קנייה במחיר השוק הנוכחי (${res['current_price']:.2f}).**\n* **פקודת לימיט עתידית:** מומלץ למקם פקודת רכש עבור **{res['total_shares_to_buy']}** יחידות ברמת התמיכה/בולינגר תחתון ב-**${res['waiting_target']:.2f}**.")
            elif res['verdict_type'] == "HOLD":
                col1.metric("סך מניות מומלץ", f"{res['shares_p1']} יחידות")
                col2.metric("תקציב מנוצל ראשוני", f"${res['cost_p1']:,.2f}")
                col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
                st.warning(f"🟡 **אסטרטגיית פעולה ל-{ticker_name} (מצב ניטרלי/דשדוש):**")
                st.markdown(f"* **שלב א':** קנה רק **{res['shares_p1']}** יחידות במחיר הנוכחי (**${res['current_price']:.2f}**).\n* **שלב ב':** שים פקודת לימיט ל-**{res['shares_p2']}** יחידות בקו התמיכה (**${res['waiting_target']:.2f}**).")
            else: # BUY
                col1.metric("סך מניות מומלץ לקנייה", f"{res['total_shares_to_buy']} יחידות")
                col2.metric("תקציב מנוצל בפועל", f"${(res['cost_p1'] + res['cost_p2']):,.2f}")
                col3.metric("מחיר קטיעת הפסד (Stop Loss)", f"${res['stop_loss_price']:.2f}")
                st.success(f"🟢 **אסטרטגיית פעולה ל-{ticker_name} (אות קנייה):**")
                st.markdown(f"* **שלב א' (כניסה מיידית):** קנה **{res['shares_p1']}** מניות במחיר נוכחי (**${res['current_price']:.2f}**).\n* **שלב ב' (חיזוק בתמיכה):** הצב פקודת לימיט ל-**{res['shares_p2']}** מניות בשער **${res['waiting_target']:.2f}**.")

        if has_second_stock:
            t1, t2 = st.tabs([f"💰 תוכנית מסחר {ticker_1}", f"💰 תוכנית מסחר {ticker_2}"])
            with t1: show_ui_metrics(res1, ticker_1)
            with t2: show_ui_metrics(res2, ticker_2)
        else:
            show_ui_metrics(res1, ticker_1)

        # --- ד. גרפים טכניים בתחתית הדף ---
        st.markdown("---")
        st.subheader("📉 גרפים טכניים ומעקב מגמות")
        
        def plot_graph(res):
            df = res['df']
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.7, 0.3])
            # הוספת נרות
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
            # הוספת רצועות בולינגר לגרף העליון
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='rgba(173,216,230,0.4)', width=1, dash='dash'), name="בולינגר עליון"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='rgba(173,216,230,0.4)', width=1, dash='dash'), name="בולינגר תחתון"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Middle'], line=dict(color='cyan', width=1), name="בולינגר אמצע"), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='red', width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.2)), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=350, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        if has_second_stock:
            cg1, cg2 = st.columns(2)
            with cg1: plot_graph(res1)
            with cg2: plot_graph(res2)
        else:
            plot_graph(res1)

        st.markdown("---")
        st.caption("**⚠️ אזהרת סיכון והבהרה משפטית:** הנתונים והניתוחים המוצגים באפליקציה זו נועדו למטרות לימודיות בלבד. שוק ההון אינו צפוי לחלוטין ועלול להיות שגוי. כל פעולה היא על אחריותך הבלעדית.")
