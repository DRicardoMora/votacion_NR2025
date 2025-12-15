import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN ---
TITULO = "🏆 Votación: Disco Favorito 2025 Nación Rock"
HOJA_NOMBRE = "Sheet1"

st.set_page_config(layout="wide", page_title=TITULO)

# --- AUTH GCP ---
@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)

gc = get_gspread_client()

# --- FUNCIONES DE LECTURA Y ESCRITURA ---

@st.cache_data(ttl=5)
def cargar_datos():
    try:
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        worksheet = sh.worksheet(HOJA_NOMBRE)

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        df = df.dropna(how="all")

        if "votos" not in df.columns:
            df["votos"] = 0

        df["votos"] = (
            pd.to_numeric(df["votos"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

        return df

    except Exception as e:
        st.error(
            "Error al cargar datos de Google Sheets. "
            "Revisa permisos del Service Account y el nombre de la hoja."
        )
        st.exception(e)
        return pd.DataFrame(
            columns=["artista", "album", "url_portada", "votos"]
        )


def guardar_datos(df):
    try:
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        worksheet = sh.worksheet(HOJA_NOMBRE)

        data_to_write = [df.columns.tolist()] + df.values.tolist()
        worksheet.update("A1", data_to_write)

        return True

    except Exception as e:
        st.error("Error al guardar datos en Google Sheets.")
        st.exception(e)
        return False


# --- SESSION STATE ---
if "df" not in st.session_state:
    st.session_state.df = cargar_datos()

# --- UI ---
st.title(TITULO)
st.markdown("---")


def votar_album(index):
    st.cache_data.clear()
    df_actualizado = cargar_datos()

    if index in df_actualizado.index:
        df_actualizado.loc[index, "votos"] += 1
        album_votado = df_actualizado.loc[index, "album"]

        if guardar_datos(df_actualizado):
            st.session_state.df = df_actualizado
            st.toast(f"¡Voto registrado para {album_votado}!", icon="✅")
        else:
            st.toast("No se pudo guardar el voto.", icon="❌")


df_display = st.session_state.df
columnas_por_fila = 3
cols = st.columns(columnas_por_fila)

if df_display.empty:
    st.warning(
        "No hay datos. Verifica que el Google Sheet tenga información válida."
    )
else:
    for i, row in df_display.iterrows():
        col = cols[i % columnas_por_fila]

        with col:
            st.markdown(f"**{row['album']}**")
            st.caption(row["artista"])

            if pd.notna(row.get("url_portada")) and row["url_portada"]:
                st.image(row["url_portada"], width=200)
            else:
                st.warning("No hay portada disponible.")

            if st.button("Votar", key=f"voto_{i}"):
                votar_album(i)
                st.rerun()

            st.info(f"Votos: {row['votos']}")
            st.markdown("---")


# --- SIDEBAR ---
st.sidebar.header("Resultados (Top 5)")

if not df_display.empty:
    df_resultados = (
        df_display.sort_values(by="votos", ascending=False)
        .head(5)
        .reset_index(drop=True)
    )
    st.sidebar.dataframe(
        df_resultados[["album", "votos"]],
        hide_index=True,
    )

if st.sidebar.button("Actualizar votos desde GSheets"):
    st.cache_data.clear()
    st.session_state.df = cargar_datos()
    st.rerun()
