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
                # 📥 CARGA
                # =========================
                Coppel = pd.read_excel(file_master, sheet_name="Coppel")
                Liverpool = pd.read_excel(file_master, sheet_name="Liverpool")
                Sears = pd.read_excel(file_master, sheet_name="Sears")
                Suburbia = pd.read_excel(file_master, sheet_name="Suburbia")
                Mavi = pd.read_excel(file_master, sheet_name="Mavi")
                Bodesa = pd.read_excel(file_master, sheet_name="Bodesa")
                Clikstore = pd.read_excel(file_master, sheet_name="Clik")
                Cklass = pd.read_excel(file_master, sheet_name="Cklass")
                Ecomm = pd.read_excel(file_master, sheet_name="Ecomm")

                # LIMPIAR COLUMNAS (CLAVE)
                for df in [Coppel, Liverpool, Sears, Suburbia, Mavi, Bodesa, Clikstore, Cklass, Ecomm]:
                    df.columns = df.columns.str.strip()

                # =========================
                # 📚 CATÁLOGOS
                # =========================
                CAT_SKU = pd.read_excel(cat_sku_raw, sheet_name="Sku_retail")
                CAT_MOD = pd.read_excel(cat_mod_raw, sheet_name="CAT_MOD_v3")
                CAT_SUC = pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC")

                CAT_SKU['SKU'] = CAT_SKU['SKU'].astype(str).str.strip().str.upper()
                mapeo_sku = CAT_SKU.drop_duplicates('SKU').set_index('SKU')['Item']

                CAT_SUC['IDRETAIL'] = (
                    CAT_SUC['ID Sucursal'].astype(str).str.strip() +
                    CAT_SUC['Cadena'].astype(str).str.strip()
                ).str.upper()

                mapeo_suc = CAT_SUC.drop_duplicates('IDRETAIL').set_index('IDRETAIL')['Sucursal']

                # =========================
                # 🔥 FIX LIVERPOOL
                # =========================
                Liverpool = Liverpool[~Liverpool['Artículo'].astype(str).str.contains('RESULT', case=False, na=False)]
                Liverpool = Liverpool.dropna(subset=['Artículo'])

                # =========================
                # 🔥 FIX ECOMM (KEYERROR)
                # =========================
                if "Id" not in Ecomm.columns:
                    Ecomm["Id"] = 1

                if "Fecha" not in Ecomm.columns:
                    for col in Ecomm.columns:
                        if "fecha" in col.lower():
                            Ecomm["Fecha"] = Ecomm[col]

                # =========================
                # 🧩 CONSOLIDADO ORIGINAL (RESPETADO)
                # =========================
                Sell_Out_Retail = pd.DataFrame()

                Sell_Out_Retail['CANAL'] = pd.concat([
                    Coppel['Cadena'], Liverpool['Canal'], Sears['Canal'], Suburbia['Canal'],
                    Mavi['CADENA'], Bodesa['Cadena'], Clikstore['Cadena'], Cklass['Cadena'], Ecomm['Tienda']
                ], ignore_index=True)

                Sell_Out_Retail['SELL'] = "SO"

                Sell_Out_Retail['FECHA'] = pd.concat([
                    Coppel['Fecha Venta'], Liverpool['Día/Periodo'], Sears['FECHA'], Suburbia['Día'],
                    Mavi['FECHA FACT'], Bodesa['Fecha Vta'], Clikstore['FECHA'], Cklass['Fecha'], Ecomm['Fecha']
                ], ignore_index=True)

                Sell_Out_Retail['SKU'] = pd.concat([
                    Coppel['Código'], Liverpool['Artículo'], Sears['SKU'], Suburbia['SKU'],
                    Mavi['CODIGO'], Bodesa['Materia'], Clikstore['SAP'], Cklass['Material'], Ecomm['Unido']
                ], ignore_index=True)

                Sell_Out_Retail['QTY'] = pd.concat([
                    Coppel['QTY'], Liverpool['Ventas Unidades'], Sears['CANT'], Suburbia['VENTA UNIDADES'],
                    Mavi['CANT.'], Bodesa['Vta pzas'], Clikstore['Cantidad'], Cklass['Cantidad'], Ecomm['Cant']
                ], ignore_index=True)

                Sell_Out_Retail['N° ARTICULO'] = pd.concat([
                    Coppel['Código'], Liverpool['Artículo'], Sears['SKU'], Suburbia['SKU'],
                    Mavi['CODIGO'], Bodesa['Materia'], Clikstore['SAP'], Cklass['Material'], Ecomm['Unido']
                ], ignore_index=True).map(mapeo_sku)

                Sell_Out_Retail['ID'] = pd.concat([
                    Coppel['Tienda'], Liverpool['Centro'], Sears['TDA'], Suburbia['CENTRO'],
                    Mavi['TIENDA'], Bodesa['Centro'], Clikstore['ID SUC'], Cklass['ID'], Ecomm['Id']
                ], ignore_index=True)

                Sell_Out_Retail['STORE'] = pd.concat([
                    Coppel['SUCURSAL'], Liverpool['SUCURSAL'], Sears['SUCURSAL'], Suburbia['SUCURSAL'],
                    Mavi['SUCURSAL'], Bodesa['SUCURSAL'], Clikstore['SUCURSAL'], Cklass['SUCURSAL'], "ECOMMERCE"
                ], ignore_index=True)

                # =========================
                # 🧹 LIMPIEZA FINAL
                # =========================
                Sell_Out_Retail = Sell_Out_Retail.dropna(subset=['N° ARTICULO'])
                Sell_Out_Retail = Sell_Out_Retail.reset_index(drop=True)

                st.success("✅ Consolidación lista (respetando tu lógica)")
                st.dataframe(Sell_Out_Retail.head(20))

                st.download_button(
                    "📥 Descargar",
                    to_excel(Sell_Out_Retail),
                    "SO_FINAL.xlsx"
                )
