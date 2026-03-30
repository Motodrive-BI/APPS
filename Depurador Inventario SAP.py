import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="MotoDrive: Herramientas de Datos", layout="wide")

# --- BARRA LATERAL ---
st.sidebar.title("🛠️ Herramientas MotoDrive")
opcion = st.sidebar.selectbox(
    "Selecciona el proceso:",
    ["Inventario Diario", "Sell Out Global (SAP)", "Consolidador Sell Out Retail"]
)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- MODULO 1: INVENTARIO (Tu primer código) ---
if opcion == "Inventario Diario":
    st.title("📦 Depurador de Inventario")
    # ... (Mismo código anterior)

# --- MODULO 2: SELL OUT GLOBAL (Tu segundo código) ---
elif opcion == "Sell Out Global (SAP)":
    st.title("🚀 Depurador de Sell Out Global")
    # ... (Mismo código anterior)

# --- MODULO 3: CONSOLIDADOR RETAIL (EL NUEVO SCRIPT) ---
elif opcion == "Consolidador Sell Out Retail":
    st.title("🔗 Consolidador Sell Out Retail")
    st.info("Este proceso requiere el Layout Master y los 3 Catálogos (SKU, Modelos y Sucursales).")

    col1, col2 = st.columns(2)
    with col1:
        file_master = st.file_uploader("1. Sube Layout Retail Master.xlsx", type=["xlsx"])
        file_sku = st.file_uploader("2. Sube Catalogo_SKU_v3.xlsx", type=["xlsx"])
    with col2:
        file_modelos = st.file_uploader("3. Sube Catalogo_Modelos.xlsx", type=["xlsx"])
        file_sucursales = st.file_uploader("4. Sube Concentrado_Master (Sucursales).xlsx", type=["xlsx"])

    if all([file_master, file_sku, file_modelos, file_sucursales]):
        if st.button("🚀 Iniciar Consolidación"):
            with st.spinner("Procesando todas las cadenas y catálogos..."):
                try:
                    # Carga de Layouts (Hojas)
                    Coppel = pd.read_excel(file_master, sheet_name="Coppel")
                    Liverpool = pd.read_excel(file_master, sheet_name="Liverpool")
                    Sears = pd.read_excel(file_master, sheet_name="Sears")
                    Suburbia = pd.read_excel(file_master, sheet_name="Suburbia")
                    Mavi = pd.read_excel(file_master, sheet_name="Mavi")
                    Bodesa = pd.read_excel(file_master, sheet_name="Bodesa")
                    Clikstore = pd.read_excel(file_master, sheet_name="Clik")
                    Cklass = pd.read_excel(file_master, sheet_name="Cklass")
                    Ecomm = pd.read_excel(file_master, sheet_name="Ecomm")

                    # Carga de Catálogos
                    CAT_SKU = pd.read_excel(file_sku, sheet_name="Sku_retail")
                    CATALOGO_MODELO = pd.read_excel(file_modelos, sheet_name='CAT_MOD_v3')
                    CATALOGO_SUCURSALES = pd.read_excel(file_sucursales, sheet_name="Sucursales RC")

                    # --- LÓGICA DE NORMALIZACIÓN (Resumen de tu script) ---
                    CAT_SKU['SKU'] = CAT_SKU['SKU'].astype(str).str.strip().str.upper()
                    mapeo_items = CAT_SKU.drop_duplicates(subset=['SKU'], keep='first')
                    mapeo_series_sku = mapeo_items.set_index('SKU')['Item']

                    # Ejemplo de procesamiento Coppel
                    Coppel['Cadena'] = "COPPEL"
                    Coppel['Código'] = Coppel['Código'].astype(str).str.strip().str.upper()
                    Coppel['Item Number'] = Coppel['Código'].map(mapeo_series_sku)
                    
                    # Normalización Sucursales
                    CATALOGO_SUCURSALES['IDRETAIL'] = CATALOGO_SUCURSALES['ID Sucursal'].astype(str).str.strip() + CATALOGO_SUCURSALES['Cadena'].astype(str).str.strip()
                    mapeo_suc = CATALOGO_SUCURSALES.drop_duplicates(subset=['IDRETAIL'], keep='first').set_index('IDRETAIL')
                    
                    Coppel['Id Retail'] = Coppel['Tienda'].astype(str) + "COPPEL"
                    Coppel['SUCURSAL'] = Coppel['Id Retail'].map(mapeo_suc['Sucursal'])
                    
                    # ... [Aquí se ejecutaría el resto de tu lógica de concatenación] ...
                    # Para fines de brevedad, simulamos el concat final:
                    
                    column_names = ["CANAL", "SELL", "FECHA", "SKU", "QTY", "N° ARTICULO", "STORE", "ID RETAIL", "MODELO", "COLOR"]
                    Sell_Out_Retail = pd.DataFrame(columns=column_names)
                    
                    # Simulación de carga (rellena con tu lógica de pd.concat)
                    Sell_Out_Retail['CANAL'] = pd.concat([Coppel['Cadena'], Liverpool['Canal'], Sears['Canal']])
                    # (Completa con todas tus columnas según tu script original)

                    st.success("✅ Consolidación completada")
                    st.dataframe(Sell_Out_Retail.head(10))

                    st.download_button(
                        label="📥 Descargar Consolidado Final",
                        data=to_excel(Sell_Out_Retail),
                        file_name="SO_RETAIL_CONSOLIDADO.xlsx"
                    )
                except Exception as e:
                    st.error(f"Error en los archivos: {e}")
