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

    st.title("🔗 Consolidador Retail COMPLETO")

    archivo = st.file_uploader("Sube Layout Retail Master", type=["xlsx"])

    if archivo and cat_sku_raw and cat_mod_raw and cat_suc_raw:

        if st.button("Procesar"):

            # =========================
            # FUNCIONES
            # =========================
            def limpiar(df):
                df.columns = df.columns.str.strip()
                return df

            def norm(x):
                return x.astype(str).str.strip().str.upper()

            # =========================
            # CARGA
            # =========================
            hojas = ["Coppel","Liverpool","Sears","Suburbia","Mavi","Bodesa","Clik","Cklass","Ecomm"]
            dfs = {h: limpiar(pd.read_excel(archivo, sheet_name=h)) for h in hojas}

            CAT_SKU = limpiar(pd.read_excel(cat_sku_raw, sheet_name="Sku_retail"))
            CAT_MOD = limpiar(pd.read_excel(cat_mod_raw, sheet_name="CAT_MOD_v3"))
            SUC = limpiar(pd.read_excel(cat_suc_raw, sheet_name="Sucursales RC"))

            # =========================
            # MAPAS BASE
            # =========================
            CAT_SKU['SKU'] = norm(CAT_SKU['SKU'])
            map_item = CAT_SKU.drop_duplicates('SKU').set_index('SKU')['Item']

            SUC['IDRETAIL'] = norm(SUC['ID Sucursal']) + norm(SUC['Cadena'])
            map_suc = SUC.drop_duplicates('IDRETAIL').set_index('IDRETAIL')

            # =========================
            # FUNCION GENERAL
            # =========================
            def procesar(df, sku_col, id_col, fecha_col, qty_col, canal, transformar_qty=None):

                df['CANAL'] = canal
                df[sku_col] = norm(df[sku_col])
                df['SKU'] = df[sku_col]
                df['N° ARTICULO'] = df['SKU'].map(map_item)

                df['ID'] = norm(df[id_col])
                df['ID RETAIL'] = df['ID'] + canal
                df['STORE'] = df['ID RETAIL'].map(map_suc['Sucursal'])

                df['FECHA'] = pd.to_datetime(df[fecha_col], errors='coerce')

                # 🔥 FIX CANTIDAD
                if transformar_qty:
                    df['QTY'] = transformar_qty(df)
                else:
                    df['QTY'] = pd.to_numeric(df[qty_col], errors='coerce')

                return df[['CANAL','FECHA','SKU','QTY','N° ARTICULO','ID','STORE','ID RETAIL']]

            # =========================
            # COPPEL (ESPECIAL)
            # =========================
            def qty_coppel(df):
                mapa = {
                    'VENTA': 1,
                    'CANCELADA': 0,
                    'ACTIVADA': 1,
                    'EN TIENDA': 1
                }
                return df['Estatus'].astype(str).str.upper().map(mapa)

            Coppel = procesar(
                dfs["Coppel"],
                "Código",
                "Tienda",
                "Fecha Venta",
                None,
                "COPPEL",
                transformar_qty=qty_coppel
            )

            # =========================
            # RESTO CADENAS
            # =========================
            Liverpool = procesar(dfs["Liverpool"], "Artículo", "Centro", "Día/Periodo", "Ventas Unidades", "LIVERPOOL")
            Sears = procesar(dfs["Sears"], "SKU", "TDA", "FECHA", "CANT", "SEARS")
            Suburbia = procesar(dfs["Suburbia"], "SKU", "CENTRO", "Día", "VENTA UNIDADES", "SUBURBIA")
            Mavi = procesar(dfs["Mavi"], "CODIGO", "TIENDA", "FECHA FACT", "CANT.", "MAVI")
            Bodesa = procesar(dfs["Bodesa"], "Materia", "Centro", "Fecha Vta", "Vta pzas", "BODESA")
            Clik = procesar(dfs["Clik"], "SAP", "ID SUC", "FECHA", "Cantidad", "CLIKSTORE")
            Cklass = procesar(dfs["Cklass"], "Material", "ID", "Fecha", "Cantidad", "CKLASS")

            # =========================
            # ECOMMERCE (ESPECIAL)
            # =========================
            E = dfs["Ecomm"]

            E['CANAL'] = "ECOMMERCE"
            E['Unido'] = norm(E['Unido'])
            E['SKU'] = E['Unido']
            E['N° ARTICULO'] = E['SKU'].map(map_item)

            E['FECHA'] = pd.to_datetime(E['Fecha'], errors='coerce')
            E['QTY'] = pd.to_numeric(E['Cant'], errors='coerce')

            E['ID'] = "1"
            E['STORE'] = "ECOMMERCE"
            E['ID RETAIL'] = "ECOMMERCE"

            E = E[['CANAL','FECHA','SKU','QTY','N° ARTICULO','ID','STORE','ID RETAIL']]

            # =========================
            # CONSOLIDADO
            # =========================
            df = pd.concat([
                Coppel, Liverpool, Sears, Suburbia,
                Mavi, Bodesa, Clik, Cklass, E
            ], ignore_index=True)

            # =========================
            # COLUMNAS EXTRA
            # =========================
            df['SELL'] = "SO"
            df['TIPO'] = ""
            df['COD TIPO'] = ""
            df['DESCRIPCION'] = "RE"
            df['MONTO'] = ""

            # =========================
            # FECHAS
            # =========================
            df['MES'] = df['FECHA'].dt.month_name()
            df['AÑO'] = df['FECHA'].dt.year.astype("Int64")
            df['MES - AÑO'] = df['MES'] + " " + df['AÑO'].astype(str)

            # =========================
            # MODELOS
            # =========================
            CAT_MOD['NÚMERO DE ARTÍCULO (SAP)'] = norm(CAT_MOD['NÚMERO DE ARTÍCULO (SAP)'])

            map_mod = CAT_MOD.drop_duplicates('NÚMERO DE ARTÍCULO (SAP)').set_index('NÚMERO DE ARTÍCULO (SAP)')

            df['N° ARTICULO'] = norm(df['N° ARTICULO'])

            df['CC'] = df['N° ARTICULO'].map(
                (map_mod['CILINDRADA'].fillna(0).astype(int).astype(str) + "CC")
            )

            df['MODELO'] = df['N° ARTICULO'].map(map_mod['MKT NAME'])
            df['AÑO MODELO'] = df['N° ARTICULO'].map(map_mod['AÑO']).astype("Int64")
            df['COLOR'] = df['N° ARTICULO'].map(map_mod['COLOR'])
            df['MOD COLOR'] = df['MODELO'] + " " + df['COLOR']

            # =========================
            # GEOGRAFÍA
            # =========================
            df['STATE'] = df['ID RETAIL'].map(map_suc['Estado'])
            df['CITY'] = df['ID RETAIL'].map(map_suc['Municipio'])

            # =========================
            # ID STORE
            # =========================
            df['ID STORE'] = df['ID'].astype(str) + "-" + df['STORE'].astype(str)

            # =========================
            # ORDEN FINAL (TU ESTRUCTURA)
            # =========================
            columnas_finales = [
                "CANAL","SELL","FECHA","COD TIPO","TIPO","SKU","DESCRIPCION",
                "QTY","MONTO","N° ARTICULO","CC","ID","STORE",
                "MES","MES - AÑO","AÑO","MODELO","AÑO MODELO","COLOR",
                "MOD COLOR","ID RETAIL","STATE","CITY","ID STORE"
            ]

            df = df[columnas_finales]

            st.success("✅ CONSOLIDADOR COMPLETO FUNCIONANDO")
            st.dataframe(df.head(20))

            st.download_button(
                "📥 Descargar Consolidado",
                to_excel(df),
                "SO_RETAIL_FINAL.xlsx"
            )
