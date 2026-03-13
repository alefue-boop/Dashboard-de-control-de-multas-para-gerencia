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
