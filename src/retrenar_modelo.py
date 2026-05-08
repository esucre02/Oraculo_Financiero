import pandas as pd
import numpy as np  # <-- ¡NUEVO! Necesario para manejar los infinitos
import yfinance as yf
import xgboost as xgb
import pickle
import json
import warnings
import sys

# Ignorar advertencias de pandas
warnings.filterwarnings('ignore')

print("🤖 Iniciando proceso de retrenamiento del Oráculo...")

# --- PASO 1: CARGAR EL DICCIONARIO ---
with open('src/diccionario_tickers.json', 'r') as f:
    diccionario_tickers = json.load(f)

lista_dataframes = []

print("📥 Descargando datos recientes de Wall Street...")
for ticker, ticker_encoded in diccionario_tickers.items():
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        
        if df.empty or len(df) < 200:
            continue
            
        df['Ticker_Encoded'] = ticker_encoded
        
        # --- CÁLCULOS TÉCNICOS ---
        df['Std_20'] = df['Close'].rolling(window=20).std()
        df['Momentum_10'] = df['Close'] - df['Close'].shift(10)
        df['High_Low_Spread'] = df['High'] - df['Low']
        
        df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_SMA_20']
        df['Vol_Change'] = df['Volume'].pct_change().fillna(0)
        
        sma200 = df['Close'].rolling(window=200).mean()
        df['Above_SMA200'] = (df['Close'] > sma200).astype(int)
        
        high_50 = df['High'].rolling(window=50).max()
        df['Pct_From_High_50'] = (df['Close'] - high_50) / high_50

        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD_Line'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']
        
        sma20 = df['Close'].rolling(window=20).mean()
        df['Z_Score_20'] = (df['Close'] - sma20) / df['Std_20']
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # --- TARGET ---
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        
        df = df.dropna()
        lista_dataframes.append(df)
        
    except Exception as e:
        print(f"⚠️ Error procesando {ticker}: {e}")

if len(lista_dataframes) == 0:
    print("❌ ERROR CRÍTICO: No se pudo descargar información de ninguna empresa.")
    sys.exit(1)

df_final = pd.concat(lista_dataframes)

# --- LIMPIEZA ANTI-INFINITOS (LA SOLUCIÓN AL ERROR) ---
print("🧹 Limpiando valores infinitos...")
# Reemplazamos los infinitos positivos y negativos por NaN, y luego borramos esas filas
df_final = df_final.replace([np.inf, -np.inf], np.nan).dropna()

# --- PASO 3: PREPARAR LOS DATOS ---
print("⚙️ Preparando datos para XGBoost...")
columnas_entrenamiento = [
    'Volume', 'Std_20', 'MACD_Line', 'MACD_Signal', 'MACD_Hist', 
    'RSI_14', 'Momentum_10', 'Vol_SMA_20', 'Vol_Ratio', 'Vol_Change', 
    'High_Low_Spread', 'Z_Score_20', 'Above_SMA200', 'Pct_From_High_50',
    'Ticker_Encoded'
]

X = df_final[columnas_entrenamiento]
y = df_final['Target']

# --- PASO 4: ENTRENAR ---
print("🧠 Entrenando la Inteligencia Artificial...")
modelo_xgb = xgb.XGBClassifier(learning_rate=0.1, max_depth=7, n_estimators=200, random_state=42)
modelo_xgb.fit(X, y)

# --- PASO 5: GUARDAR ---
ruta_modelo = 'models/oraculo_financiero2_xgb.pkl'
with open(ruta_modelo, 'wb') as archivo:
    pickle.dump(modelo_xgb, archivo)

print(f"✅ ¡Éxito! El nuevo modelo ha sido entrenado y guardado en {ruta_modelo}")