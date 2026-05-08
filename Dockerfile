# Usa una imagen base oficial de Python ligera
FROM python:3.10-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema operativo necesarias para compilar ciertos paquetes
# y para utilidades de red si son requeridas
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia primero los archivos de requerimientos para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto al contenedor
COPY . .

# Expone el puerto por defecto de Streamlit
EXPOSE 8501

# Configura las variables de entorno de Streamlit para que se ejecute correctamente en Docker
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Define el comando para ejecutar la aplicación
CMD ["streamlit", "run", "src/app.py"]
