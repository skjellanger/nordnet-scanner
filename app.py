import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import time
import requests

st.set_page_config(page_title="Oslo Børs Momentumskanner", page_icon="📊", layout="wide")

TICKERS = [
    "HEX.OL", "NEL.OL", "NOD.OL", "TOM.OL", "AZT.OL", "CRAY.OL", "DTR.OL",
    "FRO.OL", "HAFNI.OL", "BWLPG.OL", "GOGL.OL", "HAUTO.OL", "BELCO.OL", "STB.OL", 
    "MPC.OL", "HSHP.OL", "SBO.OL", "KLAV.OL", "MINT.OL",
    "EQNR.OL", "AkerBP.OL", "VAR.OL", "SUBC.OL", "BORR.OL", "PGS.OL", "AKSO.OL", 
    "TGS.OL", "AKER.OL", "DNO.OL", "OET.OL", "REACH.OL", "DOF.OL", "RANA.OL",
    "MOWI.OL", "SALM.OL", "LSG.OL", "GSF.OL", "AUST.OL", "BAKKA.OL",
    "NHY.OL", "YAR.OL", "KOG.OL", "ALNG.OL", "REC.OL", "ACC.OL", "STNM.OL", "ELK.OL",
    "DNB.OL", "GJF.OL", "STORE.OL", "AUSS.OL", "NONG.OL", "MING.OL", "SVEG.OL",
    "ORK.OL", "TEL.OL", "NAS.OL", "SCHA.OL", "ADE.OL", "ATEA.OL", "AUTO.OL", 
    "KID.OL", "BOUV.OL", "LINK.OL", "PHO.OL"
]

@st.cache_data(ttl=120) # Oppdaterer dataen automatisk hvert 2. minutt
def analyze_stocks():
    scored_data = []
    
    # OPPDATERING: Ny, stabil standard-metode for opprettelse av sesjon mot Yahoo
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    for ticker in TICKERS:
        try:
            time.sleep(0.05) # Liten pause så vi ikke blir sperret
            stock = yf.Ticker(ticker, session=session)
            df = stock.history(period="45d", interval="1d")
            
            if df.empty or len(df) < 22:
                continue
                
            latest_close = float(df['Close'].iloc[-1])
            latest_volume = float(df['Volume'].iloc[-1])
            avg_volume_20 = float(df['Volume'].iloc[-21:-1].mean())
            volume_ratio = latest_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0
            
            df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
            
            ema9 = float(df['EMA9'].iloc[-1])
            ema21 = float(df['EMA21'].iloc[-1])
            
            if pd.isna(latest_close) or pd.isna(ema9) or pd.isna(ema21) or pd.isna(volume_ratio):
                continue
                
            # --- AGGRESSIV MATEMATISK SCORING (0 - 100) ---
            pct_above_ema9 = ((latest_close - ema9) / ema9) * 100
            ema_spread = ((ema9 - ema21) / ema21) * 100
            
            momentum_score = 0.0
            if latest_close > ema9 and ema9 > ema21:
                momentum_score = 25.0 + (pct_above_ema9 * 5.0) + (ema_spread * 10.0)
            elif latest_close > ema21:
                momentum_score = 15.0 + (pct_above_ema9 * 3.0)
            else:
                momentum_score = ((latest_close - ema21) / ema21) * 100.0
                
            momentum_score = max(0.0, min(50.0, momentum_score))
            
            if volume_ratio >= 1.0:
                volume_score = 15.0 + ((volume_ratio - 1.0) * 20.0)
            else:
                volume_score = volume_ratio * 15.0
                
            volume_score = max(0.0, min(50.0, volume_score))
            total_score = round(float(momentum_score + volume_score), 1)

            scored_data.append({
                "Aksje": str(ticker.replace(".OL", "")),
                "Kurs (NOK)": round(latest_close, 2),
                "Volum_Ratio": round(volume_ratio, 2),
                "EMA9": round(ema9, 2),
                "EMA21": round(ema21, 2),
                "Super_Score": total_score
            })
        except:
            continue
            
    return pd.DataFrame(scored_data).sort_values(by="Super_Score", ascending=False) if scored_data else pd.DataFrame()

# --- WEB-VISNING ---
st.title("🚀 Oslo Børs Matematisk Momentumskanner")
st.write("Dette kontrollpanelet rangerer aksjer live basert på volumavvik og trendlinje-spredning.")

if st.button("🔄 Manuelt oppdater data nå"):
    st.cache_data.clear()

with st.spinner("Henter og kalkulerer rådata fra Oslo Børs..."):
    df_res = analyze_stocks()

if df_res.empty:
    st.error("Forbereder datastrømmen. Vennligst vent noen sekunder eller trykk på oppdateringsknappen.")
else:
    col1, col2 = st.columns([1, 1.2]) # Balanserer bredden på kolonnene
    
    with col1:
        st.subheader("🔥 Reelle Momentum-Ledere (Topp 15)")
        fig = px.bar(df_res.head(15), x='Super_Score', y='Aksje', orientation='h',
                     color='Super_Score', color_continuous_scale='Turbo', template='plotly_dark')
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("📊 Presisjonstabell for Daytrading")
        # Formaterer tabellvisningen
        df_display = df_res.copy()
        df_display["Volum_Ratio"] = df_display["Volum_Ratio"].apply(lambda x: f"{x}x")
        st.dataframe(df_display, height=600, use_container_width=True)
