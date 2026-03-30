import streamlit as st
import pandas as pd

st.set_page_config(page_title="Depurador Tarjetas de Trabajo", layout="wide")

st.title("📊 Depurador de Tarjetas de Trabajo")

st.write("Sube tu archivo Excel con las hojas 2024, 2025 y 2026")

# =========================
# FUNCIONES
# =========================

def procesar_hoja(df):
    # Renombrar columnas
    df.columns.values[0] = 'Compañia'
    df.columns.values[1] = 'Sucursal'
    df.columns.values[2] = 'Tipo_Reparacion'

    # Forward fill
    df['Compañia'] = df['Compañia'].ffill()
    df['Sucursal'] = df['Sucursal'].ffill()

    # Eliminar Totales
    df = df[~df['Tipo_Reparacion'].astype(str).str.contains('Total', na=False)]
    df = df[~df['Sucursal'].astype(str).str.contains('Total', na=False)]
    df = df[~df['Compañia'].astype(str).str.contains('Total', na=False)]

    # Limpiar nombres columnas
    df.columns = [str(c).strip() for c in df.columns]

    columnas_fijas = ['Compañia', 'Sucursal', 'Tipo_Reparacion']

    columnas_meses = [
        col for col in df.columns
        if col not in columnas_fijas
        and 'Total' not in str(col)
        and 'Unnamed' not in str(col)
    ]

    # Melt
    df_melt = df.melt(
        id_vars=columnas_fijas,
        value_vars=columnas_meses,
        var_name='Fecha',
        value_name='Cantidad'
    )

    df_melt = df_melt.dropna(subset=['Fecha'])

    return df_melt


@st.cache_data
def procesar_archivo(file):
    df2024 = pd.read_excel(file, sheet_name="2024", skiprows=2)
    df2025 = pd.read_excel(file, sheet_name="2025", skiprows=2)
    df2026 = pd.read_excel(file, sheet_name="2026", skiprows=2)

    t2024 = procesar_hoja(df2024)
    t2025 = procesar_hoja(df2025)
    t2026 = procesar_hoja(df2026)

    df_final = pd.concat([t2024, t2025, t2026], ignore_index=True)

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