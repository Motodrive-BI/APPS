import streamlit as st
import pandas as pd
from io import BytesIO

# Configuración básica de la página
st.set_page_config(page_title="Reporte de Inventarios", layout="centered")

st.title("📦 Reporte Diario de Inventarios")
st.write("Sube tu archivo **Inventory in Warehouse Report (Detailed)** para procesarlo y descargar la versión depurada.")

# 1. Carga de Archivo usando Streamlit
uploaded_file = st.file_uploader(
    "Selecciona el archivo Excel", 
    type=["xlsx", "xls"]
)

if uploaded_file is not None:
    try:
        # Cargar el archivo Excel seleccionado en un DataFrame
        df = pd.read_excel(uploaded_file, header=None)
        st.success("¡Inventario Cargado Correctamente!")
        
        with st.spinner('Procesando datos...'):
            # 2. Agregar columna ALM
            df['ALM'] = None
            df['ALM'] = df['ALM'].astype(object)
            current_alm = None
            
            # Iterar sobre las filas del DataFrame
            for index, row in df.iterrows():
                if pd.notna(row[0]) and 'Whse:' in str(row[0]):
                    current_alm = row[1]
                df.at[index, 'ALM'] = current_alm
            
            # Limpieza de filas "Whse:" y NaN
            df = df[~df[0].astype(str).str.contains('Whse:', na=False)]
            df = df.dropna(subset=[0])
            
            # 3. Asignar fila 1 a nombres de la columna
            df.columns = list(df.iloc[0, :13]) + list(df.columns[13:])
            df = df.drop(0).reset_index(drop=True)
            
            # 4. Extracción de información
            # (Asegúrate de que los nombres de las columnas coincidan exactamente con tu Excel)
            Inventario = df[['Item No.', 'Item Description', 'ALM', 'Inventory UoM', 'In Stock', 'Committed', 'Ordered', 'Available']]
            
            # Mostrar una vista previa en la aplicación
            st.subheader("Vista previa de los datos depurados:")
            st.dataframe(Inventario.head(10))
            
            # 5. Guardar Inventario Depurado en memoria para descarga
            output = BytesIO()
            # Usamos xlsxwriter como motor para asegurar compatibilidad
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                Inventario.to_excel(writer, index=False, sheet_name='Inventario Depurado')
            
            # Obtener el valor de la memoria
            processed_data = output.getvalue()
            
            st.write("---")
            st.subheader("Descargar Reporte")
            
            # Botón de descarga de Streamlit
            st.download_button(
                label="📥 Descargar Inventario Depurado",
                data=processed_data,
                file_name="Reporte_Inventario_Depurado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        # Manejo de errores en caso de que el formato del Excel no sea el esperado
        st.error(f"Ocurrió un error al procesar el archivo. Por favor verifica el formato.")
        st.exception(e)