import streamlit as st
import pandas as pd
import pickle
import json
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from indicators import calcular_indicadores_grid, formatear_valor
from simulation import ejecutar_monte_carlo
import textwrap

st.set_page_config(page_title="Advanced Quant Trading Platform", page_icon="📈", layout="wide")

# --- CUSTOM CSS INJECTION ---
st.markdown("""
<style>
    /* Premium Financial Dark Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0d1117;
        color: #f0f6fc;
    }
    
    .main {
        background-color: #0d1117;
    }
    
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
        padding-top: 2rem;
    }
    
    /* Smart Cards Grid */
    .smart-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin: 24px 0;
    }
    
    .smart-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 160px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .smart-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
    }
    
    .card-title {
        color: #8b949e;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .card-main {
        margin: 8px 0;
    }
    
    .card-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f0f6fc;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .card-variation {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 4px;
    }
    
    .comparison-box {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid rgba(48, 54, 61, 0.5);
    }
    
    .comparison-item {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-bottom: 4px;
    }
    
    .mini-indicator {
        height: 4px;
        width: 100%;
        background: #30363d;
        border-radius: 2px;
        margin-top: 8px;
        overflow: hidden;
    }
    
    .indicator-bar {
        height: 100%;
        border-radius: 2px;
    }
    
    /* Consistency & Alignment */
    .stMarkdown { line-height: 1.6; }
    .custom-divider { height: 1px; background: #30363d; margin: 24px 0; }
    
    /* Headers */
    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    
    /* Buttons and Inputs */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Custom divider */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #30363d, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

import os

# --- CARGAR ARCHIVOS ---
@st.cache_resource
def cargar_archivos_v2():
    # Directorio actual (src/)
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    # Directorio raíz (Proyecto_Final/)
    dir_raiz = os.path.dirname(dir_actual)
    
    ruta_modelo = os.path.join(dir_raiz, 'models', 'oraculo_financiero2_xgb.pkl')
    ruta_diccionario = os.path.join(dir_actual, 'diccionario_tickers.json')
    
    try:
        with open(ruta_modelo, 'rb') as archivo_modelo:
            modelo = pickle.load(archivo_modelo)
    except Exception as e:
        print(f"Error cargando modelo: {e}")
        modelo = None # Fallback if model not found
        
    try:
        with open(ruta_diccionario, 'r') as archivo_json:
            diccionario = json.load(archivo_json)
    except Exception as e:
        print(f"Error cargando diccionario: {e}")
        diccionario = {}
        
    return modelo, diccionario

modelo, diccionario_tickers = cargar_archivos_v2()



# --- SIDEBAR ---
with st.sidebar:
    st.subheader("Selección de Activos")
    # Multiselect para múltiples activos
    acciones_seleccionadas = st.multiselect(
        "Comparar Acciones (Máx 10)", 
        options=list(diccionario_tickers.keys()), 
        default=[list(diccionario_tickers.keys())[0]] if diccionario_tickers else [],
        max_selections=10
    )

    
    st.markdown("---")
    st.subheader("Proyección")
    horizonte = st.selectbox("Horizonte de Proyección", options=["1 día", "7 días", "14 días", "30 días", "60 días", "90 días"], index=3)
    dias_dict = {"1 día": 1, "7 días": 7, "14 días": 14, "30 días": 30, "60 días": 60, "90 días": 90}
    horizonte_dias = dias_dict[horizonte]
    
    st.markdown("---")
    st.subheader("Visualización")
    tipo_grafico = st.selectbox("Tipo de Visualización", options=["Línea", "Velas", "Área", "Barras"], index=2)
    mostrar_volumen = st.checkbox("Mostrar Volumen", value=True)
    mostrar_mc_paths = st.checkbox("Ver Rutas Proyectadas", value=True)
    mostrar_grid = st.checkbox("Ver Parámetros Clave", value=False)


    st.markdown("---")
    vol_mult = st.slider("Multiplicador de Volatilidad", 1.0, 3.0, 1.0, step=0.1)

import sqlite3

# --- DOWNLOAD DATA ---
@st.cache_data
def descargar_datos(ticker):
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(dir_actual, "sp500_market_data.db")
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM sp500_daily_metrics WHERE Ticker = '{ticker}'"
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            # Ensure index has name 'Date'
            df.index.name = 'Date'
            return df
    except Exception as e:
         pass
         
    df = yf.download(ticker, period='2y', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

st.title("Advanced Quant Trading Platform")

# Selector de periodo global
period = st.radio("Período de Visualización", ["1M", "3M", "6M", "YTD", "1A", "MAX"], index=4, horizontal=True)

datos_dict = {}
sim_dict = {}
stats_dict = {}

if not acciones_seleccionadas:
    st.warning("Selecciona al menos una acción en el sidebar.")
    st.stop()

# --- CACHED SIMULATION ---
@st.cache_data
def obtener_simulacion_cache(ticker, d_proyeccion, v_mult):
    df_mini = descargar_datos(ticker)
    if not df_mini.empty and len(df_mini) > 20:
        return ejecutar_monte_carlo(df_mini, dias_proyeccion=d_proyeccion, n_simulaciones=1000, vol_mult=v_mult)
    return pd.DataFrame(), {}


# --- MAIN LOGIC ---
with st.spinner(f"Generando inteligencia predictiva..."):
    for ticker in acciones_seleccionadas:
        df = descargar_datos(ticker)
        if not df.empty and len(df) > 20:
            df_s, stats_s = obtener_simulacion_cache(ticker, horizonte_dias, vol_mult)
            datos_dict[ticker] = df
            sim_dict[ticker] = df_s
            stats_dict[ticker] = stats_s

if not datos_dict:
    st.error("No se pudieron cargar datos suficientes para ninguna acción.")
    st.stop()

st.markdown("---")

# 1. Copiloto Inteligente & Insights
st.subheader("Copiloto de Inteligencia Financiera")
for i, (tk, stats) in enumerate(stats_dict.items()):
    if i % 4 == 0:
        cols_insight = st.columns(min(len(stats_dict) - i, 4), gap="medium")
    
    with cols_insight[i % 4]:
        score = stats.get('score_confianza', 0.0)
        driver = stats.get('driver_principal', 'N/A')
        sensi = stats.get('sensibilidad', 1.0)
        status = "Alto" if score > 80 else "Medio" if score > 50 else "Bajo"
        color = "#3fb950" if status == "Alto" else "#d29922" if status == "Medio" else "#f85149"
        
        st.markdown(f"""
        <div class="smart-card" style="border-left: 4px solid {color}; padding: 16px; margin-bottom: 16px;">
            <div class="card-title">{tk} | Score de Confianza</div>
            <div class="card-value" style="color: {color};">{score:.0f}% ({status})</div>
            <div style="font-size: 0.8rem; margin-top: 8px;">
                <b>Driver Principal:</b> {driver}<br>
                <b>Sensibilidad:</b> {sensi:.1f}x
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 2. Row of Quick Metrics
st.subheader("Estado de Activos")
for i, (tk, df) in enumerate(datos_dict.items()):
    if i % 5 == 0:
        cols_precio = st.columns(min(len(datos_dict) - i, 5), gap="medium")
    
    with cols_precio[i % 5]:
        ultimo_cierre = df['Close'].iloc[-1]
        cierre_anterior = df['Close'].iloc[-2]
        cambio_pct = ((ultimo_cierre - cierre_anterior) / cierre_anterior) * 100
        color_class = "pct-up" if cambio_pct > 0 else "pct-down" if cambio_pct < 0 else "pct-neutral"
        st.markdown(f"""
        <div class="smart-card" style="min-height: 100px; padding: 16px; text-align: center; margin-bottom: 16px;">
            <div class="card-title">{tk}</div>
            <div class="card-value" style="font-size: 1.2rem;">${ultimo_cierre:.2f}</div>
            <div class="{color_class}" style="font-size: 0.75rem;">{"+" if cambio_pct > 0 else ""}{cambio_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

st.markdown("---")

# 3. Matriz de Correlación
if len(datos_dict) > 1:
    st.subheader("Matriz de Correlación (Pearson)")
    df_combined = pd.DataFrame({tk: df['Close'] for tk, df in datos_dict.items()}).dropna()
    if not df_combined.empty:
        df_corr = df_combined.corr()
        fig_corr = go.Figure(go.Heatmap(
            z=df_corr.values, x=df_corr.columns, y=df_corr.index, colorscale='balance', zmin=-1, zmax=1,
            text=np.round(df_corr.values, 2), texttemplate="%{text}"
        ))
        fig_corr.update_layout(template="plotly_dark", height=280, margin=dict(t=20, b=20, l=40, r=40))
        st.plotly_chart(fig_corr, use_container_width=True)

# 2. Unified Canvas
st.subheader("Evolución y Rendimiento Proyectado")

# Si hay más de una acción, forzamos normalización %
is_comparison = len(datos_dict) > 1

fig = go.Figure()

# Colores consistentes para los activos
colores = ['#58a6ff', '#3fb950', '#f85149', '#d29922', '#bc8cff', '#ffa657', '#79c0ff', '#56d364', '#fa7970', '#e3b341']

for i, (tk, df_data) in enumerate(datos_dict.items()):
    color = colores[i % len(colores)]
    df_sim = sim_dict.get(tk, pd.DataFrame())
    stats_sim = stats_dict.get(tk, {})
    
    dias_filtro = {"1M": 30, "3M": 90, "6M": 180, "YTD": 120, "1A": 252, "MAX": len(df_data)}
    n_lookback = dias_filtro.get(period, 30)
    df_plot = df_data.tail(n_lookback)
    
    if df_plot.empty: continue
    
    ultima_fecha = df_plot.index[-1]
    fechas_futuras = pd.date_range(start=ultima_fecha + pd.Timedelta(days=1), periods=horizonte_dias + 1, freq='B')
    # Ajustar fechas si hay desalineación (el primer punto de simulación es el S0)
    fechas_completas_sim = pd.date_range(start=ultima_fecha, periods=horizonte_dias + 1, freq='B')

    if not is_comparison:
        # Modo Single Asset: Soporta todos los tipos de gráfico
        if tipo_grafico == "Velas":
            fig.add_trace(go.Candlestick(
                x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
                low=df_plot['Low'], close=df_plot['Close'], name=f'{tk} Histórico'
            ))
        elif tipo_grafico == "Barras":
            fig.add_trace(go.Ohlc(
                x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
                low=df_plot['Low'], close=df_plot['Close'], name=f'{tk} Histórico'
            ))
        else: # Línea o Área
            fill = 'tozeroy' if tipo_grafico == "Área" else None
            fig.add_trace(go.Scatter(
                x=df_plot.index, y=df_plot['Close'], mode='lines', name=f'{tk} Histórico',
                line=dict(color=color, width=2), fill=fill
            ))
        
        # --- PROYECCIÓN UNIVERSAL (Visibilidad en todos los modos) ---
        if not df_sim.empty:
            # Seleccionamos trayectoria estocástica representativa
            ultimo_valor_mediana = df_sim.median(axis=1).iloc[-1]
            distancias = (df_sim.iloc[-1] - ultimo_valor_mediana).abs()
            col_representativa = distancias.idxmin()
            ruta_jagged = df_sim[col_representativa]
            
            # Color distintivo (Dorado para el Futuro)
            color_proj = "#FFD700" 
            
            fig.add_trace(go.Scatter(
                x=fechas_completas_sim, y=ruta_jagged, mode='lines',
                name=f'{tk} Proyección (Safe)', 
                line=dict(color=color_proj, width=3, dash='dot'),
                hovertemplate='%{y:.2f} (Escenario Probable)'
            ))
            
            # ESCENARIOS DINÁMICOS P10/P90 (Divine Level)
            p10_line = df_sim.apply(lambda x: np.percentile(x, 10), axis=1)
            p90_line = df_sim.apply(lambda x: np.percentile(x, 90), axis=1)
            
            fig.add_trace(go.Scatter(
                x=fechas_completas_sim, y=p90_line, mode='lines', 
                line=dict(color='rgba(63, 185, 80, 0.4)', width=1, dash='dot'),
                name='Optimista (P90)'
            ))
            fig.add_trace(go.Scatter(
                x=fechas_completas_sim, y=p10_line, mode='lines', 
                line=dict(color='rgba(248, 81, 73, 0.4)', width=1, dash='dot'),
                name='Pesimista (P10)',
                fill='tonexty', fillcolor='rgba(88, 166, 255, 0.05)'
            ))
            

    else:
        # Modo Comparación: Siempre Normalizado (%)
        base_price = df_plot['Close'].iloc[0]
        hist_pct = (df_plot['Close'] / base_price - 1) * 100
        
        fig.add_trace(go.Scatter(
            x=df_plot.index, y=hist_pct, mode='lines', name=f'{tk}',
            line=dict(color=color, width=2)
        ))
        
        if not df_sim.empty:
            # Ruta Jagged para comparación también
            ultimo_valor_mediana = df_sim.median(axis=1).iloc[-1]
            col_repr = (df_sim.iloc[-1] - ultimo_valor_mediana).abs().idxmin()
            ruta_repr = df_sim[col_repr]
            
            sim_pct = (ruta_repr / base_price - 1) * 100
            
            fig.add_trace(go.Scatter(
                x=fechas_completas_sim, y=sim_pct, mode='lines',
                name=f'{tk} Proyección', line=dict(color=color, width=2, dash='dot')
            ))

# Layout final corregido
title_y = "Rendimiento Normalizado (%)" if is_comparison else f"Precio {tk} ($)"
fig.update_layout(
    template="plotly_dark", hovermode="x unified",
    margin=dict(l=40, r=40, t=10, b=40),
    xaxis=dict(showgrid=True, gridcolor="#21262d", rangeslider=dict(visible=False)),
    yaxis=dict(showgrid=True, gridcolor="#21262d", title_text=title_y),
    height=600, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# 3. Borrar comparación transversal (Eliminado por Requerimiento Fase 2)

if mostrar_grid:
    st.divider()
    st.subheader("Análisis de Parámetros Clave")
    
    # Definimos el activo principal para el backtest (el primero seleccionado)
    primero = acciones_seleccionadas[0]
    df_data_ind = datos_dict[primero]

    # --- REFACTOR: Smart Cards Unificadas (Fase 4) ---
    master_indicadores = {}
    for tk_id, df_tk in datos_dict.items():
        # Histórico
        dias_hist = {"1M": 30, "3M": 90, "6M": 180, "YTD": 120, "1A": 252, "MAX": len(df_tk)}.get(period, 30)
        ind_hist = calcular_indicadores_grid(df_tk, lookback_days=dias_hist)
        
        # Futuro
        df_sim_tk = sim_dict.get(tk_id, pd.DataFrame())
        ind_fut = {}
        if not df_sim_tk.empty:
            try:
                # Usamos la TRAYECTORIA REAL (Same as chart) para coherencia
                ultimo_val_med = df_sim_tk.median(axis=1).iloc[-1]
                idx_repr = (df_sim_tk.iloc[-1] - ultimo_val_med).abs().idxmin()
                camino_repr = df_sim_tk[idx_repr].values
                
                df_fut_tk = df_tk.copy()
                prom_vol = df_tk['Volume'].mean()
                fechas_f_tk = pd.date_range(start=df_tk.index[-1] + pd.Timedelta(days=1), periods=horizonte_dias + 1, freq='B')
                
                filas_fut = []
                for px in camino_repr[1:]:
                    spread = df_tk['High'].mean() / df_tk['Low'].mean() if not df_tk.empty else 1.005
                    filas_fut.append({'Open': px, 'High': px * spread, 'Low': px / spread, 'Close': px, 'Adj Close': px, 'Volume': prom_vol})
                
                df_append_tk = pd.DataFrame(filas_fut, index=fechas_f_tk[1:])
                df_total_tk = pd.concat([df_fut_tk, df_append_tk])
                ind_fut = calcular_indicadores_grid(df_total_tk, lookback_days=horizonte_dias)
            except: pass
            
        master_indicadores[tk_id] = {'hist': ind_hist, 'fut': ind_fut}

    categorias = {
        "Precio": ["ADJ CLOSE", "HIGH", "LOW", "OPEN"],
        "Volumen": ["VOLUME", "Vol ADX", "Vol OBV", "Vol CMF", "Vol FI", "Vol MFI", "Vol NVI"],
        "Volatilidad": ["Volat BBH", "Volat BBL", "Volat KCH", "Volat KCL"]
    }

    # Rendimiento unificado por métrica
    for cat_nombre, metricas_cat in categorias.items():
        st.markdown(f"#### {cat_nombre}")
        cols_cat = st.columns(4) # 4 columnas para alineación perfecta
        
        for i, m in enumerate(metricas_cat):
            with cols_cat[i % 4]:
                html_assets = ""
                for tk_id in acciones_seleccionadas:
                    if tk_id in master_indicadores and m in master_indicadores[tk_id]['hist']:
                        data_h = master_indicadores[tk_id]['hist'][m]
                        data_f = master_indicadores[tk_id]['fut'].get(m, {})
                        
                        val_now = data_h['val']
                        pct_p = data_h.get('pct', 0.0)
                        
                        val_f = data_f.get('val', val_now)
                        pct_f = ((val_f - val_now) / val_now * 100) if val_now != 0 else 0
                        
                        c_p = "pct-up" if pct_p > 0 else "pct-down"
                        c_f = "pct-up" if pct_f > 0 else "pct-down"
                        
                        # Barra de intensidad (basada en el activo principal si hay duda, o en el actual)
                        bar_w = min(abs(pct_p)*5, 100)
                        bar_c = "#3fb950" if pct_p > 0 else "#f85149"

                        html_assets += f'<div class="asset-row" style="padding: 8px 0; border-bottom: 1px solid #30363d;">'
                        html_assets += f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                        html_assets += f'<span style="font-weight: 700; color: #58a6ff; font-size: 0.85rem;">{tk_id}</span>'
                        html_assets += f'<span style="font-size: 1rem; font-weight: 500;">{formatear_valor(val_now)}</span>'
                        html_assets += f'</div>'
                        html_assets += f'<div style="display: flex; justify-content: space-between; font-size: 0.7rem; margin-top: 2px;">'
                        html_assets += f'<span class="{c_p}">Hist: {pct_p:+.1f}%</span>'
                        html_assets += f'<span class="{c_f}" style="color: #FFD700 !important; font-weight: 700;">Proj: {pct_f:+.1f}%</span>'
                        html_assets += f'</div>'
                        html_assets += f'<div style="height: 2px; background: #21262d; border-radius: 1px; margin-top: 4px;">'
                        html_assets += f'<div style="width: {bar_w}%; height: 100%; background: {bar_c}; border-radius: 1px;"></div>'
                        html_assets += f'</div></div>'
                
                full_card_html = f'<div class="smart-card" style="margin-bottom: 20px; border-top: 2px solid #58a6ff; background: #161b22; border-radius: 6px; padding: 10px;">'
                full_card_html += f'<div style="font-size: 0.9rem; font-weight: 600; color: #8b949e; margin-bottom: 8px; text-transform: uppercase;">{m}</div>'
                full_card_html += html_assets
                full_card_html += '</div>'
                
                st.markdown(full_card_html, unsafe_allow_html=True)

    # 4. Backtesting Simple (Cruce de Medias)
    st.divider()
    st.subheader("Estrategia Backtesting: Cruce Medias 20/50")
    
    fig_backtest = go.Figure()
    colores_bt = ['#3fb950', '#58a6ff', '#f85149', '#d29922', '#bc8cff', '#ffa657', '#79c0ff', '#56d364', '#fa7970', '#e3b341']

    for i, (tk, df_bt) in enumerate(datos_dict.items()):
        color = colores_bt[i % len(colores_bt)]
        # Use a copy to avoid SettingWithCopyWarning or affecting original data
        df_bt_copy = df_bt.copy()
        df_bt_copy['MA20'] = df_bt_copy['Close'].rolling(window=20).mean()
        df_bt_copy['MA50'] = df_bt_copy['Close'].rolling(window=50).mean()
        
        df_bt_copy['Signal'] = 0
        df_bt_copy.loc[df_bt_copy['MA20'] > df_bt_copy['MA50'], 'Signal'] = 1
        df_bt_copy['Retorno_Estrategia'] = df_bt_copy['Close'].pct_change() * df_bt_copy['Signal'].shift(1)
        
        rend_cum_est = (1 + df_bt_copy['Retorno_Estrategia']).dropna().cumprod() - 1
        
        fig_backtest.add_trace(go.Scatter(
            x=rend_cum_est.index, y=rend_cum_est * 100, 
            name=f"Estrategia {tk}", 
            line=dict(color=color, width=2)
        ))
        
        # Opcional: Mostrar Buy & Hold del primero como referencia gris
        if i == 0 and len(datos_dict) > 1:
            rend_cum_bh = (1 + df_bt_copy['Close'].pct_change()).dropna().cumprod() - 1
            fig_backtest.add_trace(go.Scatter(
                x=rend_cum_bh.index, y=rend_cum_bh * 100, 
                name=f"B&H {tk} (Ref)", 
                line=dict(color="#8b949e", dash='dash', width=1)
            ))
        elif len(datos_dict) == 1:
            # Si solo hay uno, mostramos su B&H normal
            rend_cum_bh = (1 + df_bt_copy['Close'].pct_change()).dropna().cumprod() - 1
            fig_backtest.add_trace(go.Scatter(
                x=rend_cum_bh.index, y=rend_cum_bh * 100, 
                name=f"Buy & Hold {tk}", 
                line=dict(color="#8b949e", dash='dash')
            ))

    fig_backtest.update_layout(
        template="plotly_dark", height=400, 
        title_text="Rendimiento Acumulado de Estrategia (%)", 
        yaxis=dict(title_text="%"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_backtest, use_container_width=True)
