import qrcode

# 1. El enlace de tu plataforma
url = "https://oraculo-financiero.onrender.com"

# 2. Configurar la calidad y tamaño del QR
qr = qrcode.QRCode(
    version=1, 
    error_correction=qrcode.constants.ERROR_CORRECT_H, # Alta corrección de errores
    box_size=15, # Hace la imagen más grande y nítida
    border=4,    # Margen blanco estándar alrededor del QR
)

# 3. Ensamblar los datos
qr.add_data(url)
qr.make(fit=True)

# 4. Crear la imagen final (puedes cambiar los colores si quieres)
img = qr.make_image(fill_color="black", back_color="white")

# 5. Guardar la imagen en tu computadora
img.save("qr_oraculo.png")

print("¡Éxito! El archivo 'qr_oraculo.png' se ha creado en tu carpeta.")