import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoDrive: Master Data Tool", layout="wide")

# --- CONFIGURACIÓN DE GITHUB ---
GITHUB_BASE_URL = "https://raw.githubusercontent.com/Motodrive-BI/APPS/main/"

URLS = {
    "sku": GITHUB_BASE_URL + "Catalogo_SKU_v3 BETA.xlsx",
    "modelos": GITHUB_BASE_URL + "Catalogo_Modelos.xlsx",
    "sucursales": GITHUB_BASE_URL + "Concentrado_Master.xlsx"
}

# --- FUNCIONES DE CARGA ---
@st.cache_data(ttl=3600)
def cargar_excel_github(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        st.error(f"Error cargando catálogo: {url}")
        return None

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- MENÚ LATERAL ---
st.sidebar.title("🛠️ MotoDrive HUB")
opcion = st.sidebar.selectbox("Selecciona el proceso:", ["Inventario Diario (SAP)", "Sell Out Global (SAP)", "Consolidador Retail"])

# Carga previa de catálogos
cat_sku_raw = cargar_excel_github(URLS["sku"])
cat_mod_raw = cargar_excel_github(URLS["modelos"])
cat_suc_raw = cargar_excel_github(URLS["sucursales"])

# --- LÓGICA DE PROCESOS ---

if opcion == "Consolidador Retail":
    st.title("🔗 Consolidador Sell Out Retail")
    st.info("Sube el archivo Layout Retail Master. Los catálogos se cargarán automáticamente desde GitHub.")
    
    file_master = st.file_uploader("Sube Layout Retail Master.xlsx", type=["xlsx"])
    
    if file_master and cat_sku_raw and cat_mod_raw and cat_suc_raw:
        if st.button("🚀 Ejecutar Consolidación"):
            with st.spinner("Procesando todas las cadenas con tu lógica exacta..."):
                # 1. IMPORTAR ARCHIVOS
                Coppel = pd.read_excel(file_master, sheet_name="Coppel")
                Liverpool = pd.read_excel(file_master, sheet_name="Liverpool")
                Sears = pd.read_excel(file_master, sheet_name="Sears")
                Suburbia = pd.read_excel(file_master, sheet_name="Suburbia")
                Mavi = pd.read_excel(file_master, sheet_name="Mavi")
                Bodesa = pd.read_excel(file_master, sheet_name="Bodesa")
                Clikstore = pd.read_excel(file_master, sheet_name="Clik")
                Cklass = pd.read_excel(file_master, sheet_name="Cklass")
                Ecomm = pd.read_excel(file_master, sheet_name="Ecomm")

                # 2. IMPORTAR CATÁLOGOS (Desde memoria)
                CAT_SKU = pd.read_excel(cat_sku_raw, sheet_name="Sku_retail")
                CATALOGO_MODELO = pd.read_excel(cat_mod_raw, sheet_name='CAT_MOD_v3')
                CATALOGO_SUCURSALES = pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC")

                # --- TU LÓGICA EMPIEZA AQUÍ ---
                CAT_SKU['SKU'] = CAT_SKU['SKU'].astype("str")
                
                # COPPEL
                Coppel['Cadena'] = "COPPEL"
                Coppel['Código'] = Coppel['Código'].astype('str').str.strip().str.upper()
                mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first').copy()
                mapeo_items['SKU'] = mapeo_items['SKU'].astype('str').str.strip().str.lower()
                mapeo_series = mapeo_items.set_index('SKU')['Item']
                Coppel['Item Number'] = Coppel['Código'].map(mapeo_series)

                CATALOGO_SUCURSALES['IDRETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() + CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                Coppel['Id Retail'] = Coppel['Tienda'].astype('str') + "COPPEL"
                Coppel['Tienda'] = Coppel['Tienda'].astype('str').str.strip().str.upper()
                mapeo_items_suc = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first').copy()
                mapeo_items_suc['IDRETAIL'] = mapeo_items_suc['IDRETAIL'].astype('str').str.strip().str.upper()
                mapeo_series_suc = mapeo_items_suc.set_index('IDRETAIL')['Sucursal']
                Coppel['SUCURSAL'] = Coppel['Id Retail'].map(mapeo_series_suc)

                Estatus_Cantidad = pd.DataFrame(list({'Venta': 1, 'Cancelada': 0, 'En tienda': 1, 'Activada': 1}.items()), columns=['estatus', 'Cantidad'])
                Coppel['Estatus'] = Coppel['Estatus'].str.upper()
                mapeo_estatus = Estatus_Cantidad.drop_duplicates(subset=['estatus'], keep='first').copy()
                mapeo_estatus['estatus'] = mapeo_estatus['estatus'].astype('str').str.strip().str.upper()
                Coppel['QTY'] = Coppel['Estatus'].map(mapeo_estatus.set_index('estatus')['Cantidad'])
                Coppel['COD TIPO'] = Coppel['QTY'] # Según tu script mapeas lo mismo
                Coppel['Fecha Venta'] = pd.to_datetime(Coppel['Fecha Venta'])

                # LIVERPOOL
                Liverpool['Canal'] = 'LIVERPOOL'
                Liverpool = Liverpool[Liverpool['Centro'] != 'Resultado total']
                Liverpool['Centro'] = Liverpool['Centro'].astype(str)
                Liverpool['Artículo'] = Liverpool['Artículo'].astype(str)
                Liverpool = Liverpool[~Liverpool['Artículo'].str.contains('Resultado', case=False, na=False)]
                Liverpool['Día/Periodo'] = pd.to_datetime(Liverpool['Día/Periodo'], errors='coerce')
                Liverpool = Liverpool[Liverpool['Día/Periodo'].notna()]
                Liverpool['Item Number'] = Liverpool['Artículo'].astype(str).str.strip().str.lower().map(mapeo_series)
                Liverpool['IDRETAIL'] = Liverpool['Centro'].astype(str) + "LIVERPOOL"
                Liverpool['SUCURSAL'] = Liverpool['IDRETAIL'].map(mapeo_series_suc)

                # SUBURBIA
                Suburbia['Canal'] = 'SUBURBIA'
                Suburbia['Item Number'] = Suburbia['SKU'].astype(str).str.strip().str.lower().map(mapeo_series)
                Suburbia['IDRETAIL'] = Suburbia['CENTRO'].astype(str) + "SUBURBIA"
                Suburbia['SUCURSAL'] = Suburbia['IDRETAIL'].map(mapeo_series_suc)

                # SEARS
                Sears['Canal'] = 'SEARS'
                Sears['TDA'] = Sears['TDA'].astype(str)
                Sears['Item Number'] = Sears['SKU'].astype(str).str.strip().str.lower().map(mapeo_series)
                Sears['IDRETAIL'] = Sears['TDA'].astype(str) + "SEARS"
                Sears['SUCURSAL'] = Sears['IDRETAIL'].map(mapeo_series_suc)
                Sears['FECHA'] = pd.to_datetime(Sears['FECHA'].str.replace('-', '/'), format='%m/%d/%Y', errors='coerce')

                # MAVI
                Mavi['CADENA'] = "MAVI"
                mapeo_mavi = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first').copy()
                mapeo_mavi['SKU'] = mapeo_mavi['SKU'].astype(str).str.strip().str.upper()
                Mavi['Item Number'] = Mavi['CODIGO'].astype(str).str.strip().str.upper().map(mapeo_mavi.set_index('SKU')['Item'])
                Mavi['IDRETAIL'] = Mavi['TIENDA'].astype(str) + "MAVI"
                CATALOGO_SUCURSALES['ID RETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'].astype(str) + CATALOGO_SUCURSALES['Cadena']
                map_suc_mavi = CATALOGO_SUCURSALES.drop_duplicates('ID RETAIL').set_index('ID RETAIL')['Sucursal']
                Mavi['SUCURSAL'] = Mavi['IDRETAIL'].astype(str).str.strip().str.upper().map(map_suc_mavi)

                # BODESA
                Bodesa['Cadena'] = "BODESA"
                Bodesa['Item Number'] = Bodesa['Materia'].astype(str).str.strip().str.upper().map(mapeo_mavi.set_index('SKU')['Item'])
                Bodesa['IDRETAIL'] = Bodesa['Centro'].astype(str) + "BODESA"
                Bodesa['SUCURSAL'] = Bodesa['IDRETAIL'].astype(str).str.strip().str.upper().map(map_suc_mavi)
                Bodesa['Fecha Vta'] = pd.to_datetime(Bodesa['Fecha Vta'].str.replace('-', '/'), format='%d/%m/%Y', errors='coerce')

                # CLIKSTORE
                Clikstore['Cadena'] = "CLIKSTORE"
                Clikstore['Item Number'] = Clikstore['SAP'].astype(str).str.strip().str.upper().map(mapeo_mavi.set_index('SKU')['Item'])
                Clikstore['IDRETAIL'] = Clikstore['ID SUC'].astype(str) + "CLIKSTORE"
                Clikstore['SUCURSAL'] = Clikstore['IDRETAIL'].astype(str).str.strip().str.upper().map(map_suc_mavi)

                # CKLASS
                Cklass['Cadena'] = "CKLASS"
                Cklass['Item Number'] = Cklass['Material'].astype(str).str.strip().str.upper().map(mapeo_mavi.set_index('SKU')['Item'])
                Cklass['IDRETAIL'] = Cklass['ID'].astype(str) + "CKLASS"
                Cklass['SUCURSAL'] = Cklass['IDRETAIL'].astype(str).str.strip().str.upper().map(map_suc_mavi)

                # ECOMMERCE
                Ecomm['Tienda'] = Ecomm['Tienda'].replace({'WM': 'WALMART', 'SAMS': 'SAM´S CLUB', 'TL': 'TIENDA EN LINEA', 'ML': 'MERCADO LIBRE'})
                Ecomm['Item Number'] = Ecomm['Unido'].astype(str).str.strip().str.upper().map(mapeo_mavi.set_index('SKU')['Item'])
                Ecomm['Sucursal'] = "ECOMMERCE"
                Ecomm['Id'] = 1
                Ecomm['idStore'] = Ecomm['Id'].astype(str) + "-" + Ecomm['Sucursal']

                # CONSOLIDADO FINAL
                column_names = ["CANAL", "SELL", "FECHA", "COD TIPO", "TIPO", "SKU", "DESCRIPCION", "ESTADO", "QTY", "MONTO", "N° ARTICULO", "CC", "EAN / UPC", "ID", "STORE", "MES", "MES - AÑO", "AÑO", "MODELO", "AÑO MODELO", "COLOR", "MOD COLOR", "ID RETAIL", "STATE", "CITY", "ASEN", "REGION", "CP", "CEDIS COPPEL", "ID STORE"]
                Sell_Out_Retail = pd.DataFrame(columns=column_names)
                
                Sell_Out_Retail['CANAL'] = pd.concat([Coppel['Cadena'], Liverpool['Canal'], Sears['Canal'], Suburbia['Canal'], Mavi['CADENA'], Bodesa['Cadena'], Clikstore['Cadena'], Cklass['Cadena'], Ecomm['Tienda']])
                Sell_Out_Retail['SELL'] = "SO"
                Sell_Out_Retail['FECHA'] = pd.concat([Coppel['Fecha Venta'], Liverpool['Día/Periodo'], Sears['FECHA'], Suburbia['Día'], Mavi['FECHA FACT'], Bodesa['Fecha Vta'], Clikstore['FECHA'], Cklass['Fecha'], Ecomm['Fecha  ']])
                Sell_Out_Retail['SKU'] = pd.concat([Coppel['Código'], Liverpool['Artículo'], Sears['SKU'], Suburbia['SKU'], Mavi['CODIGO'], Bodesa['Materia'], Clikstore['SAP'], Cklass['Material'], Ecomm['Unido']])
                Sell_Out_Retail['QTY'] = pd.concat([Coppel['QTY'], Liverpool['Ventas Unidades'], Sears['CANT'], Suburbia['VENTA UNIDADES'], Mavi['CANT.'], Bodesa['Vta pzas'], Clikstore['Cantidad'], Cklass['Cantidad'], Ecomm['Cant']]).astype('Int64')
                Sell_Out_Retail['N° ARTICULO'] = pd.concat([Coppel['Item Number'], Liverpool['Item Number'], Sears['Item Number'], Suburbia['Item Number'], Mavi['Item Number'], Bodesa['Item Number'], Clikstore['Item Number'], Cklass['Item Number'], Ecomm['Item Number']])
                Sell_Out_Retail['ID'] = pd.concat([Coppel['Tienda'], Liverpool['Centro'], Sears['TDA'], Suburbia['CENTRO'], Mavi['TIENDA'], Bodesa['Centro'], Clikstore['ID SUC'], Cklass['ID'], Ecomm['Id']])
                Sell_Out_Retail['STORE'] = pd.concat([Coppel['SUCURSAL'], Liverpool['SUCURSAL'], Sears['SUCURSAL'], Suburbia['SUCURSAL'], Mavi['SUCURSAL'], Bodesa['SUCURSAL'], Clikstore['SUCURSAL'], Cklass['SUCURSAL'], Ecomm['Sucursal']])
                
                # Procesamiento de Fechas y Columnas Extra (Cilindrada, Modelo, etc.)
                Sell_Out_Retail['FECHA'] = pd.to_datetime(Sell_Out_Retail['FECHA'], errors='coerce')
                Sell_Out_Retail['MES'] = Sell_Out_Retail['FECHA'].dt.month_name()
                Sell_Out_Retail['AÑO'] = Sell_Out_Retail['FECHA'].dt.strftime('%Y')
                Sell_Out_Retail['MES - AÑO'] = Sell_Out_Retail['MES'] + " " + Sell_Out_Retail['AÑO']
                
                # Mapeos de Catálogo Modelos
                CATALOGO_MODELO['CILINDRADA'] = (CATALOGO_MODELO['CILINDRADA'].fillna(0).astype('int64').astype(str) + "CC")
                map_mod = CATALOGO_MODELO.drop_duplicates('NÚMERO DE ARTÍCULO (SAP)').set_index('NÚMERO DE ARTÍCULO (SAP)')
                
                Sell_Out_Retail['N° ARTICULO'] = Sell_Out_Retail['N° ARTICULO'].astype(str).str.strip().str.upper()
                Sell_Out_Retail['CC'] = Sell_Out_Retail['N° ARTICULO'].map(map_mod['CILINDRADA'])
                Sell_Out_Retail['MODELO'] = Sell_Out_Retail['N° ARTICULO'].map(map_mod['MKT NAME'])
                Sell_Out_Retail['AÑO MODELO'] = Sell_Out_Retail['N° ARTICULO'].map(map_mod['AÑO']).astype('Int64')
                Sell_Out_Retail['COLOR'] = Sell_Out_Retail['N° ARTICULO'].map(map_mod['COLOR'])
                Sell_Out_Retail['MOD COLOR'] = Sell_Out_Retail['MODELO'] + " " + Sell_Out_Retail['COLOR']
                
                # Estados y Ciudades
                Sell_Out_Retail['ID'] = Sell_Out_Retail['ID'].astype(str)
                Sell_Out_Retail['ID RETAIL'] = Sell_Out_Retail['ID'] + Sell_Out_Retail['CANAL']
                map_geo = CATALOGO_SUCURSALES.drop_duplicates('IDRETAIL').set_index('IDRETAIL')
                Sell_Out_Retail['STATE'] = Sell_Out_Retail['ID RETAIL'].map(map_geo['Estado'])
                Sell_Out_Retail['CITY'] = Sell_Out_Retail['ID RETAIL'].map(map_geo['Municipio'])
                Sell_Out_Retail['ID STORE'] = Sell_Out_Retail['ID'] + "-" + Sell_Out_Retail['STORE']

                st.success("✅ Consolidación exitosa con tu lógica original")
                st.dataframe(Sell_Out_Retail.head(10))
                
                st.download_button("📥 Descargar Sell Out Consolidado", to_excel(Sell_Out_Retail), "SO_CONSOLIDADO_RETAIL.xlsx")

# --- OTROS PROCESOS (Simplificados) ---
elif opcion == "Inventario Diario (SAP)":
    st.title("📦 Inventario Diario")
    # (Código anterior del inventario)
