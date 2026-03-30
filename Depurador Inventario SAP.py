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

    archivo = st.file_uploader("Sube Layout Retail Master", type=["xlsx"])

    if archivo and cat_sku_raw and cat_mod_raw and cat_suc_raw:

        if st.button("Procesar"):

            # =========================
            # FUNCIONES AUXILIARES
            # =========================
            def norm(x):
                return x.astype(str).str.strip().str.upper()

            def limpiar(df):
                df.columns = df.columns.str.strip()
                return df

            # =========================
            # CARGA ARCHIVOS
            # =========================
            Coppel = limpiar(pd.read_excel(archivo, sheet_name="Coppel"))
            Liverpool = limpiar(pd.read_excel(archivo, sheet_name="Liverpool"))
            Sears = limpiar(pd.read_excel(archivo, sheet_name="Sears"))
            Suburbia = limpiar(pd.read_excel(archivo, sheet_name="Suburbia"))
            Mavi = limpiar(pd.read_excel(archivo, sheet_name="Mavi"))
            Bodesa = limpiar(pd.read_excel(archivo, sheet_name="Bodesa"))
            Clikstore = limpiar(pd.read_excel(archivo, sheet_name="Clik"))
            Cklass = limpiar(pd.read_excel(archivo, sheet_name="Cklass"))
            Ecomm = limpiar(pd.read_excel(archivo, sheet_name="Ecomm"))

            CAT_SKU = limpiar(pd.read_excel(cat_sku_raw, sheet_name="Sku_retail"))
            SUC = limpiar(pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC"))

            # =========================
            # MAPAS
            # =========================
            CAT_SKU['SKU'] = norm(CAT_SKU['SKU'])
            mapa_items = CAT_SKU.drop_duplicates('SKU').set_index('SKU')['Item']

            SUC['IDRETAIL'] = norm(SUC['ID Sucursal']) + norm(SUC['Cadena'])
            mapa_suc = SUC.drop_duplicates('IDRETAIL').set_index('IDRETAIL')

            # =========================
            # COPPEL
            # =========================
            Coppel['CANAL'] = "COPPEL"
            Coppel['Código'] = norm(Coppel['Código'])
            Coppel['Item'] = Coppel['Código'].map(mapa_items)
            Coppel['IDRETAIL'] = norm(Coppel['Tienda']) + "COPPEL"
            Coppel['STORE'] = Coppel['IDRETAIL'].map(mapa_suc['Sucursal'])
            Coppel['FECHA'] = pd.to_datetime(Coppel['Fecha Venta'], errors='coerce')
            Coppel['QTY'] = Coppel['Estatus'].map({
                'VENTA': 1, 'CANCELADA': 0, 'ACTIVADA': 1, 'EN TIENDA': 1
            })

            # =========================
            # LIVERPOOL
            # =========================
            Liverpool['CANAL'] = "LIVERPOOL"
            Liverpool = Liverpool[~Liverpool['Artículo'].str.contains('Resultado', na=False)]
            Liverpool['Artículo'] = norm(Liverpool['Artículo'])
            Liverpool['Item'] = Liverpool['Artículo'].map(mapa_items)
            Liverpool['IDRETAIL'] = norm(Liverpool['Centro']) + "LIVERPOOL"
            Liverpool['STORE'] = Liverpool['IDRETAIL'].map(mapa_suc['Sucursal'])
            Liverpool['FECHA'] = pd.to_datetime(Liverpool['Día/Periodo'], errors='coerce')
            Liverpool['QTY'] = Liverpool['Ventas Unidades']

            # =========================
            # SEARS
            # =========================
            Sears['CANAL'] = "SEARS"
            Sears['SKU'] = norm(Sears['SKU'])
            Sears['Item'] = Sears['SKU'].map(mapa_items)
            Sears['IDRETAIL'] = norm(Sears['TDA']) + "SEARS"
            Sears['STORE'] = Sears['IDRETAIL'].map(mapa_suc['Sucursal'])
            Sears['FECHA'] = pd.to_datetime(Sears['FECHA'], errors='coerce')
            Sears['QTY'] = Sears['CANT']

            # =========================
            # SUBURBIA
            # =========================
            Suburbia['CANAL'] = "SUBURBIA"
            Suburbia['SKU'] = norm(Suburbia['SKU'])
            Suburbia['Item'] = Suburbia['SKU'].map(mapa_items)
            Suburbia['IDRETAIL'] = norm(Suburbia['CENTRO']) + "SUBURBIA"
            Suburbia['STORE'] = Suburbia['IDRETAIL'].map(mapa_suc['Sucursal'])
            Suburbia['FECHA'] = pd.to_datetime(Suburbia['Día'], errors='coerce')
            Suburbia['QTY'] = Suburbia['VENTA UNIDADES']

            # =========================
            # MAVI
            # =========================
            Mavi['CANAL'] = "MAVI"
            Mavi['CODIGO'] = norm(Mavi['CODIGO'])
            Mavi['Item'] = Mavi['CODIGO'].map(mapa_items)
            Mavi['IDRETAIL'] = norm(Mavi['TIENDA']) + "MAVI"
            Mavi['STORE'] = Mavi['IDRETAIL'].map(mapa_suc['Sucursal'])
            Mavi['FECHA'] = pd.to_datetime(Mavi['FECHA FACT'], errors='coerce')
            Mavi['QTY'] = Mavi['CANT.']

            # =========================
            # BODESA
            # =========================
            Bodesa['CANAL'] = "BODESA"
            Bodesa['Materia'] = norm(Bodesa['Materia'])
            Bodesa['Item'] = Bodesa['Materia'].map(mapa_items)
            Bodesa['IDRETAIL'] = norm(Bodesa['Centro']) + "BODESA"
            Bodesa['STORE'] = Bodesa['IDRETAIL'].map(mapa_suc['Sucursal'])
            Bodesa['FECHA'] = pd.to_datetime(Bodesa['Fecha Vta'], errors='coerce')
            Bodesa['QTY'] = Bodesa['Vta pzas']

            # =========================
            # CLIKSTORE
            # =========================
            Clikstore['CANAL'] = "CLIKSTORE"
            Clikstore['SAP'] = norm(Clikstore['SAP'])
            Clikstore['Item'] = Clikstore['SAP'].map(mapa_items)
            Clikstore['IDRETAIL'] = norm(Clikstore['ID SUC']) + "CLIKSTORE"
            Clikstore['STORE'] = Clikstore['IDRETAIL'].map(mapa_suc['Sucursal'])
            Clikstore['FECHA'] = pd.to_datetime(Clikstore['FECHA'], errors='coerce')
            Clikstore['QTY'] = Clikstore['Cantidad']

            # =========================
            # CKLASS
            # =========================
            Cklass['CANAL'] = "CKLASS"
            Cklass['Material'] = norm(Cklass['Material'])
            Cklass['Item'] = Cklass['Material'].map(mapa_items)
            Cklass['IDRETAIL'] = norm(Cklass['ID']) + "CKLASS"
            Cklass['STORE'] = Cklass['IDRETAIL'].map(mapa_suc['Sucursal'])
            Cklass['FECHA'] = pd.to_datetime(Cklass['Fecha'], errors='coerce')
            Cklass['QTY'] = Cklass['Cantidad']

            # =========================
            # ECOMMERCE
            # =========================
            Ecomm['CANAL'] = "ECOMMERCE"
            Ecomm['Unido'] = norm(Ecomm['Unido'])
            Ecomm['Item'] = Ecomm['Unido'].map(mapa_items)
            Ecomm['STORE'] = "ECOMMERCE"
            Ecomm['FECHA'] = pd.to_datetime(Ecomm['Fecha'], errors='coerce')
            Ecomm['QTY'] = Ecomm['Cant']
            Ecomm['IDRETAIL'] = "ECOMMERCE"

            # =========================
            # CONSOLIDADO
            # =========================
            df_final = pd.concat([
                Coppel, Liverpool, Sears, Suburbia,
                Mavi, Bodesa, Clikstore, Cklass, Ecomm
            ], ignore_index=True)

            df_final = df_final[['CANAL', 'FECHA', 'Item', 'QTY', 'STORE']]

            st.success("✅ Consolidación completa")
            st.dataframe(df_final.head(20))

            st.download_button(
                "📥 Descargar",
                to_excel(df_final),
                "SO_RETAIL_COMPLETO.xlsx"
            )
