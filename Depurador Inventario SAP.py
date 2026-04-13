import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ==============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(page_title="HERRAMIENTAS DE DEPURACIÓN MOTODRIVE", layout="wide")

# --- CONFIGURACIÓN DE GITHUB ---
GITHUB_BASE_URL = "https://raw.githubusercontent.com/Motodrive-BI/APPS/main/"

URLS = {
    "sku": GITHUB_BASE_URL + "Catalogo_SKU_v3 BETA.xlsx",
    "modelos": GITHUB_BASE_URL + "Catalogo_Modelos.xlsx",
    "sucursales": GITHUB_BASE_URL + "Concentrado_Master.xlsx"
}

# ==============================================================================
# FUNCIONES DE SOPORTE
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_excel_github(url):
    """Descarga archivos Excel desde GitHub y los mantiene en caché."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        st.error(f"Error cargando catálogo desde GitHub: {url}")
        return None

def limpiar_columnas(df):
    """Elimina espacios en blanco en los nombres de las columnas."""
    df.columns = df.columns.str.strip()
    return df

def mapeo_seguro(cat_df, key_col, value_col, case='lower'):
    """Crea una Serie de mapeo garantizando un índice único y normalizado."""
    tmp = cat_df.copy()
    tmp[key_col] = tmp[key_col].astype(str).str.strip()
    if case == 'lower':
        tmp[key_col] = tmp[key_col].str.lower()
    elif case == 'upper':
        tmp[key_col] = tmp[key_col].str.upper()
    
    # Eliminar duplicados para evitar errores en el reindexado
    tmp = tmp[~tmp[key_col].duplicated(keep='first')]
    return tmp.set_index(key_col)[value_col]

def to_excel(df):
    """Convierte un DataFrame a un objeto binario de Excel para descarga."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Depurado')
    return output.getvalue()

# ==============================================================================
# CARGA DE CATÁLOGOS MAESTROS
# ==============================================================================
cat_sku_raw = cargar_excel_github(URLS["sku"])
cat_mod_raw = cargar_excel_github(URLS["modelos"])
cat_suc_raw = cargar_excel_github(URLS["sucursales"])

# ==============================================================================
# INTERFAZ: SIDEBAR
# ==============================================================================
st.sidebar.title("📊 Panel de Control")
opcion = st.sidebar.selectbox(
    "Selecciona la herramienta:",
    [
        "Reporte Diario de Inventarios", 
        "Reporte de Sell Out Global", 
        "Consolidador Sell Out Retail", 
        "Consolidador Inventarios Retail"
    ]
)

# ==============================================================================
# 1. REPORTE DIARIO DE INVENTARIOS (SAP)
# ==============================================================================
if opcion == "Reporte Diario de Inventarios":
    st.title("📦 Depurador: Inventory SAP")
    archivo = st.file_uploader("Cargar archivo de Inventario", type=["xlsx", "xls"])

    if archivo:
        motor = "xlrd" if archivo.name.endswith(".xls") else "openpyxl"
        df = pd.read_excel(archivo, header=None, engine=motor)

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
        st.download_button("📥 Descargar Inventario Depurado", to_excel(df_final), "inventario_sap.xlsx")

# ==============================================================================
# 2. SELL OUT GLOBAL
# ==============================================================================
elif opcion == "Reporte de Sell Out Global":
    st.title("🚀 Sell Out Global")
    archivo = st.file_uploader("Cargar archivo de Ventas Global", type=["xlsx", "xls"])

    if archivo:
        motor = "xlrd" if archivo.name.endswith(".xls") else "openpyxl"
        df = pd.read_excel(archivo, engine=motor)
        df = limpiar_columnas(df)

        if 'Código Postal' in df.columns: df['Código Postal'] = df['Código Postal'].astype(str)
        if 'Teléfono' in df.columns: df['Teléfono'] = df['Teléfono'].astype(str)
        if 'Fecha de fabricación' in df.columns:
            df['Fecha de fabricación'] = pd.to_datetime(df['Fecha de fabricación'], errors='coerce')

        columnas_reporte = [
            'Fecha del documento', 'Vendedor', 'Familia del modelo', 'Nombre del Modelo',
            'Color', 'Item', 'No Serie / VIN', 'Sucursal', 'Cantidad', 'Precio total de venta con IVA'
        ]
        
        columnas_existentes = [c for c in columnas_reporte if c in df.columns]
        df_final = df[columnas_existentes]

        st.dataframe(df_final.head())
        st.download_button("📥 Descargar Sell Out Global", to_excel(df_final), "sellout_global.xlsx")

# ==============================================================================
# 3. CONSOLIDADOR RETAIL (VENTAS)
# ==============================================================================
# =========================
# CONSOLIDADOR FINAL FULL
# =========================
elif opcion == "Consolidador Sell Out Retail":

    st.title("🔗 Consolidador Sell Out Retail")
    file_master = st.file_uploader("Sube Layout Retail Master.xlsx", type=["xlsx"])

    if file_master and cat_sku_raw and cat_mod_raw and cat_suc_raw:

        if st.button("🚀 Ejecutar Consolidación"):

            with st.spinner("Procesando..."):

                # =========================
                # 📥 CARGA
                # =========================
                Coppel    = pd.read_excel(file_master, sheet_name="Coppel")
                Liverpool = pd.read_excel(file_master, sheet_name="Liverpool")
                Sears     = pd.read_excel(file_master, sheet_name="Sears")
                Suburbia  = pd.read_excel(file_master, sheet_name="Suburbia")
                Mavi      = pd.read_excel(file_master, sheet_name="Mavi")
                Bodesa    = pd.read_excel(file_master, sheet_name="Bodesa")
                Clikstore = pd.read_excel(file_master, sheet_name="Clik")
                Cklass    = pd.read_excel(file_master, sheet_name="Cklass")
                Ecomm     = pd.read_excel(file_master, sheet_name="Ecomm")

                # =========================
                # 📚 CATÁLOGOS
                # =========================
                CAT_SKU             = pd.read_excel(cat_sku_raw, sheet_name="Sku_retail")
                CATALOGO_MODELO     = pd.read_excel(cat_mod_raw, sheet_name="CAT_MOD_v3")
                CATALOGO_SUCURSALES = pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC")

                # Series maestras SKU -> Item
                serie_sku_item_lower = mapeo_seguro(CAT_SKU, 'SKU', 'Item', case='lower')
                serie_sku_item_upper = mapeo_seguro(CAT_SKU, 'SKU', 'Item', case='upper')

                # Helper: serie IDRETAIL -> campo desde CATALOGO_SUCURSALES
                def serie_suc(campo):
                    tmp = CATALOGO_SUCURSALES.copy()
                    tmp['IDRETAIL'] = (
                        tmp['ID Sucursal'].astype(str).str.strip() +
                        tmp['Cadena'].astype(str).str.strip()
                    )
                    return mapeo_seguro(tmp, 'IDRETAIL', campo, case='upper')

                # Helper: serie ID RETAIL (concatenacion distinta usada por Mavi/Bodesa/Clikstore/Cklass)
                def serie_suc_idretail(campo):
                    tmp = CATALOGO_SUCURSALES.copy()
                    tmp['ID Sucursal'] = tmp['ID Sucursal'].astype('str')
                    tmp['ID RETAIL'] = tmp['ID Sucursal'] + tmp['Cadena']
                    return mapeo_seguro(tmp, 'ID RETAIL', campo, case='upper')

                # =========================
                # 🔥 Coppel
                # =========================
                Coppel['Cadena']  = "COPPEL"
                Coppel['Código']  = Coppel['Código'].astype('str').str.strip().str.upper()
                Coppel['Item Number'] = Coppel['Código'].str.lower().map(serie_sku_item_lower)

                Coppel['Id Retail'] = Coppel['Tienda'].astype('str') + "COPPEL"
                Coppel['Tienda']    = Coppel['Tienda'].astype('str').str.strip().str.upper()
                Coppel['SUCURSAL']  = Coppel['Id Retail'].str.upper().map(serie_suc('Sucursal'))

                Estatus_Cantidad = pd.DataFrame(
                    [('VENTA', 1), ('CANCELADA', 0), ('EN TIENDA', 1), ('ACTIVADA', 1)],
                    columns=['estatus', 'Cantidad']
                )
                Coppel['Estatus'] = Coppel['Estatus'].str.upper()
                mapeo_qty = mapeo_seguro(Estatus_Cantidad, 'estatus', 'Cantidad', case='upper')
                Coppel['QTY']      = Coppel['Estatus'].map(mapeo_qty)
                Coppel['COD TIPO'] = Coppel['Estatus'].map(mapeo_qty)
                Coppel['Fecha Venta'] = pd.to_datetime(Coppel['Fecha Venta'])

                # =========================
                # Liverpool
                # =========================
                Liverpool['Canal'] = 'LIVERPOOL'
                Liverpool = Liverpool[Liverpool['Centro'] != 'Resultado total']
                Liverpool['Centro']      = Liverpool['Centro'].astype(int).astype(str)
                Liverpool['Artículo']    = Liverpool['Artículo'].astype(str)
                Liverpool = Liverpool[~Liverpool['Artículo'].str.contains('Resultado', case=False, na=False)]
                Liverpool['Día/Periodo'] = pd.to_datetime(Liverpool['Día/Periodo'], errors='coerce')
                Liverpool = Liverpool[Liverpool['Día/Periodo'].notna()]
                Liverpool = Liverpool.dropna(subset=['Artículo'])

                Liverpool['Artículo']    = Liverpool['Artículo'].str.strip().str.lower()
                Liverpool['Item Number'] = Liverpool['Artículo'].map(serie_sku_item_lower)
                Liverpool['IDRETAIL']    = Liverpool['Centro'].astype(str) + "LIVERPOOL"
                Liverpool['SUCURSAL']    = Liverpool['IDRETAIL'].str.upper().map(serie_suc('Sucursal'))

                # =========================
                # Suburbia
                # =========================
                Suburbia['Canal']  = 'SUBURBIA'
                Suburbia['CENTRO'] = Suburbia['CENTRO'].astype(int)
                Suburbia['SKU']    = Suburbia['SKU'].astype('str').str.strip().str.lower()
                Suburbia['Item Number'] = Suburbia['SKU'].map(serie_sku_item_lower)
                Suburbia['IDRETAIL']    = Suburbia['CENTRO'].astype(str) + "SUBURBIA"
                Suburbia['SUCURSAL']    = Suburbia['IDRETAIL'].str.upper().map(serie_suc('Sucursal'))

                # =========================
                # Sears
                # =========================
                Sears['Canal'] = 'SEARS'
                Sears['Tipo']  = 'Físico'
                Sears['TDA']   = Sears['TDA'].astype(str)
                Sears['SKU']   = Sears['SKU'].astype('str').str.strip().str.lower()
                Sears['Item Number'] = Sears['SKU'].map(serie_sku_item_lower)
                Sears['IDRETAIL']    = Sears['TDA'].astype(str) + "SEARS"
                Sears['SUCURSAL']    = Sears['IDRETAIL'].str.upper().map(serie_suc('Sucursal'))
                Sears['FECHA']       = pd.to_datetime(
                    Sears['FECHA'].astype(str).str.replace('-', '/'),
                    format='%m/%d/%Y', errors='coerce'
                )

                # =========================
                # Mavi
                # =========================
                Mavi['CADENA']      = "MAVI"
                Mavi['Item Number'] = ""
                Mavi['CODIGO']      = Mavi['CODIGO'].astype('str').str.strip().str.upper()
                Mavi['Item Number'] = Mavi['CODIGO'].map(serie_sku_item_upper)
                Mavi['IDRETAIL']    = Mavi['TIENDA'].astype('str') + "MAVI"
                Mavi['SUCURSAL']    = ""
                Mavi['IDRETAIL']    = Mavi['IDRETAIL'].astype('str').str.strip().str.upper()
                Mavi['SUCURSAL']    = Mavi['IDRETAIL'].map(serie_suc_idretail('Sucursal'))

                # =========================
                # Bodesa
                # =========================
                Bodesa['Cadena']      = "BODESA"
                Bodesa['Item Number'] = ""
                Bodesa['Materia']     = Bodesa['Materia'].astype('str').str.strip().str.upper()
                Bodesa['Item Number'] = Bodesa['Materia'].map(serie_sku_item_upper)
                Bodesa['IDRETAIL']    = Bodesa['Centro'].astype('str') + "BODESA"
                Bodesa['SUCURSAL']    = ""
                Bodesa['IDRETAIL']    = Bodesa['IDRETAIL'].astype('str').str.strip().str.upper()
                Bodesa['SUCURSAL']    = Bodesa['IDRETAIL'].map(serie_suc_idretail('Sucursal'))
                Bodesa['Fecha Vta']   = pd.to_datetime(
                    Bodesa['Fecha Vta'].astype(str).str.replace('-', '/'),
                    format='%d/%m/%Y', errors='coerce'
                )

                # =========================
                # Clikstore
                # =========================
                Clikstore['Cadena']      = "CLIKSTORE"
                Clikstore['Item Number'] = ""
                Clikstore['SAP']         = Clikstore['SAP'].astype('str').str.strip().str.upper()
                Clikstore['Item Number'] = Clikstore['SAP'].map(serie_sku_item_upper)
                Clikstore['IDRETAIL']    = Clikstore['ID SUC'].astype('str') + "CLIKSTORE"
                Clikstore['SUCURSAL']    = ""
                Clikstore['IDRETAIL']    = Clikstore['IDRETAIL'].astype('str').str.strip().str.upper()
                Clikstore['SUCURSAL']    = Clikstore['IDRETAIL'].map(serie_suc_idretail('Sucursal'))

                # =========================
                # Cklass
                # =========================
                Cklass['Cadena']      = "CKLASS"
                Cklass['Item Number'] = ""
                Cklass['Material']    = Cklass['Material'].astype('str').str.strip().str.upper()
                Cklass['Item Number'] = Cklass['Material'].map(serie_sku_item_upper)
                Cklass['IDRETAIL']    = Cklass['ID'].astype('str') + "CKLASS"
                Cklass['SUCURSAL']    = ""
                Cklass['IDRETAIL']    = Cklass['IDRETAIL'].astype('str').str.strip().str.upper()
                Cklass['SUCURSAL']    = Cklass['IDRETAIL'].map(serie_suc_idretail('Sucursal'))

                # =========================
                # Ecomm
                # =========================
                Ecomm['Tienda'] = Ecomm['Tienda'].replace({
                    'WM': 'WALMART', 'SAMS': "SAM´S CLUB",
                    'TL': 'TIENDA EN LINEA', 'ML': 'MERCADO LIBRE'
                })
                Ecomm['Item Number'] = ""
                Ecomm['Unido']       = Ecomm['Unido'].astype('str').str.strip().str.upper()
                Ecomm['Item Number'] = Ecomm['Unido'].map(serie_sku_item_upper)
                Ecomm['Sucursal']    = "ECOMMERCE"
                Ecomm['Id']          = 1
                Ecomm['idStore']     = Ecomm['Id'].astype("str") + "-" + Ecomm['Sucursal']

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

                Sell_Out_Retail['CANAL'] = pd.concat([
                    Coppel['Cadena'], Liverpool['Canal'], Sears['Canal'], Suburbia['Canal'],
                    Mavi['CADENA'], Bodesa['Cadena'], Clikstore['Cadena'], Cklass['Cadena'], Ecomm['Tienda']
                ], ignore_index=True)

                Sell_Out_Retail['SELL'] = "SO"

                Sell_Out_Retail['FECHA'] = pd.concat([
                    Coppel['Fecha Venta'], Liverpool['Día/Periodo'], Sears['FECHA'], Suburbia['Día'],
                    Mavi['FECHA FACT'], Bodesa['Fecha Vta'], Clikstore['FECHA'], Cklass['Fecha'], Ecomm['Fecha  ']
                ], ignore_index=True)

                Sell_Out_Retail['COD TIPO']   = ""
                Sell_Out_Retail['TIPO']        = ""

                Sell_Out_Retail['SKU'] = pd.concat([
                    Coppel['Código'], Liverpool['Artículo'], Sears['SKU'], Suburbia['SKU'],
                    Mavi['CODIGO'], Bodesa['Materia'], Clikstore['SAP'], Cklass['Material'], Ecomm['Unido']
                ], ignore_index=True)

                Sell_Out_Retail['DESCRIPCION'] = "RE"
                Sell_Out_Retail['ESTADO']       = ""

                Sell_Out_Retail['QTY'] = pd.concat([
                    Coppel['QTY'], Liverpool['Ventas Unidades'], Sears['CANT'], Suburbia['VENTA UNIDADES'],
                    Mavi['CANT.'], Bodesa['Vta pzas'], Clikstore['Cantidad'], Cklass['Cantidad'], Ecomm['Cant']
                ], ignore_index=True).astype('Int64')

                Sell_Out_Retail['MONTO'] = ""

                Sell_Out_Retail['N° ARTICULO'] = pd.concat([
                    Coppel['Item Number'], Liverpool['Item Number'], Sears['Item Number'], Suburbia['Item Number'],
                    Mavi['Item Number'], Bodesa['Item Number'], Clikstore['Item Number'], Cklass['Item Number'], Ecomm['Item Number']
                ], ignore_index=True)

                Sell_Out_Retail['ID'] = pd.concat([
                    Coppel['Tienda'], Liverpool['Centro'], Sears['TDA'], Suburbia['CENTRO'],
                    Mavi['TIENDA'], Bodesa['Centro'], Clikstore['ID SUC'], Cklass['ID'], Ecomm['Id']
                ], ignore_index=True)

                Sell_Out_Retail['STORE'] = pd.concat([
                    Coppel['SUCURSAL'], Liverpool['SUCURSAL'], Sears['SUCURSAL'], Suburbia['SUCURSAL'],
                    Mavi['SUCURSAL'], Bodesa['SUCURSAL'], Clikstore['SUCURSAL'], Cklass['SUCURSAL'], Ecomm['Sucursal']
                ], ignore_index=True)

                Sell_Out_Retail['ID RETAIL'] = pd.concat([
                    Coppel['Id Retail'], Liverpool['IDRETAIL'], Sears['IDRETAIL'], Suburbia['IDRETAIL'],
                    Mavi['IDRETAIL'], Bodesa['IDRETAIL'], Clikstore['IDRETAIL'], Cklass['IDRETAIL'], Ecomm['idStore']
                ], ignore_index=True)

                # Columnas Fecha
                Sell_Out_Retail['_fecha_tmp'] = pd.to_datetime(Sell_Out_Retail['FECHA'], errors='coerce')
                Sell_Out_Retail['MES']         = Sell_Out_Retail['_fecha_tmp'].dt.month_name()
                Sell_Out_Retail['MES - AÑO']   = Sell_Out_Retail['MES'] + " " + Sell_Out_Retail['_fecha_tmp'].dt.strftime('%Y')
                Sell_Out_Retail['AÑO']         = Sell_Out_Retail['_fecha_tmp'].dt.strftime('%Y')
                Sell_Out_Retail = Sell_Out_Retail.drop(columns='_fecha_tmp')

                Sell_Out_Retail['ID']        = Sell_Out_Retail['ID'].astype('str')
                Sell_Out_Retail['ID RETAIL'] = Sell_Out_Retail['ID'] + Sell_Out_Retail['CANAL']

                # Columnas desde Catálogo Modelo
                CATALOGO_MODELO['CILINDRADA'] = (
                    CATALOGO_MODELO['CILINDRADA'].fillna(0).astype('int64').astype('str') + "CC"
                )
                serie_cc    = mapeo_seguro(CATALOGO_MODELO, 'NÚMERO DE ARTÍCULO (SAP)', 'CILINDRADA',  case='upper')
                serie_mkt   = mapeo_seguro(CATALOGO_MODELO, 'NÚMERO DE ARTÍCULO (SAP)', 'MKT NAME',    case='upper')
                serie_anio  = mapeo_seguro(CATALOGO_MODELO, 'NÚMERO DE ARTÍCULO (SAP)', 'AÑO',   case='upper')
                serie_color = mapeo_seguro(CATALOGO_MODELO, 'NÚMERO DE ARTÍCULO (SAP)', 'COLOR', case='upper')

                art_upper = Sell_Out_Retail['N° ARTICULO'].astype(str).str.strip().str.upper()
                Sell_Out_Retail['CC']         = art_upper.map(serie_cc)
                Sell_Out_Retail['MODELO']     = art_upper.map(serie_mkt)
                Sell_Out_Retail['AÑO MODELO'] = art_upper.map(serie_anio)
                Sell_Out_Retail['AÑO MODELO'] = Sell_Out_Retail['AÑO MODELO'].astype('Int64')
                Sell_Out_Retail['COLOR']      = art_upper.map(serie_color)
                Sell_Out_Retail['MOD COLOR']  = Sell_Out_Retail['MODELO'] + " " + Sell_Out_Retail['COLOR']

                # Columnas State y City
                id_retail_upper = Sell_Out_Retail['ID RETAIL'].astype(str).str.strip().str.upper()
                Sell_Out_Retail['STATE'] = id_retail_upper.map(serie_suc('Estado'))
                Sell_Out_Retail['CITY']  = id_retail_upper.map(serie_suc('Municipio'))

                # Columna ID Store
                Sell_Out_Retail['ID']       = Sell_Out_Retail['ID'].astype(str)
                Sell_Out_Retail['STORE']    = Sell_Out_Retail['STORE'].astype(str)
                Sell_Out_Retail['ID STORE'] = Sell_Out_Retail['ID'] + "-" + Sell_Out_Retail['STORE']

                st.success("✅ Consolidación lista")
                st.dataframe(Sell_Out_Retail.head(20))

                st.download_button(
                    "📥 Descargar",
                    to_excel(Sell_Out_Retail),
                    "SO_FINAL.xlsx"
                )
# ==============================================================================
# 4. CONSOLIDADOR INVENTARIOS RETAIL (NUEVO)
# ==============================================================================
elif opcion == "Consolidador Inventarios Retail":
    st.title("🏘️ Consolidador de Inventarios Retail")
    file_inv = st.file_uploader("Sube Layout Inventarios Retail.xlsx", type=["xlsx"])

    if file_inv and cat_sku_raw and cat_mod_raw:
        if st.button("🔄 Procesar Existencias Retail"):
            with st.spinner("Consolidando inventarios..."):
                # Cargar hojas del layout
                Coppel    = pd.read_excel(file_inv, sheet_name="Coppel")
                Liverpool = pd.read_excel(file_inv, sheet_name="Liverpool")
                Sears     = pd.read_excel(file_inv, sheet_name="Sears")
                Suburbia  = pd.read_excel(file_inv, sheet_name="Suburbia")
                Mavi      = pd.read_excel(file_inv, sheet_name="Mavi")
                Bodesa    = pd.read_excel(file_inv, sheet_name="Bodesa")
                Clikstore = pd.read_excel(file_inv, sheet_name="Clikstore")
                Cklass    = pd.read_excel(file_inv, sheet_name="Cklass")

                # Cargar catálogos maestros
                CAT_SKU = pd.read_excel(cat_sku_raw, sheet_name="Sku_retail")
                CAT_MOD = pd.read_excel(cat_mod_raw, sheet_name="CAT_MOD_v3")

                # Mapeo de SKU a Item Number
                serie_sku_item = mapeo_seguro(CAT_SKU, 'SKU', 'Item', case='upper')

                # --- PROCESAMIENTO INDIVIDUAL ---
                # Coppel
                Coppel["HO"] = Coppel["Exis Tda"].fillna(0) + Coppel["Exis Bod"].fillna(0)
                Coppel["Cadena"] = "COPPEL"
                Coppel["SKU_UP"] = Coppel["SKU"].astype(str).str.strip().str.upper()
                Coppel["N° ARTICULO"] = Coppel["SKU_UP"].map(serie_sku_item)
                Coppel = Coppel[Coppel["Artículo"] != "REFACCION"]

                # Liverpool
                Liverpool = Liverpool[Liverpool["Centro"] != "Resultado Total"].copy()
                Liverpool["Cadena"] = "Liverpool"
                Liverpool["SKU_UP"] = Liverpool["Artículo"].astype(str).str.strip().str.upper()
                Liverpool["N° ARTICULO"] = Liverpool["SKU_UP"].map(serie_sku_item)

                # Sears
                Sears["Cadena"] = "Sears"
                Sears["SKU_UP"] = Sears["SKU"].astype(str).str.strip().str.upper()
                Sears["N° ARTICULO"] = Sears["SKU_UP"].map(serie_sku_item)

                # Suburbia
                Suburbia["Cadena"] = "Suburbia"
                Suburbia["SKU_UP"] = Suburbia["Material"].astype(str).str.strip().str.upper()
                Suburbia["N° ARTICULO"] = Suburbia["SKU_UP"].map(serie_sku_item)

                # Mavi
                Mavi["Cadena"] = "Mavi"
                Mavi["SKU_UP"] = Mavi["CODIGO"].astype(str).str.strip().str.upper()
                Mavi["N° ARTICULO"] = Mavi["SKU_UP"].map(serie_sku_item)

                # Bodesa
                Bodesa["Cadena"] = "Bodesa"
                Bodesa["SKU_UP"] = Bodesa["Material"].astype(str).str.strip().str.upper()
                Bodesa["N° ARTICULO"] = Bodesa["SKU_UP"].map(serie_sku_item)

                # Clikstore
                Clikstore["Cadena"] = "Clikstore"
                Clikstore["SKU_UP"] = Clikstore["Sku"].astype(str).str.strip().str.upper()
                Clikstore["N° ARTICULO"] = Clikstore["SKU_UP"].map(serie_sku_item)

                # Cklass
                Cklass["Cadena"] = "Cklass"
                Cklass["SKU_UP"] = Cklass["Material"].astype(str).str.strip().str.upper()
                Cklass["N° ARTICULO"] = Cklass["SKU_UP"].map(serie_sku_item)

                # --- CONSOLIDACIÓN ---
                columnas_finales = ["CADENA", "CANAL", "SKU", "N° ARTICULO", "HO"]
                
                Inventario_RC = pd.DataFrame({
                    "CADENA": pd.concat([Coppel['Cadena'], Liverpool['Cadena'], Sears['Cadena'], Suburbia['Cadena'], Mavi['Cadena'], Bodesa['Cadena'], Clikstore['Cadena'], Cklass['Cadena']], ignore_index=True),
                    "CANAL": "RC",
                    "SKU": pd.concat([Coppel['SKU'], Liverpool['Artículo'], Sears['SKU'], Suburbia['Material'], Mavi['CODIGO'], Bodesa['Material'], Clikstore['Sku'], Cklass['Material']], ignore_index=True),
                    "N° ARTICULO": pd.concat([Coppel['N° ARTICULO'], Liverpool['N° ARTICULO'], Sears['N° ARTICULO'], Suburbia['N° ARTICULO'], Mavi['N° ARTICULO'], Bodesa['N° ARTICULO'], Clikstore['N° ARTICULO'], Cklass['N° ARTICULO']], ignore_index=True),
                    "HO": pd.concat([Coppel['HO'], Liverpool['On Hand'], Sears['Total'], Suburbia['Libre utilización'], Mavi['Total'], Bodesa['Inv. piezas'], Clikstore['Total - Cantidad'], Cklass['Libre utilización']], ignore_index=True)
                })

                Inventario_RC = Inventario_RC[Inventario_RC['HO'] > 0].copy()
                Inventario_RC['HO'] = Inventario_RC['HO'].astype('Int64')

                # --- MAPEO DE ATRIBUTOS DESDE CATÁLOGO MODELOS ---
                # Normalizar N° ARTICULO para mapeo
                Inventario_RC['N° ARTICULO'] = Inventario_RC['N° ARTICULO'].astype(str).str.strip().str.upper()
                
                serie_mkt   = mapeo_seguro(CAT_MOD, 'NÚMERO DE ARTÍCULO (SAP)', 'MKT NAME', case='upper')
                serie_anio  = mapeo_seguro(CAT_MOD, 'NÚMERO DE ARTÍCULO (SAP)', 'AÑO', case='upper')
                serie_color = mapeo_seguro(CAT_MOD, 'NÚMERO DE ARTÍCULO (SAP)', 'COLOR', case='upper')

                Inventario_RC['MODELO']     = Inventario_RC['N° ARTICULO'].map(serie_mkt)
                Inventario_RC['AÑO MODELO'] = Inventario_RC['N° ARTICULO'].map(serie_anio).astype('Int64')
                Inventario_RC['COLOR']      = Inventario_RC['N° ARTICULO'].map(serie_color)

                st.success("✅ Consolidación de Inventario RC completada")
                st.dataframe(Inventario_RC.head(20))
                
                st.download_button(
                    "📥 Descargar Inventario Retail", 
                    to_excel(Inventario_RC), 
                    "Inventarios_Retail_Consolidado.xlsx"
                )
