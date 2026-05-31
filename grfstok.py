import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# הגדרת תצורת הדף
st.set_page_config(page_title="מנוע ניתוח טכני", layout="wide")

st.title("📈 מנוע ניתוח טכני והפקת דוחות השקעה")
st.write("המערכת מנתחת את נתוני המניה ומפיקה סיכום המלצות מנומק המבוסס על אסטרטגיות מסחר קלאסיות.")

# --- סרגל צדי (Sidebar) ---
st.sidebar.header("הגדרות פיתוח וחיפוש")
ticker = st.sidebar.text_input("הכנס סימול מניה (Ticker):", value="AAPL").upper()

# נדרש טווח נתונים מספיק רחב (לפחות שנה) כדי לחשב ממוצע נע 200 בצורה תקינה
end_date = datetime.today()
start_date = end_date - timedelta(days=365 * 2) # שנתיים אחורה לגיבוי נתונים

@st.cache_data(ttl=3600)
def load_stock_data(ticker_symbol, start, end):
    stock_obj = yf.Ticker(ticker_symbol)
    hist_df = stock_obj.history(start=start, end=end)
    info_dict = stock_obj.info
    return hist_df, info_dict

try:
    with st.spinner('מנתח נתוני שוק ומחשב אינדיקטורים...'):
        df, info = load_stock_data(ticker, start_date, end_date)

    if df.empty or len(df) < 50:
        st.error("לא נמצאו מספיק נתונים היסטוריים לביצוע הניתוח הטכני.")
    else:
        # =========================================================
        # 🧪 חלק 1: חישוב אינדיקטורים טכניים (הלוגיקה המתמטית)
        # =========================================================
        
        # A. ממוצעים נעים (MA20, MA50, MA200)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['MA200'] = df['Close'].rolling(window=200).mean()

        # B. מדד כוח יחסי (RSI - 14 ימים)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # C. רמות תיקון פיבונאצ'י (מבוסס על השנה האחרונה)
        df_last_year = df.last('365D') if hasattr(df, 'last') else df.iloc[-252:]
        highest_high = df_last_year['High'].max()
        lowest_low = df_last_year['Low'].min()
        price_range = highest_high - lowest_low

        fib_levels = {
            '0.0% (שיא)': highest_high,
            '23.6%': highest_high - (0.236 * price_range),
            '38.2%': highest_high - (0.382 * price_range),
            '50.0% (מרכז)': highest_high - (0.500 * price_range),
            '61.8% (תמיכת זהב)': highest_high - (0.618 * price_range),
            '100.0% (שפל)': lowest_low
        }

        # נתונים נוכחיים לשורה התחתונה
        current_price = df['Close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        ma50_curr = df['MA50'].iloc[-1]
        ma200_curr = df['MA200'].iloc[-1]

        # =========================================================
        # 📊 חלק 2: הצגת גרפים מורחבים (מחיר + RSI)
        # =========================================================
        st.subheader(f"📊 תמונת מצב טכנית: {info.get('longName', ticker)}")
        
        # יצירת גרף עם שני פאנלים (Subplots) - עליון למחיר, תחתון ל-RSI
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, row_heights=[0.7, 0.3])

        # פאנל 1: נרות יפניים וממוצעים נעים
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="מחיר"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='orange', width=1.5), name="ממוצע נע 50"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='red', width=1.5), name="ממוצע נע 200"), row=1, col=1)
        
        # הוספת קווי פיבונאצ'י אופקיים לגרף המחיר
        for level, value in fib_levels.items():
            fig.add_shape(type="line", x0=df.index[0], y0=value, x1=df.index[-1], y1=value,
                          line=dict(color="gray", width=1, dash="dash"), row=1, col=1)

        # פאנל 2: מתנד RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
        # קווי גבול של קנוי יתר (70) ומכור יתר (30)
        fig.add_shape(type="line", x0=df.index[0], y0=70, x1=df.index[-1], y1=70, line=dict(color="red", width=1, dash="dot"), row=2, col=1)
        fig.add_shape(type="line", x0=df.index[0], y0=30, x1=df.index[-1], y1=30, line=dict(color="green", width=1, dash="dot"), row=2, col=1)

        fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # =========================================================
        # 🤖 חלק 3: מנוע החלטות והפקת דוח מנומק (The AI/Logic Engine)
        # =========================================================
        st.markdown("---")
        st.subheader("📋 דוח ניתוח טכני מנומק ומערכת החלטות")

        # מערכת חוקים לשקלול נקודות (Score)
        score = 0
        reasons_buy = []
        reasons_wait = []

        # 1. בדיקת מגמה ארוכת טווח (ממוצעים נעים)
        if current_price > ma200_curr:
            score += 1
            reasons_buy.append(f"**מגמה ראשית חיובית:** המחיר הנוכחי (${current_price:.2f}) נמצא מעל ממוצע נע 200 (${ma200_curr:.2f}), מה שמעיד על מומנטום שורי ארוך טווח.")
        else:
            score -= 1
            reasons_wait.append(f"**מגמה ראשית שלילית:** המחיר נסחר מתחת לממוצע נע 200 (${ma200_curr:.2f}). כניסה כעת היא מסוכנת ונוגדת את המגמה הכללית.")

        # 2. בדיקת מתנד מומנטום (RSI)
        if current_rsi > 70:
            score -= 2
            reasons_wait.append(f"**קניית יתר קיצונית (Overbought):** מדד ה-RSI עומד על {current_rsi:.1f} (מעל 70). הנכס 'יקר' בטווח הקצר ויש סיכוי גבוה לתיקון טכני מטה בהקדם.")
        elif current_rsi < 30:
            score += 2
            reasons_buy.append(f"**מכירת יתר עמוקה (Oversold):** מדד ה-RSI עומד על {current_rsi:.1f} (מתחת ל-30). הירידות עשויות להיות מוגזמות, ויש פוטנציאל לזינוק/ריבאונד קרוב.")
        else:
            reasons_buy.append(f"**מומנטום ניטרלי:** ה-RSI עומד על {current_rsi:.1f}, אין כרגע מצב קיצון של קנייה או מכירה.")

        # 3. בדיקת מיקום ביחס לרמות פיבונאצ'י ומציאת נקודת המתנה
        closest_fib_level = None
        closest_fib_dist = float('inf')
        for level_name, level_val in fib_levels.items():
            dist = abs(current_price - level_val)
            if dist < closest_fib_dist:
                closest_fib_dist = dist
                closest_fib_level = level_name

        # מציאת רמת התמיכה הקרובה ביותר מתחת למחיר (אם נרצה להמתין לירידה)
        waiting_target = fib_levels['61.8% (תמיכת זהב)']
        for level_name, level_val in sorted(fib_levels.items(), key=lambda x: x[1]):
            if level_val < current_price:
                waiting_target = level_val # רמת התמיכה הטכנית הקרובה ביותר מתחת למחיר

        # קביעת השורה התחתונה לפי הציון המשוקלל
        if score >= 2:
            verdict = "🟢 הזדמנות קנייה (Buy Signal)"
            color_box = "success"
            detailed_advise = "הפרמטרים הטכניים מסתנכרנים לנקודת כניסה נוחה. המומנטום תומך בעלייה, והסיכון יחסית נמוך בהשוואה לפוטנציאל."
        elif score <= -1:
            verdict = "🔴 להמתין לירידה / אל תקנה (Wait / Avoid)"
            color_box = "error"
            detailed_advise = f"השוק מראה סימני עייפות או מגמת ירידה ברורה. מומלץ להמתין לתיקון ומחיר נוח יותר באזור רמת התמיכה הקרובה."
        else:
            verdict = "🟡 החזק / המתנה מחוץ לשוק (Hold / Neutral)"
            color_box = "warning"
            detailed_advise = "אין הכרעה ברורה בין הקונים למוכרים. המחיר נמצא באזור דשדוש או באמצע הטווח. זה הזמן להמתין לפריצה ברורה של רמות המפתח."

        # הצגת תיבת ההחלטה למשתמש
        if color_box == "success": st.success(f"**השורה התחתונה של המערכת:** {verdict}")
        elif color_box == "warning": st.warning(f"**השורה התחתונה של המערכת:** {verdict}")
        else: st.error(f"**השורה התחתונה של המערכת:** {verdict}")

        # חלוקה לטורים מנומקים
        col_b, col_w = st.columns(2)
        with col_b:
            st.write("👍 **נימוקים התומכים בקנייה/החזקה:**")
            for r in reasons_buy: st.write(f"- {r}")
        with col_w:
            st.write("⚠️ **נימוקים הקוראים לזהירות/המתנה:**")
            for r in reasons_wait: st.write(f"- {r}")

        # אסטרטגיית פעולה אופרטיבית לפי הכתבה
        st.write("### 🎯 תוכנית עבודה אופרטיבית למשקיע:")
        st.info(f"""
        1. **הנחיית פעולה:** {detailed_advise}
        2. **רמת מחיר להמתנה/איסוף:** במידה וממתינים לירידה, רמת התמיכה הטכנית המרכזית (פיבונאצ'י) נמצאת ב-**${waiting_target:.2f}**.
        3. **ניהול סיכונים (חוק ה-1%-2% מתוך הכתבה):** אם בחרת להיכנס לעסקה, הגדר פקודת קטיעת הפסד (**Stop Loss**) קצת מתחת לרמת התמיכה הקרובה. ודא כי פוטנציאל הרווח שלך גדול לפחות פי 2 מהסיכון הכלכלי בעסקה.
        """)

except Exception as e:
    st.error(f"התרחשה שגיאה במהלך הניתוח הטכני: {e}")
