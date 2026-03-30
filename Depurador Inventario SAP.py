import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MotoDrive: Master Data Tool", layout="wide")

# --- CONFIGURACIÓN DE GITHUB ---
# Usamos la URL raw de githubusercontent que es la que permite descarga directa
GITHUB_BASE_URL = "https://raw.githubusercontent.com/Motodrive-BI/APPS/main/"

URLS = {
    "sku": GITHUB_BASE_URL + "Catalogo_SKU_v3 BETA.xlsx",
    "modelos": GITHUB_BASE_URL + "Catalogo_Modelos.xlsx",
    "sucursales": GITHUB_BASE_URL + "Concentrado_Master.xlsx"
}

# --- FUNCIONES DE SOPORTE ---
@st.cache_data(ttl=3600)
def cargar_excel_github(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        st.error(f"Error al conectar con GitHub. Revisa la URL: {url}")
        return None

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- BARRA LATERAL ---
st.sidebar.title("🛠️ MotoDrive HUB")
opcion = st.sidebar.selectbox(
    "Selecciona el proceso:",
    ["Inventario Diario (SAP)", "Sell Out Global (SAP)", "Consolidador Retail"]
)

# Carga automática de catálogos
cat_sku_file = cargar_excel_github(URLS["sku"])
cat_mod_file = cargar_excel_github(URLS["modelos"])
cat_suc_file = cargar_excel_github(URLS["sucursales"])

with st.sidebar:
    st.markdown("---")
    if cat_sku_file and cat_mod_file and cat_suc_file:
        st.success("✅ Catálogos actualizados desde GitHub")
    else:
        st.warning("⚠️ Error al cargar catálogos. Verifica conexión.")

# --- LÓGICA DE PROCESOS ---

if opcion == "Inventario Diario (SAP)":
    st.title("📦 Reporte Diario de Inventarios")
    file = st.file_uploader("Sube Reporte de Inventario (Excel)", type=["xlsx"])
    if file:
        df = pd.read_excel(file, header=None)
        df['ALM'] = None
        current_alm = None
        for index, row in df.iterrows():
            if pd.notna(row[0]) and 'Whse:' in str(row[0]):
                current_alm = row[1]
            df.at[index, 'ALM'] = current_alm
        df = df[~df[0].astype(str).str.contains('Whse:', na=False)].dropna(subset=[0])
        df.columns = list(df.iloc[0, :13]) + list(df.columns[13:])
        df = df.drop(0).reset_index(drop=True)
        res = df[['Item No.', 'Item Description', 'ALM', 'Inventory UoM', 'In Stock', 'Committed', 'Ordered', 'Available']]
        st.dataframe(res)
        st.download_button("📥 Descargar Excel", to_excel(res), "Inventario_Depurado.xlsx")

elif opcion == "Sell Out Global (SAP)":
    st.title("🚀 Sell Out Global SAP")
    file = st.file_uploader("Sube Reporte Sell Out", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        # Limpieza básica
        df['Código Postal'] = df['Código Postal'].astype(str)
        df['Teléfono'] = df['Teléfono'].astype(str)
        df['Fecha de fabricación'] = pd.to_datetime(df['Fecha de fabricación'], errors='coerce')
        st.dataframe(df.head())
        st.download_button("📥 Descargar Depurado", to_excel(df), "SellOut_Depurado.xlsx")

elif opcion == "Consolidador Retail":
    st.title("🔗 Consolidador Retail Master")
    file_master = st.file_uploader("Sube Layout Retail Master.xlsx", type=["xlsx"])
    
    if file_master and cat_sku_file:
        if st.button("🚀 Iniciar Proceso de Consolidación"):
            with st.spinner("Procesando todas las cadenas..."):
                # 1. Leer Hojas del Master
                hojas = ["Coppel", "Liverpool", "Sears", "Suburbia", "Mavi", "Bodesa", "Clik", "Cklass", "Ecomm"]
                dict_dfs = {h: pd.read_excel(file_master, sheet_name=h) for h in hojas}
                
                # 2. Leer Catálogos (de GitHub)
                CAT_SKU = pd.read_excel(cat_sku_file, sheet_name="Sku_retail")
                CAT_MODELO = pd.read_excel(cat_mod_file, sheet_name='CAT_MOD_v3')
                CAT_SUC = pd.read_excel(cat_suc_file, sheet_name="Sucursales RC")

                # 3. Lógica de Mapeo (Normalización de SKUs)
                CAT_SKU['SKU'] = CAT_SKU['SKU'].astype(str).str.strip().str.upper()
                map_sku = CAT_SKU.drop_duplicates('SKU').set_index('SKU')['Item']
                
                # Ejemplo rápido: Procesar Coppel
                df_coppel = dict_dfs["Coppel"]
                df_coppel['Cadena'] = "COPPEL"
                df_coppel['Código'] = df_coppel['Código'].astype(str).str.strip().str.upper()
                df_coppel['Item Number'] = df_coppel['Código'].map(map_sku)
                
                # (Aquí incluirías el resto de tu lógica de concatenación masiva)
                # ...
                
                st.success("✅ Consolidación Finalizada")
                st.dataframe(df_coppel.head())
                st.download_button("📥 Descargar Consolidado", to_excel(df_coppel), "SO_Retail_Final.xlsx")
