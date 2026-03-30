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

# =========================
# CONSOLIDADOR FINAL FULL
# =========================
elif opcion == "Consolidador Retail":

    st.title("🔗 Consolidador Sell Out Retail")
    file_master = st.file_uploader("Sube Layout Retail Master.xlsx", type=["xlsx"])

    if file_master and cat_sku_raw and cat_mod_raw and cat_suc_raw:

        if st.button("🚀 Ejecutar Consolidación"):

            with st.spinner("Procesando..."):

                # =========================
                # 📥 CARGA DE ARCHIVOS
                # =========================
                dfs = {
                    "Coppel": pd.read_excel(file_master, sheet_name="Coppel"),
                    "Liverpool": pd.read_excel(file_master, sheet_name="Liverpool"),
                    "Sears": pd.read_excel(file_master, sheet_name="Sears"),
                    "Suburbia": pd.read_excel(file_master, sheet_name="Suburbia"),
                    "Mavi": pd.read_excel(file_master, sheet_name="Mavi"),
                    "Bodesa": pd.read_excel(file_master, sheet_name="Bodesa"),
                    "Clikstore": pd.read_excel(file_master, sheet_name="Clik"),
                    "Cklass": pd.read_excel(file_master, sheet_name="Cklass"),
                    "Ecomm": pd.read_excel(file_master, sheet_name="Ecomm"),
                }

                CAT_SKU = pd.read_excel(cat_sku_raw, sheet_name="Sku_retail")
                CAT_MOD = pd.read_excel(cat_mod_raw, sheet_name="CAT_MOD_v3")
                CAT_SUC = pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC")

                # =========================
                # 🧠 MAPEOS
                # =========================
                CAT_SKU['SKU'] = CAT_SKU['SKU'].astype(str).str.strip().str.upper()
                mapeo_sku = CAT_SKU.drop_duplicates('SKU').set_index('SKU')['Item']

                CAT_SUC['IDRETAIL'] = (
                    CAT_SUC['ID Sucursal'].astype(str).str.strip() +
                    CAT_SUC['Cadena'].astype(str).str.strip()
                ).str.upper()

                mapeo_suc = CAT_SUC.drop_duplicates('IDRETAIL').set_index('IDRETAIL')['Sucursal']
                mapeo_estado = CAT_SUC.drop_duplicates('IDRETAIL').set_index('IDRETAIL')['Estado']
                mapeo_ciudad = CAT_SUC.drop_duplicates('IDRETAIL').set_index('IDRETAIL')['Municipio']

                # =========================
                # 🔧 FUNCIÓN GENERAL
                # =========================
                def procesar(df, sku_col, tienda_col, fecha_col, qty_col, canal):

                    df = df.copy()

                    # limpiar columnas
                    df[sku_col] = df[sku_col].astype(str).str.strip().str.upper()
                    df[tienda_col] = df[tienda_col].astype(str).str.strip()

                    # eliminar basura tipo "resultado"
                    df = df[~df[sku_col].str.contains("RESULT", case=False, na=False)]

                    # fechas
                    df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')

                    # qty
                    df['QTY'] = pd.to_numeric(df.get(qty_col, 1), errors='coerce')

                    # map SKU
                    df['N° ARTICULO'] = df[sku_col].map(mapeo_sku)

                    # ID RETAIL
                    df['ID'] = df[tienda_col]
                    df['CANAL'] = canal
                    df['ID RETAIL'] = df['ID'].astype(str) + canal

                    # sucursal
                    df['STORE'] = df['ID RETAIL'].map(mapeo_suc)

                    # limpiar NaN críticos
                    df = df.dropna(subset=['N° ARTICULO'])

                    return df.reset_index(drop=True)

                # =========================
                # 🚀 PROCESAMIENTO
                # =========================
                Coppel = procesar(dfs["Coppel"], "Código", "Tienda", "Fecha Venta", "QTY", "COPPEL")
                Liverpool = procesar(dfs["Liverpool"], "Artículo", "Centro", "Día/Periodo", "Ventas Unidades", "LIVERPOOL")
                Sears = procesar(dfs["Sears"], "SKU", "TDA", "FECHA", "CANT", "SEARS")
                Suburbia = procesar(dfs["Suburbia"], "SKU", "CENTRO", "Día", "VENTA UNIDADES", "SUBURBIA")
                Mavi = procesar(dfs["Mavi"], "CODIGO", "TIENDA", "FECHA FACT", "CANT.", "MAVI")
                Bodesa = procesar(dfs["Bodesa"], "Materia", "Centro", "Fecha Vta", "Vta pzas", "BODESA")
                Clikstore = procesar(dfs["Clikstore"], "SAP", "ID SUC", "FECHA", "Cantidad", "CLIKSTORE")
                Cklass = procesar(dfs["Cklass"], "Material", "ID", "Fecha", "Cantidad", "CKLASS")
                Ecomm = procesar(dfs["Ecomm"], "Unido", "Id", "Fecha  ", "Cant", "ECOMM")

                # =========================
                # 🧩 CONSOLIDADO
                # =========================
                frames = [Coppel, Liverpool, Sears, Suburbia, Mavi, Bodesa, Clikstore, Cklass, Ecomm]
                df_final = pd.concat(frames, ignore_index=True)

                # =========================
                # 📅 FECHAS
                # =========================
                df_final['FECHA'] = pd.to_datetime(df_final['FECHA'], errors='coerce')
                df_final['MES'] = df_final['FECHA'].dt.month_name()
                df_final['AÑO'] = df_final['FECHA'].dt.year
                df_final['MES - AÑO'] = df_final['MES'] + " " + df_final['AÑO'].astype(str)

                # =========================
                # 🧠 MODELOS
                # =========================
                CAT_MOD['NÚMERO DE ARTÍCULO (SAP)'] = CAT_MOD['NÚMERO DE ARTÍCULO (SAP)'].astype(str).str.strip().str.upper()
                CAT_MOD['CILINDRADA'] = CAT_MOD['CILINDRADA'].fillna(0).astype(int).astype(str) + "CC"

                map_mod = CAT_MOD.drop_duplicates('NÚMERO DE ARTÍCULO (SAP)').set_index('NÚMERO DE ARTÍCULO (SAP)')

                df_final['CC'] = df_final['N° ARTICULO'].map(map_mod['CILINDRADA'])
                df_final['MODELO'] = df_final['N° ARTICULO'].map(map_mod['MKT NAME'])
                df_final['AÑO MODELO'] = df_final['N° ARTICULO'].map(map_mod['AÑO']).astype('Int64')
                df_final['COLOR'] = df_final['N° ARTICULO'].map(map_mod['COLOR'])
                df_final['MOD COLOR'] = df_final['MODELO'] + " " + df_final['COLOR']

                # =========================
                # 🌎 GEOGRAFÍA
                # =========================
                df_final['STATE'] = df_final['ID RETAIL'].map(mapeo_estado)
                df_final['CITY'] = df_final['ID RETAIL'].map(mapeo_ciudad)

                # =========================
                # 🆔 ID STORE
                # =========================
                df_final['ID STORE'] = df_final['ID'].astype(str) + "-" + df_final['STORE'].astype(str)

                # =========================
                # 🧹 LIMPIEZA FINAL
                # =========================
                df_final = df_final.dropna(subset=['N° ARTICULO'])
                df_final = df_final.reset_index(drop=True)

                # =========================
                # 📊 OUTPUT
                # =========================
                st.success("✅ Consolidación completa sin errores")
                st.dataframe(df_final.head(20))

                st.download_button(
                    "📥 Descargar Consolidado",
                    to_excel(df_final),
                    "SO_CONSOLIDADO_FINAL.xlsx"
                )
