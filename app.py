import streamlit as st
import pandas as pd
import os

# --- CONFIGURACIÓN Y CARGA DE DATOS ---
TITULO = "🏆 Votación: Disco Favorito 2025 Nación Rock"
ARCHIVO_CSV = "topdiscos_nacionrock.csv" 

# 🚨 CORRECCIÓN CLAVE: Eliminamos el decorador @st.cache_data
# para que los datos se lean del disco (CSV) en cada interacción.
def cargar_datos():
    """Carga los datos del CSV y asegura el tipo de dato para 'votos'."""
    if os.path.exists(ARCHIVO_CSV):
        df = pd.read_csv(ARCHIVO_CSV)
        # Asegura que la columna de votos sea numérica (importante para sumar)
        df['votos'] = pd.to_numeric(df['votos'], errors='coerce').fillna(0).astype(int)
        return df
    st.error(f"Error: No se encontró el archivo '{ARCHIVO_CSV}'.")
    return pd.DataFrame(columns=['artista', 'album', 'url_portada', 'votos'])

def guardar_datos(df):
    """Guarda el DataFrame actualizado al archivo CSV."""
    df.to_csv(ARCHIVO_CSV, index=False)

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
    Incrementa el contador de votos para el índice dado y guarda el archivo.
    """
    # 1. Necesitamos cargar la versión más reciente del disco (CSV)
    df_actualizado = cargar_datos()
    
    # 2. Incrementar el voto en esa versión
    if index in df_actualizado.index:
        df_actualizado.loc[index, 'votos'] += 1
        
        # 3. Guardar el archivo CSV
        guardar_datos(df_actualizado)
        
        # 4. Actualizar el DataFrame en la Session State y forzar el refresco de la app
        st.session_state.df = df_actualizado
        st.toast(f"¡Voto registrado para {df_actualizado.loc[index, 'album']}!", icon="✅")
        # El botón de Streamlit ya causa un rerun, no necesitamos forzarlo
        
# --- INTERFAZ DE VOTACIÓN ---
df_display = st.session_state.df # Usamos la versión del Session State
columnas_por_fila = 3
cols = st.columns(columnas_por_fila)

if df_display.empty:
    st.warning("Asegúrate de que el CSV tenga datos y el nombre sea correcto.")
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
            
            # Muestra el conteo de votos
            st.info(f"Votos: {row['votos']}")
            st.markdown("---")

# --- Sección de Resultados (Barra Lateral) ---
st.sidebar.header("Resultados (Top 5)")
if not df_display.empty:
    # Ordenar y mostrar los resultados más recientes del Session State
    df_resultados = df_display.sort_values(by='votos', ascending=False).head(5)
    st.sidebar.dataframe(df_resultados[['album', 'votos']].reset_index(drop=True), hide_index=True)