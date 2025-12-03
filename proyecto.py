import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(page_title="Hotel – Dashboard con menú", layout="wide")

# ------------------------------------------------------------
# ESTILO BEIGE / CAFÉ + LETRAS
# ------------------------------------------------------------
st.markdown("""
<style>
/* Fondo general beige café */
.stApp {
    background-color: #e8d9c4 !important;
}

/* Contenido principal: texto oscuro */
.block-container {
    color: #2b1a0f !important;
}
h1, h2, h3, h4, h5, h6, p, span, label {
    color: #2b1a0f !important;
}

/* Sidebar café con letras blancas */
[data-testid="stSidebar"] {
    background-color: #7b4a26 !important;
}
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Barra superior (deploy / rerun) con letras blancas */
[data-testid="stHeader"] * {
    color: #ffffff !important;
}

/* Métricas – tarjetas café, todo en blanco */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #5c371c, #7b4a26);
    padding: 12px;
    border-radius: 10px;
    border: 1px solid #3e2723;
}
[data-testid="stMetric"] * {
    color: #ffffff !important;
}

/* Expanders – “botoncitos” */
details {
    background-color: #d1b792 !important;
    border-radius: 8px;
    padding: 0.4rem 0.7rem;
    border: 1px solid #8d6e63;
}
summary {
    font-weight: 700 !important;
    color: #2b1a0f !important;
}

/* Tablas */
[data-testid="stDataFrame"] {
    color: #2b1a0f !important;
}
</style>
""", unsafe_allow_html=True)

# Paleta madera para TODOS los gráficos
WOOD_COLORS = ["#4b2e1a", "#6d4c3d", "#8d6e63", "#a1887f", "#3e2723"]
px.defaults.color_discrete_sequence = WOOD_COLORS


def style_fig(fig):
    """Aplica fondo beige–café y letras oscuras a los gráficos."""
    fig.update_layout(
        paper_bgcolor="#c7ab85",
        plot_bgcolor="#e1c39b",
        font_color="#1c130d",
        title_font_color="#1c130d",
        xaxis=dict(title_font_color="#1c130d", tickfont=dict(color="#1c130d")),
        yaxis=dict(title_font_color="#1c130d", tickfont=dict(color="#1c130d")),
    )
    return fig


# ============================================================
# CONEXIÓN A BD Y CARGA DE DATOS
# ============================================================
DB_URI = "mysql+pymysql://root@localhost:3306/proyecto"


def get_engine(db_uri: str = DB_URI):
    try:
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"Error conectando a la base de datos:\n{e}")
        st.stop()


engine = get_engine()


@st.cache_data(ttl=600)
def load_data(db_uri: str):
    engine_local = create_engine(db_uri)
    query = """
        SELECT 
            r.id_reserva,
            r.fecha_reserva,
            r.fecha_vencimiento,
            r.monto_total,
            r.estado_reserva,
            r.localizacion_reserva,
            
            c.id_cliente,
            CONCAT(c.nombre, ' ', c.apellido_paterno, ' ', c.apellido_materno) AS nombre_cliente,
            c.ci,
            
            h.id_habitacion,
            h.numero_habitacion,
            h.piso,
            h.precio AS tarifa_noche,
            
            th.id_tipo_habitacion,
            th.tipo_cama,
            th.numero_camas,
            th.descripcion AS descripcion_tipo_habitacion,
            th.capacidad,
            
            dr.id_detalle_reserva,
            dr.cantidad_personas,
            dr.check_in,
            dr.check_out,
            
            se.id_servicios_especiales,
            se.nombre AS nombre_servicio_especial,
            se.precio AS precio_servicio_catalogo,
            drs.precio_unitario AS precio_servicio_reserva,
            drs.subtotal AS subtotal_servicio,
            drs.hora,
            
            p.id_pago,
            p.monto AS monto_pago,
            p.estado_pago AS estado_pago_sistema,
            p.fecha_pago,
            
            ep.nombre_estado_pago,
            
            dp.id_detalle_pago,
            dp.monto AS monto_detalle_pago,
            dp.fecha AS fecha_detalle_pago,
            
            mp.id_metodo_pago,
            mp.nombre AS metodo_pago_nombre
        FROM reserva r
        JOIN cliente c 
            ON c.id_cliente = r.id_cliente
        JOIN detalle_reserva dr 
            ON dr.id_reserva = r.id_reserva
        JOIN habitacion h 
            ON h.id_habitacion = dr.id_habitacion
        JOIN tipo_habitacion th 
            ON th.id_tipo_habitacion = h.id_tipo_habitacion
        LEFT JOIN detalle_reserva_servicios_especiales drs
            ON drs.id_detalle_reserva = dr.id_detalle_reserva
        LEFT JOIN servicios_especiales se
            ON se.id_servicios_especiales = drs.id_servicios_especiales
        LEFT JOIN pago p
            ON p.id_reserva = r.id_reserva
        LEFT JOIN detalle_pago dp
            ON dp.id_detalle_pago = p.id_detalle_pago
        LEFT JOIN metodo_pago mp
            ON mp.id_metodo_pago = dp.id_metodo_pago
        LEFT JOIN estado_pago ep
            ON ep.id_estado_pago = p.id_estado_pago;
    """
    df_local = pd.read_sql(query, engine_local)

    # Conversión de fechas
    df_local["fecha_reserva"] = pd.to_datetime(df_local["fecha_reserva"])
    df_local["fecha_vencimiento"] = pd.to_datetime(df_local["fecha_vencimiento"])
    df_local["check_in"] = pd.to_datetime(df_local["check_in"])
    df_local["check_out"] = pd.to_datetime(df_local["check_out"])
    df_local["fecha_pago"] = pd.to_datetime(df_local["fecha_pago"])
    df_local["fecha_detalle_pago"] = pd.to_datetime(df_local["fecha_detalle_pago"])
    df_local["hora"] = pd.to_datetime(df_local["hora"])

    # Montos numéricos
    df_local["monto_total"] = df_local["monto_total"].astype(float)
    df_local["monto_pago"] = df_local["monto_pago"].astype(float)
    df_local["monto_detalle_pago"] = df_local["monto_detalle_pago"].astype(float)
    df_local["tarifa_noche"] = df_local["tarifa_noche"].astype(float)
    df_local["precio_servicio_catalogo"] = df_local["precio_servicio_catalogo"].astype(float)
    df_local["precio_servicio_reserva"] = df_local["precio_servicio_reserva"].astype(float)
    df_local["subtotal_servicio"] = df_local["subtotal_servicio"].astype(float)

    # Columnas derivadas
    df_local["mes_anio"] = df_local["fecha_reserva"].dt.to_period("M").astype(str)
    df_local["noches"] = (df_local["check_out"] - df_local["check_in"]).dt.days

    # Textos / nulos
    df_local["localizacion_reserva"] = df_local["localizacion_reserva"].fillna("Sin localización")
    df_local["descripcion_tipo_habitacion"] = df_local["descripcion_tipo_habitacion"].fillna("Sin descripción")
    df_local["nombre_servicio_especial"] = df_local["nombre_servicio_especial"].fillna("Sin servicio")
    df_local["metodo_pago_nombre"] = df_local["metodo_pago_nombre"].fillna("Sin método")
    df_local["nombre_estado_pago"] = df_local["nombre_estado_pago"].fillna("Sin estado")

    return df_local


df_base = load_data(DB_URI)

if df_base.empty:
    st.warning("No se pudo cargar información desde la base de datos.")
    st.stop()

# ============================================================
# MENÚ PRINCIPAL EN EL SIDEBAR
# ============================================================
st.sidebar.title("Menú del hotel")

pagina = st.sidebar.radio(
    "Selecciona una sección",
    (
        "Dashboard general",
        "Habitaciones y clientes",
        "Localización y pagos",
        "Servicios especiales",
    )
)

# ============================================================
# 1) DASHBOARD GENERAL
# ============================================================
if pagina == "Dashboard general":
    df = df_base.copy()

    st.title("Dashboard general de reservas")

    st.sidebar.subheader("Filtros – Dashboard general")

    fecha_min = df["fecha_reserva"].min().date()
    fecha_max = df["fecha_reserva"].max().date()

    rango_fechas = st.sidebar.date_input(
        "Rango de fechas de reserva",
        [fecha_min, fecha_max],
        min_value=fecha_min,
        max_value=fecha_max
    )

    if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
        fi, ff = rango_fechas
    else:
        fi = ff = fecha_min

    localizaciones = st.sidebar.multiselect(
        "Hotel / localización",
        sorted(df["localizacion_reserva"].unique().tolist())
    )

    estados_reserva = st.sidebar.multiselect(
        "Estado de la reserva",
        sorted(df["estado_reserva"].unique().tolist())
    )

    df = df[df["fecha_reserva"].dt.date.between(fi, ff)]

    if localizaciones:
        df = df[df["localizacion_reserva"].isin(localizaciones)]
    if estados_reserva:
        df = df[df["estado_reserva"].isin(estados_reserva)]

    if df.empty:
        st.warning("No se encontraron resultados con los filtros seleccionados.")
        st.stop()

    # Indicadores
    col1, col2, col3, col4 = st.columns(4)

    total_reservas = df["id_reserva"].nunique()
    monto_total_reservas = df.drop_duplicates("id_reserva")["monto_total"].sum()
    monto_promedio = monto_total_reservas / total_reservas if total_reservas > 0 else 0
    noches_totales = df.drop_duplicates("id_reserva")["noches"].sum()

    col1.metric("Reservas únicas", total_reservas)
    col2.metric("Monto total reservas", f"${monto_total_reservas:,.2f}")
    col3.metric("Monto promedio por reserva", f"${monto_promedio:,.2f}")
    col4.metric("Noches reservadas (total)", int(noches_totales))

    st.markdown("---")

    # Tabla en botoncito
    st.subheader("Tabla de reservas filtradas")
    with st.expander("Ver tabla de reservas filtradas"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Visualizaciones")

    # Gráfico 1
    with st.expander("📊 Monto total de reservas por fecha"):
        df_ts = (
            df.drop_duplicates("id_reserva")
              .groupby("fecha_reserva", as_index=False)["monto_total"]
              .sum()
              .sort_values("fecha_reserva")
        )
        fig1 = px.line(df_ts, x="fecha_reserva", y="monto_total",
                       title="Monto total de reservas por fecha")
        st.plotly_chart(style_fig(fig1), use_container_width=True)

    # Gráfico 2
    with st.expander("📊 Monto total por estado de reserva"):
        df_estado = (
            df.drop_duplicates("id_reserva")
              .groupby("estado_reserva", as_index=False)["monto_total"]
              .sum()
              .sort_values("monto_total", ascending=False)
        )
        fig2 = px.bar(df_estado, x="estado_reserva", y="monto_total",
                      title="Monto total por estado de reserva")
        fig2.update_layout(xaxis_title="Estado", yaxis_title="Monto total")
        st.plotly_chart(style_fig(fig2), use_container_width=True)

    # Gráfico 3
    with st.expander("📊 Distribución de montos de reserva"):
        df_res = df.drop_duplicates("id_reserva")
        fig3 = px.histogram(df_res, x="monto_total", nbins=10,
                            title="Distribución de montos de reserva")
        fig3.update_layout(xaxis_title="Monto total de reserva", yaxis_title="Frecuencia")
        st.plotly_chart(style_fig(fig3), use_container_width=True)


# ============================================================
# 2) HABITACIONES Y CLIENTES
# ============================================================
elif pagina == "Habitaciones y clientes":
    df = df_base.copy()

    st.title("Habitaciones y clientes")

    st.sidebar.subheader("Filtros – Habitaciones y clientes")

    fecha_min = df["fecha_reserva"].min().date()
    fecha_max = df["fecha_reserva"].max().date()

    rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max],
                                  min_value=fecha_min, max_value=fecha_max)
    if isinstance(rango, (list, tuple)) and len(rango) == 2:
        fi, ff = rango
    else:
        fi = ff = fecha_min

    tipos_h = st.sidebar.multiselect(
        "Tipo de habitación",
        sorted(df["descripcion_tipo_habitacion"].unique().tolist())
    )

    df = df[df["fecha_reserva"].dt.date.between(fi, ff)]
    if tipos_h:
        df = df[df["descripcion_tipo_habitacion"].isin(tipos_h)]

    if df.empty:
        st.warning("No se encontraron resultados con los filtros.")
        st.stop()

    # Indicadores
    c1, c2, c3, c4 = st.columns(4)

    hab_distintas = df["id_habitacion"].nunique()
    tipos_distintos = df["id_tipo_habitacion"].nunique()
    clientes_distintos = df["id_cliente"].nunique()
    noches_prom = df.drop_duplicates("id_reserva")["noches"].mean()

    c1.metric("Habitaciones distintas reservadas", hab_distintas)
    c2.metric("Tipos de habitación utilizados", tipos_distintos)
    c3.metric("Clientes distintos", clientes_distintos)
    c4.metric("Promedio de noches por reserva", f"{noches_prom:,.2f}")

    st.markdown("---")

    # Tabla en botoncito
    st.subheader("Reservas filtradas – detalle de habitaciones y clientes")
    with st.expander("Ver tabla de reservas filtradas (habitaciones y clientes)"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Visualizaciones")

    # Gráfico 1 – Monto por tipo de habitación
    with st.expander("📊 Monto total por tipo de habitación"):
        df_tipo = (
            df.drop_duplicates("id_reserva")
              .groupby("descripcion_tipo_habitacion", as_index=False)["monto_total"]
              .sum()
              .sort_values("monto_total", ascending=False)
        )
        fig1 = px.bar(df_tipo, x="descripcion_tipo_habitacion", y="monto_total",
                      title="Monto total por tipo de habitación")
        fig1.update_layout(xaxis_title="Tipo de habitación", yaxis_title="Monto total")
        st.plotly_chart(style_fig(fig1), use_container_width=True)

    # Gráfico 2 – Top 10 clientes por noches
    with st.expander("📊 Top 10 clientes por noches reservadas"):
        df_noches = (
            df.drop_duplicates("id_reserva")
              .groupby("nombre_cliente", as_index=False)["noches"]
              .sum()
              .sort_values("noches", ascending=False)
              .head(10)
        )
        fig2 = px.bar(df_noches, x="nombre_cliente", y="noches",
                      title="Top 10 clientes por noches reservadas")
        fig2.update_layout(xaxis_title="Cliente", yaxis_title="Noches")
        st.plotly_chart(style_fig(fig2), use_container_width=True)

    # Gráfico 3 – Tarifa vs personas
    with st.expander("📊 Relación tarifa noche vs cantidad de personas"):
        fig3 = px.scatter(
            df.drop_duplicates("id_detalle_reserva"),
            x="tarifa_noche",
            y="cantidad_personas",
            color="descripcion_tipo_habitacion",
            title="Tarifa por noche vs cantidad de personas",
            hover_data=["numero_habitacion", "nombre_cliente"]
        )
        fig3.update_layout(xaxis_title="Tarifa por noche", yaxis_title="Cantidad de personas")
        st.plotly_chart(style_fig(fig3), use_container_width=True)


# ============================================================
# 3) LOCALIZACIÓN Y PAGOS
# ============================================================
elif pagina == "Localización y pagos":
    df = df_base.copy()

    st.title("Localización y pagos")

    st.sidebar.subheader("Filtros – Localización y pagos")

    fecha_min = df["fecha_reserva"].min().date()
    fecha_max = df["fecha_reserva"].max().date()

    rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max],
                                  min_value=fecha_min, max_value=fecha_max)
    if isinstance(rango, (list, tuple)) and len(rango) == 2:
        fi, ff = rango
    else:
        fi = ff = fecha_min

    localizaciones = st.sidebar.multiselect(
        "Localización",
        sorted(df["localizacion_reserva"].unique().tolist())
    )

    metodos = st.sidebar.multiselect(
        "Método de pago",
        sorted(df["metodo_pago_nombre"].unique().tolist())
    )

    estados_pago = st.sidebar.multiselect(
        "Estado del pago",
        sorted(df["nombre_estado_pago"].unique().tolist())
    )

    df = df[df["fecha_reserva"].dt.date.between(fi, ff)]
    if localizaciones:
        df = df[df["localizacion_reserva"].isin(localizaciones)]
    if metodos:
        df = df[df["metodo_pago_nombre"].isin(metodos)]
    if estados_pago:
        df = df[df["nombre_estado_pago"].isin(estados_pago)]

    if df.empty:
        st.warning("No se encontraron resultados.")
        st.stop()

    # Indicadores
    c1, c2, c3, c4 = st.columns(4)

    reservas = df["id_reserva"].nunique()
    monto_total = df.drop_duplicates("id_reserva")["monto_total"].sum()
    pagos_realizados = df["id_pago"].nunique()
    monto_pagado = (
        df.dropna(subset=["id_pago"])
          .drop_duplicates("id_pago")["monto_pago"]
          .sum()
    )

    c1.metric("Reservas únicas", reservas)
    c2.metric("Monto total (reservas)", f"${monto_total:,.2f}")
    c3.metric("Pagos registrados", pagos_realizados)
    c4.metric("Monto total pagado", f"${monto_pagado:,.2f}")

    st.markdown("---")

    # Tabla en botoncito
    st.subheader("Reservas y pagos filtrados")
    with st.expander("Ver tabla de reservas y pagos filtrados"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Visualizaciones")

    # Gráfico 1 – Monto por localización
    with st.expander("📊 Monto total por localización"):
        df_loc = (
            df.drop_duplicates("id_reserva")
              .groupby("localizacion_reserva", as_index=False)["monto_total"]
              .sum()
              .sort_values("monto_total", ascending=False)
        )
        fig1 = px.bar(df_loc, x="localizacion_reserva", y="monto_total",
                      title="Monto total por localización")
        fig1.update_layout(xaxis_title="Localización", yaxis_title="Monto total")
        st.plotly_chart(style_fig(fig1), use_container_width=True)

    # Gráfico 2 – Monto pagado por método de pago
    with st.expander("📊 Monto pagado por método de pago"):
        df_mp = (
            df.dropna(subset=["id_pago"])
              .drop_duplicates("id_pago")
              .groupby("metodo_pago_nombre", as_index=False)["monto_pago"]
              .sum()
              .sort_values("monto_pago", ascending=False)
        )
        fig2 = px.bar(df_mp, x="metodo_pago_nombre", y="monto_pago",
                      title="Monto pagado por método de pago")
        fig2.update_layout(xaxis_title="Método de pago", yaxis_title="Monto pagado")
        st.plotly_chart(style_fig(fig2), use_container_width=True)

    # Gráfico 3 – Distribución de montos por estado de pago
    with st.expander("📊 Distribución de montos por estado de pago"):
        df_pe = (
            df.dropna(subset=["id_pago"])
              .drop_duplicates("id_pago")
              .groupby("nombre_estado_pago", as_index=False)["monto_pago"]
              .sum()
        )
        fig3 = px.pie(df_pe, values="monto_pago", names="nombre_estado_pago",
                      title="Distribución de montos por estado de pago")
        st.plotly_chart(style_fig(fig3), use_container_width=True)


# ============================================================
# 4) SERVICIOS ESPECIALES
# ============================================================
elif pagina == "Servicios especiales":
    df = df_base.copy()

    st.title("Servicios especiales")

    st.sidebar.subheader("Filtros – Servicios especiales")

    fecha_min = df["fecha_reserva"].min().date()
    fecha_max = df["fecha_reserva"].max().date()

    rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max],
                                  min_value=fecha_min, max_value=fecha_max)
    if isinstance(rango, (list, tuple)) and len(rango) == 2:
        fi, ff = rango
    else:
        fi = ff = fecha_min

    servicios = st.sidebar.multiselect(
        "Servicio especial",
        sorted(df["nombre_servicio_especial"].unique().tolist())
    )

    localizaciones = st.sidebar.multiselect(
        "Localización",
        sorted(df["localizacion_reserva"].unique().tolist())
    )

    df = df[df["fecha_reserva"].dt.date.between(fi, ff)]
    if servicios:
        df = df[df["nombre_servicio_especial"].isin(servicios)]
    if localizaciones:
        df = df[df["localizacion_reserva"].isin(localizaciones)]

    if df.empty:
        st.warning("No se encontraron resultados.")
        st.stop()

    # Indicadores
    c1, c2, c3, c4 = st.columns(4)

    servicios_usados = df["id_servicios_especiales"].nunique()
    reservas_con_servicio = df["id_reserva"].nunique()
    monto_catalogo = df["precio_servicio_catalogo"].sum()
    monto_reserva = df["precio_servicio_reserva"].sum()

    c1.metric("Servicios distintos utilizados", servicios_usados)
    c2.metric("Reservas con servicios especiales", reservas_con_servicio)
    c3.metric("Monto catálogo (teórico)", f"${monto_catalogo:,.2f}")
    c4.metric("Monto aplicado en reservas", f"${monto_reserva:,.2f}")

    st.markdown("---")

    # Tabla en botoncito
    st.subheader("Detalle de servicios especiales en reservas filtradas")
    with st.expander("Ver tabla de servicios especiales filtrados"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Visualizaciones")

    # Gráfico 1 – Monto por servicio
    with st.expander("📊 Monto total por servicio especial"):
        df_serv = (
            df.groupby("nombre_servicio_especial", as_index=False)["precio_servicio_reserva"]
              .sum()
              .sort_values("precio_servicio_reserva", ascending=False)
        )
        fig1 = px.bar(df_serv, x="nombre_servicio_especial", y="precio_servicio_reserva",
                      title="Monto total por servicio especial")
        fig1.update_layout(xaxis_title="Servicio especial", yaxis_title="Monto total")
        st.plotly_chart(style_fig(fig1), use_container_width=True)

    # Gráfico 2 – Servicios por localización
    with st.expander("📊 Servicios por localización"):
        df_loc = (
            df.groupby(["localizacion_reserva", "nombre_servicio_especial"], as_index=False)
              ["precio_servicio_reserva"]
              .sum()
        )
        fig2 = px.bar(
            df_loc,
            x="localizacion_reserva",
            y="precio_servicio_reserva",
            color="nombre_servicio_especial",
            barmode="stack",
            title="Monto por servicios especiales según localización"
        )
        fig2.update_layout(xaxis_title="Localización", yaxis_title="Monto total")
        st.plotly_chart(style_fig(fig2), use_container_width=True)

    # Gráfico 3 – Serie temporal
    with st.expander("📊 Ingresos por servicios especiales en el tiempo"):
        df_ts = (
            df.groupby("fecha_reserva", as_index=False)["precio_servicio_reserva"]
              .sum()
              .sort_values("fecha_reserva")
        )
        fig3 = px.line(df_ts, x="fecha_reserva", y="precio_servicio_reserva",
                       title="Ingresos por servicios especiales en el tiempo")
        fig3.update_layout(xaxis_title="Fecha", yaxis_title="Monto servicios")
        st.plotly_chart(style_fig(fig3), use_container_width=True)

st.caption("UNIVALLE – Bases de Datos I – Proyecto Hotel con menú")