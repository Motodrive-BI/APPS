import streamlit as st
import pandas as pd
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Herramientas de Inventario & Sell Out", layout="wide")

# --- BARRA LATERAL (MENÚ) ---
st.sidebar.title("📊 Panel de Control")
opcion = st.sidebar.selectbox(
    "Selecciona el reporte a procesar:",
    ["Reporte Diario de Inventarios", "Reporte de Sell Out Global"]
)

st.sidebar.markdown("---")
st.sidebar.info("Sube el archivo Excel descargado de SAP para comenzar la depuración.")

# --- FUNCIÓN PARA DESCARGA ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Depurado')
    return output.getvalue()

# --- LÓGICA DE LA APLICACIÓN ---

if opcion == "Reporte Diario de Inventarios":
    st.title("📦 Depurador: Inventory in Warehouse")
    archivo = st.file_uploader("Cargar Reporte de Inventario (Excel)", type=["xlsx", "xls"])

    if archivo:
        df = pd.read_excel(archivo, header=None)
        
        # Procesamiento
        df['ALM'] = None
        df['ALM'] = df['ALM'].astype(object)
        current_alm = None
        
        for index, row in df.iterrows():
            if pd.notna(row[0]) and 'Whse:' in str(row[0]):
                current_alm = row[1]
            df.at[index, 'ALM'] = current_alm
        
        df = df[~df[0].astype(str).str.contains('Whse:', na=False)]
        df = df.dropna(subset=[0])
        df.columns = list(df.iloc[0, :13]) + list(df.columns[13:])
        df = df.drop(0).reset_index(drop=True)
        
        # Extracción
        columnas_inv = ['Item No.', 'Item Description', 'ALM', 'Inventory UoM', 'In Stock', 'Committed', 'Ordered', 'Available']
        inventario_final = df[columnas_inv]
        
        st.success("✅ Inventario procesado con éxito")
        st.dataframe(inventario_final.head(10))
        
        st.download_button(
            label="📥 Descargar Inventario Depurado",
            data=to_excel(inventario_final),
            file_name="Inventario_Depurado.xlsx"
        )

elif opcion == "Reporte de Sell Out Global":
    st.title("🚀 Depurador: Sell Out Global")
    archivo = st.file_uploader("Cargar Reporte de Sell Out (Excel)", type=["xlsx", "xls"])

    if archivo:
        so_global = pd.read_excel(archivo)
        
        # 1. Corrección de tipos de datos
        with st.expander("Ver detalles de limpieza"):
            st.write("Cambiando tipos de datos...")
            so_global['Código Postal'] = so_global['Código Postal'].astype(str)
            so_global['Teléfono'] = so_global['Teléfono'].astype(str)
            so_global['Fecha de fabricación'] = pd.to_datetime(so_global['Fecha de fabricación'], errors='coerce')
            so_global['Zona'] = so_global['Zona'].astype(str)
            
            # 2. Análisis de duplicados y nulos
            dups = so_global.duplicated().sum()
            nulos = so_global.isnull().sum().sum()
            st.warning(f"Se encontraron {dups} filas duplicadas y {nulos} valores nulos en total.")

        # 3. Extracción de columnas específicas
        columnas_so = [
            'Fecha del documento', 'Vendedor', 'Familia del modelo', 'Familia de submodelos',
            'Nombre del Modelo', 'Color', 'Item', 'No Serie / VIN', 'Gerente Regional',
            'Codigo de Compañía', 'Compañía', 'Código de sucursal', 'Sucursal', 'Campaña',
            'Financiera', 'Tipo Operacion MotoDrive ', 'Proveedor de seguros', 'Género',
            'Estatus', 'Status', 'Nombre del Canal', 'Fuente', 'Cantidad', 'Precio',
            'Descuento', 'Monto del descuento', 'Precio total de venta sin IVA', 'Precio total de venta con IVA'
        ]
        
        # Filtrar solo si las columnas existen
        so_global_dep = so_global[columnas_so]
        
        st.success("✅ Sell Out procesado y corregido")
        st.dataframe(so_global_dep.head(10))
        
        st.download_button(
            label="📥 Descargar Sell Out Depurado",
            data=to_excel(so_global_dep),
            file_name="Sell_Out_Global_Depurado.xlsx"
        )
