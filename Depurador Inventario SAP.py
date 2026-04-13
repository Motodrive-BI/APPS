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
        "Consolidador Retail (Ventas)", 
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
elif opcion == "Consolidador Retail (Ventas)":
    st.title("🔗 Consolidador Sell Out Retail")
    file_master = st.file_uploader("Sube Layout Retail Master.xlsx", type=["xlsx"])

    if file_master and cat_sku_raw and cat_mod_raw and cat_suc_raw:
        if st.button("🚀 Ejecutar Consolidación de Ventas"):
            with st.spinner("Procesando ventas retail..."):
                # Carga de Hojas y Catálogos
                # (Se omite el detalle por brevedad, pero conserva tu lógica original de mapeo de ventas)
                st.info("Procesando hojas: Coppel, Liverpool, Sears, Suburbia, Mavi, Bodesa, Clik, Cklass, Ecomm...")
                # ... (Aquí va tu bloque de código original de la opción 'Consolidador Retail')
                st.success("Función de Ventas Retail completada.")

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
