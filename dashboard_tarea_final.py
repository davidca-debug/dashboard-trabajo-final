import streamlit as st
import pandas as pd
import folium
import geopandas as gpd
import seaborn as sns
import matplotlib.pyplot as plt

from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster

# -------------------------
# CONFIGURACIÓN
# -------------------------
st.set_page_config(layout="wide")

# -------------------------
# TÍTULO
# -------------------------
st.markdown("""
<h1 style='text-align: center; color: #2E86C1;'>
 Dashboard de Análisis de Ventas y Logística
</h1>
<hr style='border: 2px solid #2E86C1; width: 60%; margin: auto;'>
""", unsafe_allow_html=True)
st.markdown("### ")

# -------------------------
# CARGA DE DATOS (CACHE)
# -------------------------
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_excel('dataset_tarea_ind.xlsx')
    geo = gpd.read_file('comunas_metropolitana-1.geojson')
    return df, geo

df, geo = load_data()

# -------------------------
# LIMPIEZA (CACHE)
# -------------------------
@st.cache_data
def limpiar_datos(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    def clean_float(col):
        return pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

    for col in ['lat', 'lng', 'lat_cd', 'lng_cd']:
        df[col] = clean_float(col)

    df['venta_neta'] = clean_float('venta_neta')

    df = df.dropna(subset=['lat', 'lng', 'venta_neta'])
    return df

df = limpiar_datos(df)

col_ventas = 'venta_neta'

# -------------------------
# FILTROS
# -------------------------
st.sidebar.title("🔎 Filtros")

opciones = ["Todos"] + sorted(df['canal'].dropna().unique())
canal = st.sidebar.selectbox("Canal", opciones)

if canal != "Todos":
    df = df[df['canal'] == canal]

# -------------------------
# ANÁLISIS 1 (CACHE)
# -------------------------
@st.cache_data
def ventas_por_canal(df):
    return df.groupby('canal')['venta_neta'].sum().reset_index()

#st.markdown("##  Panorama general del negocio")
st.markdown(
    "<h2 style='text-align: center;'> Panorama general del negocio</h2>",
    unsafe_allow_html=True
)
st.markdown("### ")

if len(df) > 0:
    data_canal = ventas_por_canal(df)

    fig, ax = plt.subplots(figsize=(10,5))
    sns.barplot(data=data_canal, x='canal', y='venta_neta', ax=ax)
    ax.set_title("Ventas por canal")
    ax.set_xlabel("Canal")
    ax.set_ylabel("Ventas")

    with st.container():
        st.pyplot(fig, use_container_width=True)

st.divider()

# -------------------------
# ANÁLISIS 2
# -------------------------
#st.markdown("##  Mapa de la red logística")
st.markdown(
    "<h2 style='text-align: center;'> Mapa de la red logística</h2>",
    unsafe_allow_html=True
)
st.markdown("### ")

if len(df) > 0:
    mapa = folium.Map(
        location=[-33.45, -70.65],
        zoom_start=11,
        tiles='cartodbpositron'
    )

    cluster = MarkerCluster().add_to(mapa)

    cd = df[['centro_dist', 'lat_cd', 'lng_cd']].drop_duplicates()

    for _, row in cd.iterrows():
        folium.Marker(
            location=[row['lat_cd'], row['lng_cd']],
            popup=f"Centro: {row['centro_dist']}",
            icon=folium.Icon(color='red')
        ).add_to(mapa)

    #  SAMPLE FIJO (SIN PARPADEO)
    sample = df.sample(n=min(500, len(df)), random_state=42)

    for _, row in sample.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lng']],
            radius=3,
            color='blue',
            fill=True
        ).add_to(cluster)

    st_folium(
        mapa,
        use_container_width=True,
        height=600,
        returned_objects=[]
    )

st.divider()

# -------------------------
# ANÁLISIS 3
# -------------------------
#st.markdown("## Mapa de calor")
st.markdown(
    "<h2 style='text-align: center;'> Mapa de calor</h2>",
    unsafe_allow_html=True
)
st.markdown("### ")

if len(df) > 0:
    mapa_heat = folium.Map(
        location=[-33.45, -70.65],
        zoom_start=11,
        tiles='cartodbpositron'
    )

    heat_data = df[['lat', 'lng', col_ventas]].values.tolist()

    HeatMap(heat_data, radius=10, blur=15).add_to(mapa_heat)

    st_folium(
        mapa_heat,
        use_container_width=True,
        height=600,
        returned_objects=[]
    )

st.divider()

# -------------------------
# ANÁLISIS 4
# -------------------------
import numpy as np

#st.markdown("##  Mapa de ventas por comuna")
st.markdown(
    "<h2 style='text-align: center;'> Mapa de ventas por comuna</h2>",
    unsafe_allow_html=True
)
st.markdown("### ")

if len(df) > 0:

    # -------------------------
    # LIMPIEZA
    # -------------------------
    df['comuna'] = df['comuna'].astype(str).str.upper().str.strip()
    geo['name'] = geo['name'].astype(str).str.upper().str.strip()

    # -------------------------
    # AGRUPACIÓN
    # -------------------------
    ventas_comuna = df.groupby('comuna')[col_ventas].sum().reset_index()

    # TRANSFORMACIÓN LOG
    ventas_comuna['ventas_log'] = np.log1p(ventas_comuna[col_ventas])

    # -------------------------
    # MERGE GEO
    # -------------------------
    geo_merge = geo.merge(
        ventas_comuna,
        left_on='name',
        right_on='comuna',
        how='left'
    )

    geo_merge[col_ventas] = geo_merge[col_ventas].fillna(0)
    geo_merge['ventas_log'] = geo_merge['ventas_log'].fillna(0)

    # -------------------------
    # MAPA BASE
    # -------------------------
    mapa_cor = folium.Map(
        location=[-33.45, -70.65],
        zoom_start=10,
        tiles='cartodbpositron'
    )

    # -------------------------
    # COROPLETAS 
    # -------------------------
    folium.Choropleth(
        geo_data=geo_merge,
        data=geo_merge,
        columns=['comuna', 'ventas_log'],
        key_on='feature.properties.name',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0, 
        legend_name='Ventas (escala log)'
    ).add_to(mapa_cor)

    # -------------------------
    # GEOJSON PERSONALIZADO 
    # -------------------------
    folium.GeoJson(
        geo_merge,
        style_function=lambda x: {
            'color': 'black',   
            'weight': 0.8,
            'fillOpacity': 0
        },
        highlight_function=lambda x: {
            'color': 'black',
            'weight': 1.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['name', col_ventas],
            aliases=['Comuna:', 'Ventas reales:'],
            localize=True
        )
    ).add_to(mapa_cor)

    # -------------------------
    # MOSTRAR MAPA 
    # -------------------------
    st_folium(
        mapa_cor,
        use_container_width=True,
        height=600,
        returned_objects=[]
    )

st.divider()


