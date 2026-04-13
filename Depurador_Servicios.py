import streamlit as st
import pandas as pd

st.set_page_config(page_title="Depurador Tarjetas de Trabajo", layout="wide")

st.title("📊 Depurador de Tarjetas de Trabajo")

st.write("Sube tu archivo Excel con las hojas 2024, 2025 y 2026")

# =========================
# FUNCIONES
# =========================

def procesar_hoja(df):
    if df.empty:
        return df
        
    # Extraemos las columnas a una lista para modificarlas de forma segura
    columnas = list(df.columns)
    
    # Validamos que existan suficientes columnas antes de asignar
    if len(columnas) >= 3:
        columnas[0] = 'Compañia'
        columnas[1] = 'Sucursal'
        columnas[2] = 'Tipo_Reparacion'
        # Aplicamos la lista modificada de vuelta al DataFrame
        df.columns = columnas
    else:
        # Si el DataFrame no tiene la estructura esperada, devolvemos el original o manejamos el error
        return df

    # Forward fill para completar datos hacia abajo
    df['Compañia'] = df['Compañia'].ffill()
    df['Sucursal'] = df['Sucursal'].ffill()

    # Eliminar filas que contengan 'Total' en las columnas clave
    df = df[~df['Tipo_Reparacion'].astype(str).str.contains('Total', na=False)]
    df = df[~df['Sucursal'].astype(str).str.contains('Total', na=False)]
    df = df[~df['Compañia'].astype(str).str.contains('Total', na=False)]

    # Limpiar espacios en blanco en los nombres de las columnas
    df.columns = [str(c).strip() for c in df.columns]

    columnas_fijas = ['Compañia', 'Sucursal', 'Tipo_Reparacion']

    # Identificar columnas de meses (excluyendo fijas, totales y errores de lectura)
    columnas_meses = [
        col for col in df.columns
        if col not in columnas_fijas
        and 'Total' not in str(col)
        and 'Unnamed' not in str(col)
    ]

    # Transformación de ancho a largo (Melt)
    df_melt = df.melt(
        id_vars=columnas_fijas,
        value_vars=columnas_meses,
        var_name='Fecha',
        value_name='Cantidad'
    )

    # Limpiar registros sin fecha
    df_melt = df_melt.dropna(subset=['Fecha'])

    return df_melt

@st.cache_data
def procesar_archivo(file):
    # Lectura de las pestañas correspondientes
    df2024 = pd.read_excel(file, sheet_name="2024", skiprows=2)
    df2025 = pd.read_excel(file, sheet_name="2025", skiprows=2)
    df2026 = pd.read_excel(file, sheet_name="2026", skiprows=2)

    # Procesamiento individual de cada año
    t2024 = procesar_hoja(df2024)
    t2025 = procesar_hoja(df2025)
    t2026 = procesar_hoja(df2026)

    # Concatenación de resultados
    df_final = pd.concat([t2024, t2025, t2026], ignore_index=True)

    # Conversión de la columna Fecha a formato datetime
    df_final['Fecha'] = pd.to_datetime(df_final['Fecha'])

    return df_final

# =========================
# UI
# =========================

uploaded_file = st.file_uploader(
    "📂 Sube tu archivo Excel",
    type=["xlsx"]
)

if uploaded_file is not None:

    if st.button("⚙️ Procesar archivo"):
        with st.spinner("Procesando..."):
            df_final = procesar_archivo(uploaded_file)

        st.success("✅ Archivo procesado correctamente")

        # Vista previa
        st.subheader("🔍 Vista previa")
        st.dataframe(df_final.head(50), use_container_width=True)

        # Métricas rápidas
        col1, col2, col3 = st.columns(3)

        col1.metric("Registros", len(df_final))
        col2.metric("Compañías", df_final['Compañia'].nunique())
        col3.metric("Sucursales", df_final['Sucursal'].nunique())

        # =========================
        # DESCARGA
        # =========================
        import io

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, sheet_name='Datos', index=False)

            worksheet = writer.sheets['Datos']

            for i, col in enumerate(df_final.columns):
                column_len = max(
                    df_final[col].astype(str).str.len().max(),
                    len(col)
                ) + 2

                worksheet.set_column(i, i, column_len)

        st.download_button(
            label="📥 Descargar archivo procesado",
            data=output.getvalue(),
            file_name="Acumulado_Targetas_Trabajo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
