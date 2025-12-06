# app.py
import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import plotly.express as px
from datetime import datetime

# ----------------------------------------------
# CONFIGURACIÓN DE ESTILO (AZUL MARINO)
# ----------------------------------------------
st.set_page_config(page_title="Dashboard Club Fitness", layout="wide")

# CSS para personalizar colores
st.markdown("""
    <style>

        /* Fondo general negro */
        body, .main, .stApp {
            background-color: #000000 !important;
        }

        /* Letras blancas en toda la aplicación */
        h1, h2, h3, h4, h5, h6, p, span, div, label {
            color: #FFFFFF !important;
        }

        /* Sidebar texto blanco */
        .css-1d391kg, .css-1y4p8pa, .css-1lcbmhc, .css-qrbaxs {
            color: #FFFFFF !important;
        }

        /* KPIs blancos con borde azul */
        .stMetric {
            background-color: #111111 !important;
            color: #FFFFFF !important;
            padding: 15px;
            border-radius: 12px;
            border: 2px solid #185ADB !important;
        }

        /* Expanders — fondo oscuro y borde azul marino */
        .stExpander {
            background-color: #111111 !important;
            border: 2px solid #185ADB !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
        }

        /* Encabezado de expander en blanco */
        summary {
            color: #FFFFFF !important;
        }

        /* Tablas en azul marino */
        .stDataFrame, .stTable {
            background-color: #0A2342 !important;
            color: #FFFFFF !important;
            border-radius: 10px;
            padding: 10px;
        }

        /* Scrollbars oscuras */
        ::-webkit-scrollbar {
            width: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #000000;
        }
        ::-webkit-scrollbar-thumb {
            background: #185ADB;
            border-radius: 5px;
        }

    </style>
""", unsafe_allow_html=True)

# Paleta para Plotly
COLOR_MARINO = ["#0A2342", "#185ADB", "#39A9DB", "#A2D6F9"]

# ----------------------------------------------
# CONEXIÓN A BASE DE DATOS
# ----------------------------------------------
DB_CONFIG = {
    "user": "sql10810884",
    "password": "9ZKaWJmkeq",
    "host": "sql10.freesqldatabase.com",
    "port": 3306,
    "database": "sql10810884",
}

@st.cache_resource
def get_engine():
    conn_str = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(conn_str)

MAIN_QUERY = """
SELECT 
    a.id_asistencia,
    a.fecha_inicio,
    a.hora_inicio,
    a.intensidad_percibida,
    s.id_socios,
    CONCAT(s.nombre, ' ', IFNULL(s.apellido_paterno,'')) AS socio,
    c.id_clase,
    c.nombre AS clase,
    c.zona AS sala,
    i.id_instructor,
    CONCAT(i.nombre, ' ', IFNULL(i.apellido_paterno,'')) AS instructor
FROM asistencia a
JOIN socios s ON a.id_socio = s.id_socios
LEFT JOIN socios_clases sc ON sc.id_socio = s.id_socios
LEFT JOIN clases c ON sc.id_clase = c.id_clase
LEFT JOIN instructor i ON c.id_instructor = i.id_instructor
ORDER BY a.fecha_inicio, a.hora_inicio;
"""

@st.cache_data(ttl=600)
def load_data():
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(MAIN_QUERY), conn)
    df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio']).dt.date
    return df


# ----------------------------------------------
# TÍTULO PRINCIPAL
# ----------------------------------------------
st.title("📊 Dashboard de Asistencias – Club Fitness")


# ----------------------------------------------
# Cargar Datos
# ----------------------------------------------
df = load_data()

if df.empty:
    st.error("❌ No se encontraron datos en la base.")
    st.stop()

# ----------------------------------------------
# SIDEBAR - FILTROS
# ----------------------------------------------
st.sidebar.header("🔎 Filtros")

min_date, max_date = df['fecha_inicio'].min(), df['fecha_inicio'].max()
date_range = st.sidebar.date_input("Rango de fechas", (min_date, max_date))

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

selected_clases = st.sidebar.multiselect("Clase", df['clase'].dropna().unique())
selected_instr = st.sidebar.multiselect("Instructor", df['instructor'].dropna().unique())

# Aplicación de filtros
filt = pd.Series(True, index=df.index)
filt &= df['fecha_inicio'] >= start_date
filt &= df['fecha_inicio'] <= end_date

if selected_clases:
    filt &= df['clase'].isin(selected_clases)
if selected_instr:
    filt &= df['instructor'].isin(selected_instr)

df_filtered = df[filt]


# ----------------------------------------------
# KPIs (en expander)
# ----------------------------------------------
with st.expander("📌 Indicadores / KPIs (clic para abrir)", expanded=True):
    col1, col2, col3 = st.columns(3)

    col1.metric("Total de Asistencias", len(df_filtered))
    col2.metric("Socios Distintos", df_filtered['id_socios'].nunique())

    clase_top = (
        df_filtered['clase'].value_counts().idxmax()
        if df_filtered['clase'].notna().any()
        else "N/A"
    )
    col3.metric("Clase con Más Asistencias", clase_top)


# ----------------------------------------------
# TABLA DE DATOS
# ----------------------------------------------
with st.expander("📄 Tabla de Datos (clic para mostrar/ocultar)", expanded=False):
    st.dataframe(df_filtered, use_container_width=True)


# ----------------------------------------------
# GRÁFICOS
# ----------------------------------------------
st.subheader("📈 Visualizaciones")

# ----------- 1. BARRAS -----------
bar_df = df_filtered.groupby('clase').size().reset_index(name="asistencias")

with st.expander("📊 Asistencias por Clase (Barras)"):
    if bar_df.empty:
        st.info("No hay datos suficientes.")
    else:
        fig = px.bar(
            bar_df,
            x="clase",
            y="asistencias",
            title="Asistencias por Clase",
            color="clase",
            color_discrete_sequence=COLOR_MARINO,
        )
        st.plotly_chart(fig, use_container_width=True)

# ----------- 2. PIE CHART -----------
pie_df = df_filtered.groupby('instructor').size().reset_index(name="asistencias")

with st.expander("🧩 Asistencias por Instructor (Pie Chart)"):
    if pie_df.empty:
        st.info("No hay datos suficientes.")
    else:
        fig = px.pie(
            pie_df,
            values="asistencias",
            names="instructor",
            title="Asistencias por Instructor",
            color_discrete_sequence=COLOR_MARINO,
        )
        st.plotly_chart(fig, use_container_width=True)

# ----------- 3. LÍNEA -----------
line_df = df_filtered.groupby("fecha_inicio").size().reset_index(name="asistencias")

with st.expander("📈 Asistencias por Fecha (Línea)"):
    if line_df.empty:
        st.info("No hay datos suficientes.")
    else:
        fig = px.line(
            line_df,
            x="fecha_inicio",
            y="asistencias",
            markers=True,
            title="Asistencias por Fecha",
            color_discrete_sequence=["#185ADB"],
        )
        st.plotly_chart(fig, use_container_width=True)
