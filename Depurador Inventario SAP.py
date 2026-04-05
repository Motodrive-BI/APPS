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

                # =========================
                # 📚 CATÁLOGOS
                # =========================
                CAT_SKU = pd.read_excel(cat_sku_raw, sheet_name="Sku_retail")
                CATALOGO_MODELO = pd.read_excel(cat_mod_raw, sheet_name="CAT_MOD_v3")
                CATALOGO_SUCURSALES = pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC")

                # =========================
                # 🔥 Coppel
                # =========================
                Coppel['Cadena'] = "COPPEL"

                Coppel['Código'] = Coppel['Código'].astype('str').str.strip().str.upper()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.lower()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Coppel['Item Number'] = Coppel['Código'].map(mapeo_series)

                CATALOGO_SUCURSALES['IDRETAIL'] = (
                    CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() +
                    CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                )
                Coppel['Id Retail'] = Coppel['Tienda'].astype('str') + "COPPEL"
                Coppel['Tienda'] = Coppel['Tienda'].astype('str').str.strip().str.upper()

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first')
                mapeo_items['IDRETAIL'] = mapeo_items['IDRETAIL'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('IDRETAIL')['Sucursal']

                Coppel['SUCURSAL'] = Coppel['Id Retail'].map(mapeo_series)

                Estatus_Cantidad = {'Venta': 1, 'Cancelada': 0, 'En tienda': 1, 'Activada': 1}
                Estatus_Cantidad = pd.DataFrame(list(Estatus_Cantidad.items()), columns=['estatus', 'Cantidad'])

                Coppel['Estatus'] = Coppel['Estatus'].str.upper()
                mapeo_items = Estatus_Cantidad.drop_duplicates(subset=['estatus'], keep='first')
                mapeo_items['estatus'] = mapeo_items['estatus'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('estatus')['Cantidad']

                Coppel['QTY'] = Coppel['Estatus'].map(mapeo_series)

                CODIGO_TIPO = {'FÍSICO': '10', 'VIRTUAL': '30'}
                CODIGO_TIPO = pd.DataFrame(list(CODIGO_TIPO.items()), columns=['Tipo', 'CODIGO'])

                Coppel['Estatus'] = Coppel['Estatus'].str.upper()
                mapeo_items = Estatus_Cantidad.drop_duplicates(subset=['estatus'], keep='first')
                mapeo_items['estatus'] = mapeo_items['estatus'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('estatus')['Cantidad']

                Coppel['COD TIPO'] = Coppel['Estatus'].map(mapeo_series)
                Coppel['Fecha Venta'] = pd.to_datetime(Coppel['Fecha Venta'])

                # =========================
                # RETAIL CHAINS
                # =========================

                # Liverpool
                Liverpool['Canal'] = 'LIVERPOOL'
                Liverpool = Liverpool[Liverpool['Centro'] != 'Resultado total']
                Liverpool['Centro'] = Liverpool['Centro'].astype(int)

                # Suburbia
                Suburbia['Canal'] = 'SUBURBIA'
                Suburbia['CENTRO'] = Suburbia['CENTRO'].astype(int)

                # Sears
                Sears['Canal'] = 'SEARS'
                Sears['Tipo'] = 'Físico'
                Sears['TDA'] = Sears['TDA'].astype(str)

                # LIVERPOOL
                Liverpool['Centro'] = Liverpool['Centro'].astype(str)
                Liverpool['Artículo'] = Liverpool['Artículo'].astype(str)

                Liverpool = Liverpool[~Liverpool['Artículo'].str.contains('Resultado', case=False, na=False)]
                Liverpool['Día/Periodo'] = pd.to_datetime(Liverpool['Día/Periodo'], errors='coerce')
                Liverpool = Liverpool[Liverpool['Día/Periodo'].notna()]
                Liverpool = Liverpool.dropna(subset=['Artículo'])

                Liverpool['Artículo'] = Liverpool['Artículo'].astype('str').str.strip().str.lower()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.lower()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Liverpool['Item Number'] = Liverpool['Artículo'].map(mapeo_series)
                Liverpool['IDRETAIL'] = Liverpool['Centro'].astype(str) + "LIVERPOOL"

                CATALOGO_SUCURSALES['IDRETAIL'] = (
                    CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() +
                    CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                )

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first')
                mapeo_items['IDRETAIL'] = mapeo_items['IDRETAIL'].astype(str).str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('IDRETAIL')['Sucursal']

                Liverpool['SUCURSAL'] = Liverpool['IDRETAIL'].map(mapeo_series)

                # SUBURBIA
                Suburbia['SKU'] = Suburbia['SKU'].astype('str').str.strip().str.lower()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.lower()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Suburbia['Item Number'] = Suburbia['SKU'].map(mapeo_series)
                Suburbia['IDRETAIL'] = Suburbia['CENTRO'].astype(str) + "SUBURBIA"

                CATALOGO_SUCURSALES['IDRETAIL'] = (
                    CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() +
                    CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                )

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first')
                mapeo_items['IDRETAIL'] = mapeo_items['IDRETAIL'].astype(str).str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('IDRETAIL')['Sucursal']

                Suburbia['SUCURSAL'] = Suburbia['IDRETAIL'].map(mapeo_series)

                # SEARS
                Sears['SKU'] = Sears['SKU'].astype('str').str.strip().str.lower()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.lower()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Sears['Item Number'] = Sears['SKU'].map(mapeo_series)
                Sears['IDRETAIL'] = Sears['TDA'].astype(str) + "SEARS"

                CATALOGO_SUCURSALES['IDRETAIL'] = (
                    CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() +
                    CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                )

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first')
                mapeo_items['IDRETAIL'] = mapeo_items['IDRETAIL'].astype(str).str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('IDRETAIL')['Sucursal']

                Sears['SUCURSAL'] = Sears['IDRETAIL'].map(mapeo_series)
                Sears['FECHA'] = pd.to_datetime(Sears['FECHA'].str.replace('-', '/'), format='%m/%d/%Y', errors='coerce')

                # =========================
                # CADENAS ALICIA RETAIL
                # =========================

                # Mavi
                Mavi['CADENA'] = "MAVI"
                Mavi['Item Number'] = ""
                Mavi['Item Number'] = Mavi['Item Number'].astype(str)

                Mavi['CODIGO'] = Mavi['CODIGO'].astype('str').str.strip().str.upper()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Mavi['Item Number'] = Mavi['CODIGO'].map(mapeo_series)

                Mavi['IDRETAIL'] = Mavi['TIENDA'].astype('Int64')
                Mavi['IDRETAIL'] = Mavi['TIENDA'].astype('str') + "MAVI"
                Mavi['SUCURSAL'] = ""
                Mavi['SUCURSAL'] = Mavi['SUCURSAL'].astype(str)

                CATALOGO_SUCURSALES['ID Sucursal'] = CATALOGO_SUCURSALES['ID Sucursal'].astype('str')
                CATALOGO_SUCURSALES['ID RETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'] + CATALOGO_SUCURSALES['Cadena']

                Mavi['IDRETAIL'] = Mavi['IDRETAIL'].astype('str').str.strip().str.upper()

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['ID RETAIL'], keep='first')
                mapeo_items['ID RETAIL'] = mapeo_items['ID RETAIL'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('ID RETAIL')['Sucursal']

                Mavi['SUCURSAL'] = Mavi['IDRETAIL'].map(mapeo_series)

                # Bodesa
                Bodesa['Cadena'] = "BODESA"
                Bodesa['Item Number'] = ""
                Bodesa['Item Number'] = Bodesa['Item Number'].astype(str)

                Bodesa['Materia'] = Bodesa['Materia'].astype('str').str.strip().str.upper()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Bodesa['Item Number'] = Bodesa['Materia'].map(mapeo_series)

                Bodesa['IDRETAIL'] = Bodesa['Centro'].astype('str') + "BODESA"
                Bodesa['SUCURSAL'] = ""
                Bodesa['SUCURSAL'] = Bodesa['SUCURSAL'].astype(str)

                CATALOGO_SUCURSALES['ID Sucursal'] = CATALOGO_SUCURSALES['ID Sucursal'].astype('str')
                CATALOGO_SUCURSALES['ID RETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'] + CATALOGO_SUCURSALES['Cadena']

                Bodesa['IDRETAIL'] = Bodesa['IDRETAIL'].astype('str').str.strip().str.upper()

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['ID RETAIL'], keep='first')
                mapeo_items['ID RETAIL'] = mapeo_items['ID RETAIL'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('ID RETAIL')['Sucursal']

                Bodesa['SUCURSAL'] = Bodesa['IDRETAIL'].map(mapeo_series)
                Bodesa['Fecha Vta'] = pd.to_datetime(Bodesa['Fecha Vta'].str.replace('-', '/'), format='%d/%m/%Y', errors='coerce')

                # Clikstore
                Clikstore['Cadena'] = "CLIKSTORE"
                Clikstore['Item Number'] = ""
                Clikstore['Item Number'] = Clikstore['Item Number'].astype(str)

                Clikstore['SAP'] = Clikstore['SAP'].astype('str').str.strip().str.upper()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Clikstore['Item Number'] = Clikstore['SAP'].map(mapeo_series)

                Clikstore['IDRETAIL'] = Clikstore['ID SUC'].astype('str') + "CLIKSTORE"
                Clikstore['SUCURSAL'] = ""
                Clikstore['SUCURSAL'] = Clikstore['SUCURSAL'].astype(str)

                CATALOGO_SUCURSALES['ID Sucursal'] = CATALOGO_SUCURSALES['ID Sucursal'].astype('str')
                CATALOGO_SUCURSALES['ID RETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'] + CATALOGO_SUCURSALES['Cadena']

                Clikstore['IDRETAIL'] = Clikstore['IDRETAIL'].astype('str').str.strip().str.upper()

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['ID RETAIL'], keep='first')
                mapeo_items['ID RETAIL'] = mapeo_items['ID RETAIL'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('ID RETAIL')['Sucursal']

                Clikstore['SUCURSAL'] = Clikstore['IDRETAIL'].map(mapeo_series)

                # Cklass
                Cklass['Cadena'] = "CKLASS"
                Cklass['Item Number'] = ""
                Cklass['Item Number'] = Cklass['Item Number'].astype(str)

                Cklass['Material'] = Cklass['Material'].astype('str').str.strip().str.upper()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Cklass['Item Number'] = Cklass['Material'].map(mapeo_series)

                Cklass['IDRETAIL'] = Cklass['ID'].astype('str') + "CKLASS"
                Cklass['SUCURSAL'] = ""
                Cklass['SUCURSAL'] = Cklass['SUCURSAL'].astype(str)

                CATALOGO_SUCURSALES['ID Sucursal'] = CATALOGO_SUCURSALES['ID Sucursal'].astype('str')
                CATALOGO_SUCURSALES['ID RETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'] + CATALOGO_SUCURSALES['Cadena']

                Cklass['IDRETAIL'] = Cklass['IDRETAIL'].astype('str').str.strip().str.upper()

                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['ID RETAIL'], keep='first')
                mapeo_items['ID RETAIL'] = mapeo_items['ID RETAIL'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('ID RETAIL')['Sucursal']

                Cklass['SUCURSAL'] = Cklass['IDRETAIL'].map(mapeo_series)

                # ECOMMERCE
                Ecomm['Tienda'] = Ecomm['Tienda'].replace('WM', 'WALMART')
                Ecomm['Tienda'] = Ecomm['Tienda'].replace('SAMS', 'SAM´S CLUB')
                Ecomm['Tienda'] = Ecomm['Tienda'].replace('TL', 'TIENDA EN LINEA')
                Ecomm['Tienda'] = Ecomm['Tienda'].replace('ML', 'MERCADO LIBRE')

                Ecomm['Item Number'] = ""
                Ecomm['Item Number'] = Ecomm['Item Number'].astype(str)

                Ecomm['Unido'] = Ecomm['Unido'].astype('str').str.strip().str.upper()

                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('SKU')['Item']

                Ecomm['Item Number'] = Ecomm['Unido'].map(mapeo_series)
                Ecomm['Sucursal'] = "ECOMMERCE"
                Ecomm['Id'] = 1
                Ecomm['idStore'] = Ecomm['Id'].astype("str") + "-" + Ecomm['Sucursal']

                # =========================
                # CONSOLIDADO SELL OUT RETAIL
                # =========================
                column_names = [
                    "CANAL", "SELL", "FECHA", "COD TIPO", "TIPO", "SKU", "DESCRIPCION",
                    "ESTADO", "QTY", "MONTO", "N° ARTICULO", "CC", "EAN / UPC", "ID",
                    "STORE", "MES", "MES - AÑO", "AÑO", "MODELO", "AÑO MODELO", "COLOR",
                    "MOD COLOR", "ID RETAIL", "STATE", "CITY", "ASEN", "REGION", "CP",
                    "CEDIS COPPEL", "ID STORE"
                ]

                Sell_Out_Retail = pd.DataFrame(columns=column_names)

                Sell_Out_Retail['CANAL'] = pd.concat([Coppel['Cadena'], Liverpool['Canal'], Sears['Canal'], Suburbia['Canal'], Mavi['CADENA'], Bodesa['Cadena'], Clikstore['Cadena'], Cklass['Cadena'], Ecomm['Tienda']], ignore_index=True)
                Sell_Out_Retail['SELL'] = "SO"
                Sell_Out_Retail['FECHA'] = pd.concat([Coppel['Fecha Venta'], Liverpool['Día/Periodo'], Sears['FECHA'], Suburbia['Día'], Mavi['FECHA FACT'], Bodesa['Fecha Vta'], Clikstore['FECHA'], Cklass['Fecha'], Ecomm['Fecha  ']], ignore_index=True)
                Sell_Out_Retail['COD TIPO'] = ""
                Sell_Out_Retail['TIPO'] = ""
                Sell_Out_Retail['SKU'] = pd.concat([Coppel['Código'], Liverpool['Artículo'], Sears['SKU'], Suburbia['SKU'], Mavi['CODIGO'], Bodesa['Materia'], Clikstore['SAP'], Cklass['Material'], Ecomm['Unido']], ignore_index=True)
                Sell_Out_Retail['DESCRIPCION'] = "RE"
                Sell_Out_Retail['ESTADO'] = ""
                Sell_Out_Retail['QTY'] = pd.concat([Coppel['QTY'], Liverpool['Ventas Unidades'], Sears['CANT'], Suburbia['VENTA UNIDADES'], Mavi['CANT.'], Bodesa['Vta pzas'], Clikstore['Cantidad'], Cklass['Cantidad'], Ecomm['Cant']], ignore_index=True).astype('Int64')
                Sell_Out_Retail['MONTO'] = ""
                Sell_Out_Retail['N° ARTICULO'] = pd.concat([Coppel['Item Number'], Liverpool['Item Number'], Sears['Item Number'], Suburbia['Item Number'], Mavi['Item Number'], Bodesa['Item Number'], Clikstore['Item Number'], Cklass['Item Number'], Ecomm['Item Number']], ignore_index=True)
                Sell_Out_Retail['ID'] = pd.concat([Coppel['Tienda'], Liverpool['Centro'], Sears['TDA'], Suburbia['CENTRO'], Mavi['TIENDA'], Bodesa['Centro'], Clikstore['ID SUC'], Cklass['ID'], Ecomm['Id']], ignore_index=True)
                Sell_Out_Retail['STORE'] = pd.concat([Coppel['SUCURSAL'], Liverpool['SUCURSAL'], Sears['SUCURSAL'], Suburbia['SUCURSAL'], Mavi['SUCURSAL'], Bodesa['SUCURSAL'], Clikstore['SUCURSAL'], Cklass['SUCURSAL'], Ecomm['Sucursal']], ignore_index=True)
                Sell_Out_Retail['ID RETAIL'] = pd.concat([Coppel['Id Retail'], Liverpool['IDRETAIL'], Sears['IDRETAIL'], Suburbia['IDRETAIL'], Mavi['IDRETAIL'], Bodesa['IDRETAIL'], Clikstore['IDRETAIL'], Cklass['IDRETAIL'], Ecomm['idStore']], ignore_index=True)

                # Columnas Fecha
                Sell_Out_Retail['Fecha del documento 2'] = pd.to_datetime(Sell_Out_Retail['FECHA'], errors='coerce')
                Sell_Out_Retail['MES'] = Sell_Out_Retail['Fecha del documento 2'].dt.month_name()
                Sell_Out_Retail['MES - AÑO'] = Sell_Out_Retail['MES'] + " " + Sell_Out_Retail['Fecha del documento 2'].dt.strftime('%Y')
                Sell_Out_Retail['AÑO'] = Sell_Out_Retail['Fecha del documento 2'].dt.strftime('%Y')
                Sell_Out_Retail = Sell_Out_Retail.drop(columns='Fecha del documento 2')

                Sell_Out_Retail['ID'] = Sell_Out_Retail['ID'].astype('str')
                Sell_Out_Retail['ID RETAIL'] = Sell_Out_Retail['ID'] + Sell_Out_Retail['CANAL']

                # Columna CC
                CATALOGO_MODELO['CILINDRADA'] = CATALOGO_MODELO['CILINDRADA'].fillna(0).astype('int64')
                CATALOGO_MODELO['CILINDRADA'] = CATALOGO_MODELO['CILINDRADA'].astype('str')
                CATALOGO_MODELO['CILINDRADA'] = CATALOGO_MODELO['CILINDRADA'] + "CC"

                mapeo_items = CATALOGO_MODELO.drop_duplicates(subset=['NÚMERO DE ARTÍCULO (SAP)'], keep='first')
                mapeo_items['NÚMERO DE ARTÍCULO (SAP)'] = mapeo_items['NÚMERO DE ARTÍCULO (SAP)'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('NÚMERO DE ARTÍCULO (SAP)')['CILINDRADA']

                Sell_Out_Retail['CC'] = Sell_Out_Retail['N° ARTICULO'].map(mapeo_series)

                # Columna Modelo
                mapeo_items['NÚMERO DE ARTÍCULO (SAP)'] = mapeo_items['NÚMERO DE ARTÍCULO (SAP)'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('NÚMERO DE ARTÍCULO (SAP)')['MKT NAME']
                Sell_Out_Retail['MODELO'] = Sell_Out_Retail['N° ARTICULO'].map(mapeo_series)

                # Columna Año Modelo
                mapeo_items['NÚMERO DE ARTÍCULO (SAP)'] = mapeo_items['NÚMERO DE ARTÍCULO (SAP)'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('NÚMERO DE ARTÍCULO (SAP)')['AÑO MODEL']
                Sell_Out_Retail['AÑO MODELO'] = Sell_Out_Retail['N° ARTICULO'].map(mapeo_series)
                Sell_Out_Retail['AÑO MODELO'] = Sell_Out_Retail['AÑO MODELO'].astype('Int64')

                # Columna Color
                mapeo_items['NÚMERO DE ARTÍCULO (SAP)'] = mapeo_items['NÚMERO DE ARTÍCULO (SAP)'].astype('str').str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('NÚMERO DE ARTÍCULO (SAP)')['COLOR MODEL']
                Sell_Out_Retail['COLOR'] = Sell_Out_Retail['N° ARTICULO'].map(mapeo_series)

                # Columna Mod Color
                Sell_Out_Retail['MOD COLOR'] = Sell_Out_Retail['MODELO'] + " " + Sell_Out_Retail['COLOR']

                # Columna State
                CATALOGO_SUCURSALES['IDRETAIL'] = (
                    CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() +
                    CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                )
                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first')
                mapeo_items['IDRETAIL'] = mapeo_items['IDRETAIL'].astype(str).str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('IDRETAIL')['Estado']
                Sell_Out_Retail['STATE'] = Sell_Out_Retail['ID RETAIL'].map(mapeo_series)

                # Columna City
                CATALOGO_SUCURSALES['IDRETAIL'] = (
                    CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() +
                    CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                )
                mapeo_items = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first')
                mapeo_items['IDRETAIL'] = mapeo_items['IDRETAIL'].astype(str).str.strip().str.upper()
                mapeo_series = mapeo_items.set_index('IDRETAIL')['Municipio']
                Sell_Out_Retail['CITY'] = Sell_Out_Retail['ID RETAIL'].map(mapeo_series)

                # Columna ID Store
                Sell_Out_Retail['ID'] = Sell_Out_Retail['ID'].astype(str)
                Sell_Out_Retail['STORE'] = Sell_Out_Retail['STORE'].astype(str)
                Sell_Out_Retail['ID STORE'] = Sell_Out_Retail['ID'] + "-" + Sell_Out_Retail['STORE']

                st.success("✅ Consolidación lista")
                st.dataframe(Sell_Out_Retail.head(20))

                st.download_button(
                    "📥 Descargar",
                    to_excel(Sell_Out_Retail),
                    "SO_FINAL.xlsx"
                )
