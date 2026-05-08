import numpy as np
import pandas as pd

def ejecutar_monte_carlo(df, dias_proyeccion=30, n_simulaciones=1000, vol_mult=1.0):
    """
    Ejecuta una simulación estocástica basada en Movimiento Browniano Geométrico (GBM).
    Refinado para asegurar coherencia estadística y reproductibilidad.
    """
    if df.empty or len(df) < 20:
        return pd.DataFrame(), {}
        
    # Calcular retornos logarítmicos
    precios = df['Adj Close'] if 'Adj Close' in df.columns else df['Close']
    retornos_log = np.log(precios / precios.shift(1)).dropna()
    
    # Parámetros base diarios
    mu = retornos_log.mean() 
    sigma_base = retornos_log.std()
    
    # Aplicar Multiplicador de Volatilidad (Stress Test)
    # Si aumentamos la volatilidad, el componente de drift (mu - 0.5 * sigma^2) 
    # debe recalcularse para mantener la coherencia del modelo GBM.
    sigma_adj = sigma_base * vol_mult
    drift_adj = mu - (0.5 * (sigma_adj**2))
    
    # Precio inicial
    S0 = precios.iloc[-1]
    
    # Generación de caminos (Vectorizada para performance)
    # W_t ~ N(0, 1) con semilla fija para determinismo
    rng = np.random.default_rng(42)
    shocks = rng.normal(0, 1, (dias_proyeccion, n_simulaciones))
    
    # Matriz de incrementos: exp((mu - 0.5*sigma^2) + sigma * Z)
    incrementos = np.exp(drift_adj + sigma_adj * shocks)
    
    # Concatenar precio inicial y calcular producto acumulado
    caminos = np.vstack([np.full(n_simulaciones, S0), incrementos])
    precios_simulados = np.cumprod(caminos, axis=0)
    
    # Convertir a DataFrame (Filas = Días, Columnas = Simulaciones)
    df_sim = pd.DataFrame(precios_simulados)
    
    # Estadísticas de resumen
    precios_finales = precios_simulados[-1, :]
    
    # --- Inteligencia Avanzada (Divine Level) ---
    # 1. Percentiles P10, P50, P90
    p10, p50, p90 = np.percentile(precios_finales, [10, 50, 90])
    spread_rel = (p90 - p10) / S0
    score_confianza = max(0, min(100, 100 * (1 - (spread_rel / 1.5)))) # Refinado para P90/P10
    
    # 2. Análisis de Top 3 Drivers
    driver_drift = abs(drift_adj)
    driver_sigma = sigma_base
    driver_stress = sigma_adj - sigma_base
    
    total_impact = driver_drift + driver_sigma + driver_stress
    top_drivers = [
        {"name": "Tendencia Histórica (Drift)", "impact": (driver_drift / total_impact) * 100},
        {"name": "Volatilidad Base (Sigma)", "impact": (driver_sigma / total_impact) * 100},
        {"name": "Factor de Estrés (Stress)", "impact": (driver_stress / total_impact) * 100}
    ]
    top_drivers = sorted(top_drivers, key=lambda x: x['impact'], reverse=True)
    
    stats = {
        "current_price": S0,
        "mean_projection": np.mean(precios_finales),
        "p50": p50,
        "p10": p10,
        "p90": p90,
        "std_dev": np.std(precios_finales),
        "score_confianza": score_confianza,
        "driver_principal": top_drivers[0]['name'],
        "top_3_drivers": top_drivers,
        "coef_incertidumbre": spread_rel,
        "sensibilidad": sigma_adj / sigma_base,
        "n_simulaciones": n_simulaciones,
        "dias": dias_proyeccion
    }
    
    return df_sim, stats
