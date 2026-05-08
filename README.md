# Advanced Quant Trading Platform (Oráculo Financiero)

![Status](https://img.shields.io/badge/Status-Production--Ready-success?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-2.1.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)

## Enlace a la app: https://oraculo-financiero.onrender.com

Documentación técnica detallada sobre la arquitectura, diseño y operaciones de la plataforma Advanced Quant Trading. Este documento sigue los estándares de ingeniería para sistemas de misión crítica.

---

## 1. Visión Ejecutiva

### Propuesta de Valor
La plataforma **Advanced Quant Trading** es una herramienta de grado institucional diseñada para proporcionar inteligencia accionable en los mercados financieros. Combina análisis técnico avanzado, simulaciones estocásticas de riesgo e inteligencia predictiva basada en Machine Learning, permitiendo a los analistas cuantitativos y traders tomar decisiones basadas en datos empíricos y probabilidades, reduciendo el ruido cognitivo inherente al mercado.

### Problema que Resuelve
Los analistas financieros se enfrentan a la sobrecarga de información y a la latencia en el cálculo de múltiples escenarios de riesgo. Esta plataforma resuelve este cuello de botella consolidando la ingesta de datos en tiempo real, el cálculo de docenas de indicadores técnicos, la proyección probabilística del riesgo (Monte Carlo) y el modelado predictivo (XGBoost) en un panel de control unificado y de baja latencia.

---

## 2. Arquitectura y Tech Stack

El sistema adopta una arquitectura de **Monolito Modular Orientado a Datos (Data-Driven Modular Monolith)**, priorizando el rendimiento computacional y la mantenibilidad. La separación estricta entre la capa de presentación, el motor de inferencia matemática y el pipeline de datos permite una evolución independiente de los componentes.

### Decisiones de Stack Tecnológico

| Componente | Tecnología | Justificación Arquitectónica |
| :--- | :--- | :--- |
| **Frontend & UI** | **Streamlit** | Permite el desarrollo declarativo de la UI directamente en Python, eliminando la sobrecarga de mantener un framework JS separado. Ideal para aplicaciones data-heavy de uso interno. |
| **Data Processing** | **Pandas & NumPy** | Estándar de la industria para manipulación vectorial de series temporales. Garantiza procesamiento en memoria de baja latencia. |
| **Machine Learning** | **XGBoost** | Algoritmo *Gradient Boosting* altamente optimizado para datos tabulares estructurados. Supera a las redes neuronales en series de tiempo financieras en términos de rendimiento y explicabilidad (Feature Importance). |
| **Simulación Estocástica** | **NumPy (Vectorized)** | El modelo *Geometric Brownian Motion* (GBM) se ejecuta vectorialmente sobre matrices de NumPy, calculando miles de trayectorias en milisegundos sin bucles pesados. |
| **Capa de Datos** | **SQLite + yfinance** | Arquitectura híbrida: SQLite actúa como un caché persistente local de alta velocidad para datos históricos (SP500), mientras que `yfinance` sirve como fallback dinámico para datos en vivo. |
| **Visualización** | **Plotly (Go)** | Renderizado basado en WebGL, permitiendo gráficos interactivos fluidos incluso con miles de puntos de datos (velas japonesas, nubes de dispersión, heatmaps). |

---

## 3. Principios de Diseño y Patrones

La base de código está estructurada siguiendo principios de ingeniería robustos para garantizar su escalabilidad a medida que aumenta la complejidad cuantitativa.

*   **Separation of Concerns (SoC):** La lógica de negocio está estrictamente desacoplada. `app.py` actúa únicamente como controlador de presentación. Las matemáticas complejas residen en `simulation.py` y los cálculos de análisis técnico en `indicators.py`. El pipeline de entrenamiento está aislado en `retrenar_modelo.py`.
*   **Memoization Pattern (Caché Multinivel):** Debido a que los cálculos de Monte Carlo y descargas de red son costosos, el sistema emplea la decoración `@st.cache_data` intensivamente. Esto asegura que parámetros idénticos recuperen los resultados de la memoria RAM en O(1), escalando eficientemente con múltiples usuarios simultáneos.
*   **Fallback & Resilience Pattern (Graceful Degradation):** El módulo de ingesta de datos intenta leer primero desde una base de datos SQLite precompilada (`sp500_market_data.db`). Si el activo no existe o el archivo no está accesible, el sistema hace *fallback* automáticamente a las APIs web (`yfinance`) sin interrumpir la sesión del usuario.
*   **Vectorización de Cálculos Matemáticos:** Se evitan los bucles `for` en las simulaciones probabilísticas. En su lugar, el Movimiento Browniano Geométrico calcula matrices estocásticas en bloques contiguos de memoria usando las capacidades de C de NumPy.

---

## 4. Guía de Inicio Rápido (Local Development)

Siga estas instrucciones para levantar el entorno de desarrollo local.

### Prerequisitos
*   Python 3.9 o superior.
*   Gestor de paquetes `pip` y entorno virtual.

### Setup de Entorno

```bash
# 1. Clonar el repositorio
git clone <repository_url>
cd Proyecto_Final

# 2. Crear y activar el entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: .\venv\Scripts\activate

# 3. Instalar las dependencias estrictas
pip install -r requirements.txt

# 4. (Opcional) Ejecutar pipeline de reentrenamiento del modelo
python src/retrenar_modelo.py

# 5. Levantar el servidor de desarrollo
streamlit run src/app.py
```

El servidor estará disponible en `http://localhost:8501`.

### Ejecución con Docker (Recomendado)

La aplicación cuenta con soporte nativo para contenedores e incluye resolución dinámica de rutas para bases de datos locales (`SQLite`), haciéndola 100% *cross-platform*.

```bash
# 1. Construir la imagen optimizada
docker build -t quant-platform:latest .

# 2. Levantar el contenedor
docker run -p 8501:8501 quant-platform:latest
```

El dashboard estará accesible en `http://localhost:8501`.

---

## 5. Estrategia de Testing y Calidad

Para asegurar la confiabilidad matemática de los modelos, el sistema debe regirse por los siguientes umbrales y tipos de pruebas:

*   **Pruebas Unitarias (Pytest):** Cobertura mínima esperada: **85%**. Enfocadas en verificar la pureza matemática de las funciones en `simulation.py` (ej. asegurar que el cálculo del *Drift* sea coherente con la volatilidad base) y la precisión de los indicadores en `indicators.py`.
*   **Pruebas de Integración:** Validar el contrato de datos entre la descarga web (`yfinance`) y el fallback local (`SQLite`). Asegurar que los DataFrames devueltos compartan idéntico esquema, índices temporales y manejo de NaNs.
*   **Pruebas de Seguridad (Data Sanitization):** Validación estricta para evitar la inyección de `np.inf` y `NaN` en las matrices de features del modelo XGBoost, previniendo *segmentation faults* o cálculos corruptos en producción.

---

## 6. Pipeline de CI/CD y Deployment

### Continuous Integration (GitHub Actions)
En cada `Push` o `Pull Request` hacia la rama principal, se ejecutarán flujos automatizados:
1.  **Code Linting:** `flake8` y `black` para asegurar adherencia al PEP-8.
2.  **Ejecución de Tests:** Corridas completas de `pytest`.
3.  **Análisis Estático:** Uso de `bandit` para identificar vulnerabilidades de seguridad en el código Python.

### Deployment Strategy (Docker & Serverless)
Para ambientes de producción, la aplicación está diseñada para ser *Stateless* (con la excepción de la caché en memoria).
1.  **Containerización:** El repositorio incluye un `Dockerfile` optimizado (basado en `python:3.10-slim`) y un `.dockerignore` estricto. El contenedor gestiona dependencias del SO, caché de capas en Python y expone el servicio en el puerto 8501 sin requerir configuraciones adicionales.
2.  **Hosting Recomendado:** Para soportar picos de carga (análisis concurrentes), se recomienda desplegar la imagen en plataformas de contenedores serverless como **AWS ECS Fargate** o **Google Cloud Run**, configurando políticas de auto-scaling basadas en utilización de CPU.

---

## 7. Guía de Contribución y Estilo

Todo desarrollo dentro de este repositorio debe adherirse estrictamente a las convenciones institucionales para asegurar la legibilidad y mantenibilidad a largo plazo.

### Flujo de Trabajo (Trunk-based Development)
*   Las características de corta duración se ramifican desde `main` (`feature/nombre-corto`).
*   Integración rápida y continua: Evitamos ramas de largo ciclo de vida para minimizar el *merge conflict hell*.
*   **Code Review Obligatorio:** Ningún PR puede fusionarse a `main` sin la revisión y aprobación técnica de al menos un ingeniero (L5+).

### Convenciones de Git (Conventional Commits)
Los mensajes de commit deben seguir el estándar para facilitar la autogeneración de *Changelogs*.
*   `feat: [Módulo] Añade nueva simulación de estrés de liquidez`
*   `fix: [Datos] Corrige manejo de fechas NaN en descarga de yfinance`
*   `refactor: [UI] Optimiza renderizado de la grilla de métricas clave`
*   `perf: [Simulación] Vectoriza cálculo de percentiles reduciendo tiempo en 40%`