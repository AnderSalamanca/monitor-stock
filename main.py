import requests
from bs4 import BeautifulSoup
import json
import os
import sys

# --- CONFIGURACIÓN ---
URL_OBJETIVO = "https://outlet-pc.es/collections/tarjetas-graficas"
ARCHIVO_DATOS = "vistos.json"
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')

# Headers básicos para simular navegador
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def cargar_vistos():
    if not os.path.exists(ARCHIVO_DATOS):
        return []
    try:
        with open(ARCHIVO_DATOS, 'r') as f:
            return json.load(f)
    except:
        return []

def guardar_vistos(lista):
    with open(ARCHIVO_DATOS, 'w') as f:
        json.dump(lista, f)

def notificar_discord(producto):
    if not WEBHOOK_URL:
        print("Falta configurar el Webhook de Discord.")
        return

    embed = {
        "title": producto['nombre'],
        "url": producto['link'],
        "description": "¡Nuevo producto detectado en la sección!",
        "color": 5814783, # Color verde
        "fields": [
            {
                "name": "Precio",
                "value": producto['precio'],
                "inline": True
            }
        ],
        "footer": {
            "text": "Monitor de Stock - Outlet PC"
        }
    }
    
    data = {
        "content": "🚨 **STOCK DETECTADO** 🚨",
        "embeds": [embed]
    }
    
    try:
        requests.post(WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"Error enviando a Discord: {e}")

def check_stock():
    print(f"Consultando {URL_OBJETIVO}...")
    try:
        response = requests.get(URL_OBJETIVO, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error cargando la web: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # --- LÓGICA NUEVA PARA SHOPIFY ---
    # En Shopify, los productos son enlaces que contienen '/products/' en su href.
    # Buscamos todos los enlaces que cumplan eso dentro de la zona principal.
    
    productos_encontrados = []
    links_procesados = set() # Para evitar duplicados (imagen + título suelen ser 2 links al mismo sitio)

    # Buscamos enlaces que contengan '/products/'
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        # Filtramos para asegurarnos que es un producto y no basura
        if '/products/' in href and 'collections' not in href:
            
            # Normalizamos la URL (a veces vienen relativas)
            full_link = f"https://outlet-pc.es{href}" if href.startswith('/') else href
            
            # Si ya procesamos este link en esta pasada, saltar
            if full_link in links_procesados:
                continue
            
            links_procesados.add(full_link)

            # Intentamos sacar el nombre y precio
            # A veces el nombre está dentro del <a> o en un div cercano.
            # Estrategia genérica: buscar el texto del enlace o buscar un título hijo
            nombre = a_tag.get_text(strip=True)
            
            # Si el link no tiene texto (ej: es la imagen), buscamos el siguiente link que suele ser el título
            if not nombre:
                continue 

            # Limpiamos nombre muy largo o sucio
            if len(nombre) < 3: 
                continue

            # Precio: En esta web suele estar cerca, pero para no fallar,
            # pondremos "Consultar en web" si no lo parseamos fácil, 
            # lo importante es que avise del stock.
            precio = "Ver en web" 
            
            # ID único del producto (usamos la parte final de la URL)
            product_id = href.split('/')[-1].split('?')[0]

            productos_encontrados.append({
                'id': product_id,
                'nombre': nombre,
                'link': full_link,
                'precio': precio
            })

    print(f"Encontrados {len(productos_encontrados)} posibles productos.")
    
    vistos_antiguos = cargar_vistos()
    vistos_nuevos = [p['id'] for p in productos_encontrados]
    
    hay_novedades = False

    for prod in productos_encontrados:
        if prod['id'] not in vistos_antiguos:
            print(f"NUEVO: {prod['nombre']}")
            notificar_discord(prod)
            hay_novedades = True
    
    # Actualizamos el archivo json solo si hemos encontrado productos (para no borrar la base de datos si la web falla)
    if len(vistos_nuevos) > 0:
        if hay_novedades or not vistos_antiguos:
            print("Guardando nueva lista de vistos...")
            guardar_vistos(vistos_nuevos)
        else:
            print("Sin novedades.")
    else:
        print("Cuidado: No se detectó ningún producto. Posible cambio en la web o bloqueo.")

if __name__ == "__main__":
    check_stock()