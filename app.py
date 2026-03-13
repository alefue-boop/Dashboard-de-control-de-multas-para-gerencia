import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard Multas RRHH", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Control de Multas - Inspección del Trabajo")

# Función para formatear dinero al estilo chileno ($ 2.500.000)
def formato_clp(valor):
    if pd.isna(valor): return "$0"
    return f"${valor:,.0f}".replace(",", ".")

# Traductor de números (Formato Chile a Nube)
def arreglar_numeros(val):
    val = str(val).strip()
    if val in ['nan', 'None', '', 'NaN']: return None
    
    if ',' in val and '.' in val:
        if val.rfind(',') > val.rfind('.'):
            val = val.replace('.', '').replace(',', '.')
        else:
            val = val.replace(',', '')
    elif ',' in val:
        val = val.replace(',', '.')
    elif '.' in val:
        partes = val.split('.')
        if len(partes) == 2 and len(partes[1]) <= 2:
            pass 
        else:
            val = val.replace('.', '')
            
    try:
        return float(val)
    except:
        return None

# 2. Función Inteligente y Verificación de Base de Datos
@st.cache_data
def cargar_datos_comprobados():
    archivos_posibles = ["MULTAS.csv", "RESUMEN MULTAS.xls - MULTAS.csv", "RESUMEN_MULTAS.csv"]
    archivo_encontrado = None
    
    for arch in archivos_posibles:
        if os.path.exists(arch):
            archivo_encontrado = arch
            break
            
    if archivo_encontrado is None:
        st.error("🚨 No se encontró la base de datos. Asegúrate de haber subido tu Excel/CSV a GitHub.")
        st.stop()

    opciones_formato = [
        {"skiprows": 4, "sep": ",", "encoding": "utf-8"},
        {"skiprows": 4, "sep": ",", "encoding": "latin-1"},
        {"skiprows": 0, "sep": ",", "encoding": "utf-8"},
        {"skiprows": 0, "sep": ";", "encoding": "latin-1"}
    ]
    
    df_final = None
    for config in opciones_formato:
        try:
            df = pd.read_csv(archivo_encontrado, 
                             skiprows=config["skiprows"], 
                             sep=config["sep"], 
                             encoding=config["encoding"], 
                             on_bad_lines="skip")
            df.columns = df.columns.str.strip()
            
            for col in df.columns:
                if 'A' in col and 'o' in col and len(col) <= 4:
                    df.rename(columns={col: 'Año'}, inplace=True)
            
            if 'Costo Monetario' in df.columns and 'Año' in df.columns:
                df_final = df
                break 
        except:
            continue
            
    if df_final is None:
        st.error("🚨 El archivo se encontró, pero el formato interno no es legible.")
        st.stop()
        
    df = df_final
    
    # ---------------- LIMPIEZA DE DATOS PARA RRHH ----------------
    df = df.dropna(subset=['Costo Monetario', 'Año']).copy()
    
    df['Año'] = pd.to_numeric(df['Año'], errors='coerce').fillna(0).astype(int).astype(str)
    
    df['Estado Actual'] = df['Estado Actual'].astype(str).str.upper().str.strip()
    df['Estado Actual'] = df['Estado Actual'].replace({'PAGADO': 'PAGADA', 'SIN EFECTO': 'DEJA SIN EFECTO'})
    df['Responsable'] = df['Responsable'].astype(str).str.upper().str.strip()
    
    # Aplicar el traductor inteligente de montos
    df['Costo Monetario Real'] = df['Costo Monetario'].apply(arreglar_numeros)
    df = df.dropna(subset=['Costo Monetario Real'])
    
    # Columna en Millones solo para los gráficos
    df['Costo en Millones (MM$)'] = df['Costo Monetario Real'] / 1000000
    
    return df

df = cargar_datos_comprobados()

# 3. Barra Lateral (Filtros interactivos)
st.sidebar.header("Filtros del Dashboard")
anio_filtro = st.sidebar.multiselect("Seleccionar Año:", options=sorted(df['Año'].unique()), default=sorted(df['Año'].unique()))
resp_filtro = st.sidebar.multiselect("Seleccionar Responsable:", options=df['Responsable'].dropna().unique(), default=df['Responsable'].dropna().unique())
estado_filtro = st.sidebar.multiselect("Estado de la Multa:", options=df['Estado Actual'].dropna().unique(), default=df['Estado Actual'].dropna().unique())

df_filtrado = df[
    (df['Año'].isin(anio_filtro)) & 
    (df['Responsable'].isin(resp_filtro)) &
    (df['Estado Actual'].isin(estado_filtro))
]

# 4. Tarjetas de Indicadores Clave
col1, col2, col3 = st.columns(3)
gasto_total = df_filtrado['Costo Monetario Real'].sum()
cantidad_multas = len(df_filtrado)
promedio_multa = df_filtrado['Costo Monetario Real'].mean() if cantidad_multas > 0 else 0

col1.metric("Gasto Total (CLP)", formato_clp(gasto_total))
col2.metric("Cantidad de Multas", cantidad_multas)
col3.metric("Costo Promedio por Multa", formato_clp(promedio_multa))

st.divider()

# 5. Gráficos Interactivos
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    gasto_anio = df_filtrado.groupby('Año')['Costo en Millones (MM$)'].sum().reset_index()
    fig_anio = px.bar(gasto_anio, x='Año', y='Costo en Millones (MM$)', title="Gasto Total por Año (Millones de Pesos)", text_auto='.1f', color_discrete_sequence=['#1f77b4'])
    st.plotly_chart(fig_anio, use_container_width=True)

with col_graf2:
    gasto_resp = df_filtrado.groupby('Responsable')['Costo en Millones (MM$)'].sum().reset_index()
    fig_resp = px.pie(gasto_resp, values='Costo en Millones (MM$)', names='Responsable', title="Distribución por Departamento", hole=0.4)
    st.plotly_chart(fig_resp, use_container_width=True)

col_graf3, col_graf4 = st.columns(2)

with col_graf3:
    if 'Ciudad' in df_filtrado.columns:
        gasto_ciudad = df_filtrado.groupby('Ciudad')['Costo en Millones (MM$)'].sum().reset_index().sort_values(by='Costo en Millones (MM$)', ascending=False).head(10)
        fig_ciudad = px.bar(gasto_ciudad, x='Costo en Millones (MM$)', y='Ciudad', orientation='h', title="Top 10 Ciudades con Mayor Gasto", color='Costo en Millones (MM$)', color_continuous_scale='Reds')
        st.plotly_chart(fig_ciudad, use_container_width=True)

with col_graf4:
    if 'Tipo de Infracción' in df_filtrado.columns:
        infracciones = df_filtrado['Tipo de Infracción'].value_counts().reset_index().head(5)
        infracciones.columns = ['Tipo de Infracción', 'Cantidad']
        fig_infraccion = px.bar(infracciones, x='Cantidad', y='Tipo de Infracción', orientation='h', title="Top 5 Infracciones más Frecuentes", color_discrete_sequence=['#ff7f0e'])
        st.plotly_chart(fig_infraccion, use_container_width=True)

st.divider()

# 6. Tabla de Detalles de Resoluciones
st.subheader("📑 Detalle de Multas")
columnas_mostrar = [col for col in ['Año', 'Región', 'Ciudad', 'Resolución', 'Tipo de Infracción', 'Estado Actual', 'Responsable', 'Costo Monetario Real'] if col in df_filtrado.columns]

df_tabla = df_filtrado[columnas_mostrar].copy()
if 'Costo Monetario Real' in df_tabla.columns:
    df_tabla['Costo Monetario Real'] = df_tabla['Costo Monetario Real'].apply(lambda x: formato_clp(x))

st.dataframe(df_tabla)
