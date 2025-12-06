# app.py
import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard Club Fitness", layout="wide")

# -------------------------
# Configuración de conexión
# -------------------------
DB_CONFIG = {
    "user": "sql10810884",
    "password": "9ZKaWJmkeq",
    "host": "sql10.freesqldatabase.com",
    "port": 3306,
    "database": "sql10810884",
}

# Crear engine SQLAlchemy (requiere pymysql)
@st.cache_resource
def get_engine():
    conn_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    return engine

# Query principal: unimos asistencia -> socio -> socio_clases -> clases -> instructor
# Observación: la tabla 'asistencia' no tiene id_clase en tu SQL, por eso usamos socios_clases para relacionar.
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
    # Asegurar tipos
    if 'fecha_inicio' in df.columns:
        df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio']).dt.date
    if 'hora_inicio' in df.columns:
        df['hora_inicio'] = pd.to_datetime(df['hora_inicio'])
    return df

# -------------------------
# UI: Sidebar - filtros
# -------------------------
st.title("Dashboard - Club Fitness")
st.markdown("Visualización de asistencias — Streamlit app (PARTE 5)")

df = load_data()

# Si el join no devolvió clases/instructores, avisamos
if df.empty:
    st.warning("La consulta no devolvió registros. Verifica conexión y que la BD contiene datos.")
else:
    # Sidebar filtros
    st.sidebar.header("Filtros")
    min_date = df['fecha_inicio'].min()
    max_date = df['fecha_inicio'].max()
    date_range = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    # Manejar caso un solo date_input devuelve un date en vez de tupla
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_range, date_range

    clases = df['clase'].dropna().unique().tolist()
    instrs = df['instructor'].dropna().unique().tolist()

    selected_clases = st.sidebar.multiselect("Clase", options=sorted(clases), default=sorted(clases))
    selected_instr = st.sidebar.multiselect("Instructor", options=sorted(instrs), default=sorted(instrs))

    # Aplicar filtros
    filt = pd.Series(True, index=df.index)
    if start_date:
        filt &= df['fecha_inicio'] >= pd.to_datetime(start_date).date()
    if end_date:
        filt &= df['fecha_inicio'] <= pd.to_datetime(end_date).date()
    if selected_clases:
        filt &= df['clase'].isin(selected_clases)
    if selected_instr:
        filt &= df['instructor'].isin(selected_instr)

    df_filtered = df[filt].copy()

    # -------------------------
    # KPIs
    # -------------------------
    st.subheader("Indicadores (KPIs)")
    col1, col2, col3 = st.columns(3)
    total_asistencias = len(df_filtered)
    distinct_socios = df_filtered['id_socios'].nunique()
    # Clase con más asistencias (cuando clase sea NaN lo ignoramos)
    clase_mas_asist = df_filtered.groupby('clase').size().sort_values(ascending=False)
    clase_top = clase_mas_asist.index[0] if not clase_mas_asist.empty else "N/A"
    col1.metric("Total asistencias registradas", total_asistencias)
    col2.metric("Socios distintos (filtrados)", distinct_socios)
    col3.metric("Clase con mayor asistencias", clase_top)

    st.markdown("---")

    # -------------------------
    # Tabla de datos
    # -------------------------
    st.subheader("Tabla de datos (origen)")
    st.dataframe(df_filtered.reset_index(drop=True), use_container_width=True)

    # Botón para descargar CSV de los datos filtrados
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar datos filtrados (CSV)", data=csv, file_name="asistencias_filtradas.csv", mime="text/csv")

    # -------------------------
    # Gráficos
    # -------------------------
    st.subheader("Gráficos")

    # 1) Gráfico de barras: número de asistencias por clase
    st.markdown("**Asistencias por Clase (barras)**")
    bar_df = df_filtered.dropna(subset=['clase']).groupby('clase').size().reset_index(name='asistencias')
    if bar_df.empty:
        st.info("No hay datos de clase para mostrar en el gráfico de barras.")
    else:
        fig_bar = px.bar(bar_df, x='clase', y='asistencias', title="Asistencias por clase", labels={'clase':'Clase','asistencias':'Asistencias'})
        st.plotly_chart(fig_bar, use_container_width=True)

    # 2) Pie: número de asistencias por instructor
    st.markdown("**Asistencias por Instructor (pie)**")
    pie_df = df_filtered.dropna(subset=['instructor']).groupby('instructor').size().reset_index(name='asistencias')
    if pie_df.empty:
        st.info("No hay datos de instructor para mostrar en pie chart.")
    else:
        fig_pie = px.pie(pie_df, values='asistencias', names='instructor', title="Asistencias por instructor")
        st.plotly_chart(fig_pie, use_container_width=True)

    # 3) Línea: número de asistencias por fecha
    st.markdown("**Asistencias por Fecha (línea)**")
    line_df = df_filtered.groupby('fecha_inicio').size().reset_index(name='asistencias').sort_values('fecha_inicio')
    if line_df.empty:
        st.info("No hay datos por fecha para mostrar.")
    else:
        fig_line = px.line(line_df, x='fecha_inicio', y='asistencias', markers=True, title="Asistencias por fecha", labels={'fecha_inicio':'Fecha','asistencias':'Asistencias'})
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    st.caption("Query usada para obtener datos: unión entre asistencia → socio → socios_clases → clases → instructor. Si la relación 'asistencia → clase' está explícita en tu esquema, modifica la query MAIN_QUERY en app.py accordingly.")
