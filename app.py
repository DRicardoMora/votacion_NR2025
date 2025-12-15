import streamlit as st
import pandas as pd
# Importamos la librería clave para interactuar con Google Sheets
from streamlit_gsheets import GSheetsConnection 

# --- CONFIGURACIÓN Y CONEXIÓN ---
TITULO = "🏆 Votación: Disco Favorito 2025 Nación Rock"
HOJA_NOMBRE = "Sheet1" # Nombre de la hoja de cálculo
# El ID de la hoja se obtiene automáticamente de st.secrets["spreadsheet_id"]

# Inicializar conexión con Google Sheets
# Se asume que los secretos están configurados en [gcp_service_account]
conn = st.connection("gsheets", type=GSheetsConnection) 

# --- FUNCIONES DE LECTURA Y ESCRITURA ---

@st.cache_data(ttl=5) # Cacheamos la lectura por 5 segundos para reducir peticiones
def cargar_datos():
    """Carga los datos de Google Sheets."""
    try:
        # Lee los datos de la hoja configurada con el ID del secreto.
        # Usa headers=1 para tomar la primera fila como nombres de columna.
        df = conn.read(worksheet=HOJA_NOMBRE, usecols=list(range(4)), ttl=5) 
        
        # Proceso de limpieza similar al anterior
        df = df.dropna(how="all") # Elimina filas completamente vacías
        df['votos'] = pd.to_numeric(df['votos'], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos de Google Sheets: {e}")
        return pd.DataFrame(columns=['artista', 'album', 'url_portada', 'votos'])

def guardar_datos(df):
    """Guarda el DataFrame actualizado a Google Sheets."""
    try:
        # Escribe todo el DataFrame de vuelta a la hoja de cálculo
        conn.write(data=df, worksheet=HOJA_NOMBRE)
        return True
    except Exception as e:
        st.error(f"Error al guardar datos en Google Sheets: {e}")
        return False

# Usamos Session State para cargar y mantener el DataFrame
# Esto permite que la interfaz muestre el estado actual sin recargar GSheets constantemente
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
    # 1. Necesitamos cargar la versión más reciente de GSheets (la que tiene más votos)
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
            # Nota: Usar el index 'i' para el key del botón es crucial
            if st.button("Votar", key=f"voto_{i}"):
                votar_album(i)
                
            # Muestra el conteo de votos (de la Session State)
            st.info(f"Votos: {row['votos']}")
            st.markdown("---")
            
# --- Sección de Resultados (Barra Lateral) ---
st.sidebar.header("Resultados (Top 5)")
if not df_display.empty:
    # Ordenar y mostrar los resultados más recientes del Session State
    df_resultados = df_display.sort_values(by='votos', ascending=False).head(5)
    # Se debe resetear el índice para que muestre la tabla correctamente
    st.sidebar.dataframe(df_resultados[['album', 'votos']].reset_index(drop=True), hide_index=True)

# Añade un botón para forzar la actualización de los datos de GSheets
if st.sidebar.button("Actualizar Votos de GSheets"):
    # Limpia el cache y fuerza la recarga de los datos de la fuente
    st.cache_data.clear()
    st.session_state.df = cargar_datos()
    st.rerun() # Fuerza el refresco de toda la aplicación para mostrar los nuevos datos