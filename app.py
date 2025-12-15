import streamlit as st
import pandas as pd
# Importamos gspread para el cliente de la API que usaremos internamente
import gspread 

# --- CONFIGURACIÓN Y CONEXIÓN ---
TITULO = "🏆 Votación: Disco Favorito 2025 Nación Rock"
HOJA_NOMBRE = "Sheet1" # Nombre de la hoja de cálculo

# Inicializar conexión con Streamlit usando el tipo 'json'
# Esto permite que Streamlit gestione la autenticación del Service Account
# y nos dé acceso al cliente de gspread (conn.client())
conn = st.connection("gsheets", type="json", ttl=5) 

# --- FUNCIONES DE LECTURA Y ESCRITURA ---

# Cacheamos la lectura por 5 segundos para reducir peticiones a Google Sheets
@st.cache_data(ttl=5) 
def cargar_datos():
    """Carga los datos de Google Sheets usando el cliente gspread."""
    try:
        # 1. Obtener el cliente gspread autenticado
        gc = conn.client() 
        # 2. Abrir la hoja de cálculo usando el ID guardado en st.secrets
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        # 3. Seleccionar la hoja (worksheet) por su nombre
        worksheet = sh.worksheet(HOJA_NOMBRE)
        
        # 4. Obtener todos los valores. get_all_records() devuelve una lista de diccionarios.
        data = worksheet.get_all_records()
        df = pd.DataFrame(data) 
        
        # Proceso de limpieza: asegura el tipo de dato para 'votos'
        df = df.dropna(how="all") 
        df['votos'] = pd.to_numeric(df['votos'], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos de Google Sheets. Verifica secretos y permisos: {e}")
        return pd.DataFrame(columns=['artista', 'album', 'url_portada', 'votos'])

def guardar_datos(df):
    """Guarda el DataFrame actualizado a Google Sheets."""
    try:
        gc = conn.client() 
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        worksheet = sh.worksheet(HOJA_NOMBRE)

        # 1. Convertir el DataFrame a una lista de listas, incluyendo las cabeceras (columnas)
        data_to_write = [df.columns.values.tolist()] + df.values.tolist()

        # 2. Escribir los datos de vuelta, empezando desde la celda 'A1'
        # Esto reemplaza todo el contenido de la hoja
        worksheet.update('A1', data_to_write)
        return True
    except Exception as e:
        st.error(f"Error al guardar datos en Google Sheets: {e}")
        return False

# Usamos Session State para cargar y mantener el DataFrame
# Se carga una sola vez al inicio de la sesión
if 'df' not in st.session_state:
    st.session_state.df = cargar_datos()

st.set_page_config(layout="wide", page_title=TITULO)
st.title(TITULO)
st.markdown("---")

# --- FUNCIÓN DE VOTO ---
def votar_album(index):
    """
    Incrementa el contador de votos para el índice dado, actualiza y guarda en GSheets.
    """
    # 1. Cargar la versión más reciente (rompe el caché temporalmente si es necesario)
    # Debemos llamar a cargar_datos() sin usar caché aquí para obtener la versión más actual de GSheets
    # Sin embargo, dado que cargar_datos tiene ttl=5, si votan dos veces en 5s, el segundo voto se perderá.
    # Por ahora, mantenemos la llamada normal.
    st.cache_data.clear() # Limpiamos el caché antes de cargar para obtener la versión más nueva
    df_actualizado = cargar_datos()
    
    # 2. Incrementar el voto en esa versión
    if index in df_actualizado.index:
        df_actualizado.loc[index, 'votos'] += 1
        album_votado = df_actualizado.loc[index, 'album']
        
        # 3. Guardar el archivo en Google Sheets
        if guardar_datos(df_actualizado):
            # 4. Actualizar el DataFrame en la Session State y notificar
            st.session_state.df = df_actualizado
            st.toast(f"¡Voto registrado para {album_votado}!", icon="✅")
        else:
            st.toast("⚠️ No se pudo guardar el voto.", icon="❌")

# --- INTERFAZ DE VOTACIÓN ---
df_display = st.session_state.df # Usamos la versión del Session State
columnas_por_fila = 3
cols = st.columns(columnas_por_fila)

if df_display.empty:
    st.warning("Asegúrate de que Google Sheet tenga datos y la conexión esté configurada correctamente.")
else:
    for i, row in df_display.iterrows():
        col = cols[i % columnas_por_fila]
        
        with col:
            # Título del Álbum y Artista
            st.markdown(f"**{row['album']}**")
            st.caption(row['artista'])
            
            # Portada del Álbum
            if pd.notna(row['url_portada']) and row['url_portada']:
                st.image(row['url_portada'], width=200)
            else:
                st.warning("No hay portada disponible.")

            # Botón de Voto
            if st.button("Votar", key=f"voto_{i}"):
                votar_album(i)
                st.rerun() # Forzar el refresco para mostrar el voto actualizado
                
            # Muestra el conteo de votos (de la Session State)
            st.info(f"Votos: {row['votos']}")
            st.markdown("---")
            
# --- Sección de Resultados (Barra Lateral) ---
st.sidebar.header("Resultados (Top 5)")
if not df_display.empty:
    # Ordenar y mostrar los resultados más recientes del Session State
    df_resultados = df_display.sort_values(by='votos', ascending=False).head(5)
    st.sidebar.dataframe(df_resultados[['album', 'votos']].reset_index(drop=True), hide_index=True)

# Añade un botón para forzar la actualización de los datos de GSheets
if st.sidebar.button("Actualizar Votos de GSheets"):
    # Limpia el cache y fuerza la recarga de los datos de la fuente
    st.cache_data.clear()
    st.session_state.df = cargar_datos()
    st.rerun() # Fuerza el refresco de toda la aplicación para mostrar los nuevos datos