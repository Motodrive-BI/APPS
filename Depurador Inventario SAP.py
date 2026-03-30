import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="HERRAMIENTAS DE DEPURACIÓN", layout="wide")

# --- CONFIGURACIÓN DE GITHUB ---
GITHUB_BASE_URL = "https://raw.githubusercontent.com/Motodrive-BI/APPS/main/"

URLS = {
    "sku": GITHUB_BASE_URL + "Catalogo_SKU_v3 BETA.xlsx",
    "modelos": GITHUB_BASE_URL + "Catalogo_Modelos.xlsx",
    "sucursales": GITHUB_BASE_URL + "Concentrado_Master.xlsx"
}

# --- FUNCIONES ---
@st.cache_data(ttl=3600)
def cargar_excel_github(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception:
        st.error(f"Error cargando catálogo: {url}")
        return None

def limpiar_columnas(df):
    df.columns = df.columns.str.strip()
    return df

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Depurado')
    return output.getvalue()

# --- CARGA CATÁLOGOS ---
cat_sku_raw = cargar_excel_github(URLS["sku"])
cat_mod_raw = cargar_excel_github(URLS["modelos"])
cat_suc_raw = cargar_excel_github(URLS["sucursales"])

# --- SIDEBAR ---
st.sidebar.title("📊 Panel de Control")
opcion = st.sidebar.selectbox(
    "Selecciona el reporte:",
    ["Reporte Diario de Inventarios", "Reporte de Sell Out Global", "Consolidador Retail"]
)

# ===============================
# INVENTARIOS
# ===============================
if opcion == "Reporte Diario de Inventarios":
    st.title("📦 Depurador: Inventory")

    archivo = st.file_uploader("Cargar archivo", type=["xlsx", "xls"])

    if archivo:
        df = pd.read_excel(archivo, header=None)

        df['ALM'] = None
        current_alm = None

        for i, row in df.iterrows():
            if pd.notna(row[0]) and 'Whse:' in str(row[0]):
                current_alm = row[1]
            df.at[i, 'ALM'] = current_alm

        df = df[~df[0].astype(str).str.contains('Whse:', na=False)]
        df = df.dropna(subset=[0])
        df.columns = list(df.iloc[0, :13]) + list(df.columns[13:])
        df = df.drop(0).reset_index(drop=True)

        columnas = ['Item No.', 'Item Description', 'ALM', 'Inventory UoM',
                    'In Stock', 'Committed', 'Ordered', 'Available']

        columnas_existentes = [c for c in columnas if c in df.columns]
        df_final = df[columnas_existentes]

        st.dataframe(df_final.head())
        st.download_button("Descargar", to_excel(df_final), "inventario.xlsx")

# ===============================
# SELL OUT GLOBAL
# ===============================
elif opcion == "Reporte de Sell Out Global":
    st.title("🚀 Sell Out Global")

    archivo = st.file_uploader("Cargar archivo", type=["xlsx", "xls"])

    if archivo:
        df = pd.read_excel(archivo)
        df = limpiar_columnas(df)

        # Tipos
        df['Código Postal'] = df['Código Postal'].astype(str)
        df['Teléfono'] = df['Teléfono'].astype(str)
        df['Fecha de fabricación'] = pd.to_datetime(df['Fecha de fabricación'], errors='coerce')

        columnas = [
            'Fecha del documento', 'Vendedor', 'Familia del modelo',
            'Nombre del Modelo', 'Item', 'Cantidad', 'Precio'
        ]

        columnas_existentes = [c for c in columnas if c in df.columns]
        df_final = df[columnas_existentes]

        st.dataframe(df_final.head())
        st.download_button("Descargar", to_excel(df_final), "sellout.xlsx")

# ===============================
# CONSOLIDADOR RETAIL
# ===============================
elif opcion == "Consolidador Retail":
    st.title("🔗 Consolidador Retail")

    archivo = st.file_uploader("Sube archivo master", type=["xlsx"])

    if archivo and cat_sku_raw and cat_mod_raw and cat_suc_raw:

        if st.button("Procesar"):

            # Leer
            Coppel = limpiar_columnas(pd.read_excel(archivo, sheet_name="Coppel"))
            Liverpool = limpiar_columnas(pd.read_excel(archivo, sheet_name="Liverpool"))

            CAT_SKU = limpiar_columnas(pd.read_excel(cat_sku_raw, sheet_name="Sku_retail"))
            SUC = limpiar_columnas(pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC"))

            # Normalizar
            CAT_SKU['SKU'] = CAT_SKU['SKU'].astype(str).str.strip().str.upper()
            mapa = CAT_SKU.drop_duplicates('SKU').set_index('SKU')['Item']

            # COPPEL
            Coppel['Código'] = Coppel['Código'].astype(str).str.strip().str.upper()
            Coppel['Item'] = Coppel['Código'].map(mapa)

            # LIVERPOOL
            Liverpool['Artículo'] = Liverpool['Artículo'].astype(str).str.strip().str.upper()
            Liverpool['Item'] = Liverpool['Artículo'].map(mapa)

            # CONCAT SEGURO
            df_final = pd.concat([
                Coppel[['Item']],
                Liverpool[['Item']]
            ], ignore_index=True)

            st.success("✅ Procesado correctamente")
            st.dataframe(df_final.head())

            st.download_button(
                "Descargar",
                to_excel(df_final),
                "consolidado.xlsx"
            )
