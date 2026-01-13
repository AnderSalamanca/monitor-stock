import requests
from bs4 import BeautifulSoup
import json
import os
import sys

# Configuración
URL_OBJETIVO = "https://outlet-pc.es/collections/tarjetas-graficas" # Cambia esto a la categoría exacta que quieras
ARCHIVO_DATOS = "vistos.json"
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')

# Headers para parecer un navegador real (Importante para que no te bloqueen)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def cargar_vistos():
    if not os.path.exists(ARCHIVO_DATOS):
        return []
    with open(ARCHIVO_DATOS, 'r') as f:
        return json.load(f)

def guardar_vistos(lista):
    with open(ARCHIVO_DATOS, 'w') as f:
        json.dump(lista, f)

def notificar_discord(producto):
    data = {
        "content": "🚨 **NUEVO PRODUCTO DETECTADO** 🚨",
        "embeds": [{
            "title": producto['nombre'],
            "url": producto['link'],
            "description": f"Precio: {producto['precio']}",
            "color": 5814783
        }]
    }
    requests.post(WEBHOOK_URL, json=data)

def check_stock():
    print(f"Consultando {URL_OBJETIVO}...")
    try:
        response = requests.get(URL_OBJETIVO, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error cargando la web: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # IMPORTANTE: Aquí buscamos los elementos HTML. 
    # En Outlet PC los productos suelen estar en artículos con clase 'product-miniature'
    # Esto puede cambiar si ellos actualizan su web.
    productos_html = soup.find_all('article', class_='product-miniature')
    
    vistos_antiguos = cargar_vistos()
    vistos_nuevos = []
    nuevos_encontrados = False

    print(f"Encontrados {len(productos_html)} productos en la web.")

    for prod in productos_html:
        try:
            # Extraer datos (esto depende de la estructura HTML de la web)
            tag_a = prod.find('a', class_='product-name')
            nombre = tag_a.text.strip()
            link = tag_a['href']
            
            # El ID suele ser único para identificar el producto
            product_id = prod['data-id-product'] 
            
            # Buscar precio
            precio = prod.find('span', class_='price').text.strip()

            # Guardamos el ID en la lista nueva para la próxima vez
            vistos_nuevos.append(product_id)

            # Lógica: Si el ID no estaba en la lista antigua, es NUEVO
            if product_id not in vistos_antiguos:
                print(f"NUEVO: {nombre}")
                notificar_discord({'nombre': nombre, 'link': link, 'precio': precio})
                nuevos_encontrados = True
                
        except Exception as e:
            print(f"Error parseando un producto: {e}")
            continue

    # Si encontramos nuevos, o es la primera vez (lista vacía), actualizamos el archivo
    if nuevos_encontrados or not vistos_antiguos:
        print("Actualizando base de datos local...")
        guardar_vistos(vistos_nuevos)
    else:
        print("Sin novedades.")

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("Error: Falta el secreto DISCORD_WEBHOOK")
        sys.exit(1)
    check_stock()