import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO
import numpy as np

st.set_page_config(page_title="Control de Cotizaciones", layout="wide")

conn = sqlite3.connect("cotizaciones.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS cotizaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisicion TEXT,
    fecha_solicitud TEXT,
    descripcion TEXT,
    planta TEXT,
    usuario TEXT,
    proveedor TEXT,
    fecha_envio TEXT,
    importe REAL,
    estatus TEXT,
    orden_compra TEXT,
    responsable TEXT,
    email_responsable TEXT
)
""")
conn.commit()

def insertar_cotizacion(data):
    cursor.execute("""
        INSERT INTO cotizaciones (
            requisicion, fecha_solicitud, descripcion, planta, usuario,
            proveedor, fecha_envio, importe, estatus, orden_compra,
            responsable, email_responsable
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

def actualizar_cotizacion(id, proveedor, fecha_envio, importe, estatus, orden_compra):
    cursor.execute("""
        UPDATE cotizaciones SET
            proveedor = ?,
            fecha_envio = ?,
            importe = ?,
            estatus = ?,
            orden_compra = ?
        WHERE id = ?
    """, (proveedor, fecha_envio, importe, estatus, orden_compra, id))
    conn.commit()

def exportar_excel(df):
    output = BytesIO()
    fecha_actual = datetime.today().strftime("%Y-%m-%d")
    nombre_archivo = f"reporte_cotizaciones_{fecha_actual}.xlsx"
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Cotizaciones')
    output.seek(0)
    return output, nombre_archivo

def eliminar_cotizacion(id):
    cursor.execute("DELETE FROM cotizaciones WHERE id = ?", (id,))
    conn.commit()

st.title("📋 Control de Cotizaciones")

menu = ["Capturar PR", "Operación", "Seguimiento", "Cotizaciones Completadas"]
opcion = st.sidebar.selectbox("Menú", menu)

if opcion == "Capturar PR":
    st.header("📝 Nueva Solicitud de Cotización (PR)")

    responsables = {
        "Vicente Ledezma": "v-ledezma@axisarquitectura.com",
        "Rebeca Gonzalez": "r-gonzalez@axisarquitectura.com",
        "Esteban Mendez": "e-mendez@axisarqutiectura.com"
    }

    with st.form("form_pr", clear_on_submit=True):
        requisicion = st.text_input("No. de Requisición")
        fecha_solicitud = st.date_input("Fecha de Solicitud", value=datetime.today())
        descripcion = st.text_area("Descripción")
        planta = st.text_input("Planta")
        usuario = st.text_input("Usuario")
        responsable = st.selectbox("Responsable de Cotización", list(responsables.keys()))
        email_responsable = responsables[responsable]

        submitted = st.form_submit_button("Guardar PR")
        if submitted:
            data = (
                requisicion, str(fecha_solicitud), descripcion, planta,
                usuario, "", "", 0.0, "Abierta", "",
                responsable, email_responsable
            )
            insertar_cotizacion(data)
            st.success("✅ PR registrada correctamente")

elif opcion == "Operación":
    st.header("🧾 Cotizaciones Pendientes")
    df = pd.read_sql_query("SELECT * FROM cotizaciones", conn)

    if not df.empty:
        df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'], errors='coerce')
        df['fecha_envio'] = pd.to_datetime(df['fecha_envio'], errors='coerce')
        hoy = pd.to_datetime(datetime.today().date())
        df['dias_respuesta'] = (df['fecha_envio'] - df['fecha_solicitud']).dt.days
        df['dias_sin_respuesta'] = np.where(df['fecha_envio'].isna(), (hoy - df['fecha_solicitud']).dt.days, None)
        df['alerta'] = np.where((df['fecha_envio'].isna()) & ((hoy - df['fecha_solicitud']).dt.days > 5), "⚠️ +5 días", "")
        df['orden_compra_generada'] = df['orden_compra'].apply(lambda x: "Sí" if x else "No")

        pendientes = df[df['proveedor'] == ""]
        if not pendientes.empty:
            seleccion = st.selectbox("Selecciona una PR para completar:", pendientes['id'].astype(str) + " - " + pendientes['requisicion'])

            if seleccion:
                id_sel = int(seleccion.split(" - ")[0])
                row = pendientes[pendientes['id'] == id_sel].iloc[0]

                st.subheader("📦 Completar Cotización")
                with st.form("form_completar"):
                    proveedor = st.text_input("Proveedor", value=row['proveedor'])
                    fecha_envio = st.date_input("Fecha de Envío de Cotización")
                    importe = st.number_input("Importe Cotización", min_value=0.0, step=0.01)
                    estatus = st.selectbox("Estatus", ["En Proceso", "Cotizada", "Cerrada", "Orden de Compra generada"], index=0)
                    orden_compra = st.text_input("No. Orden de Compra")

                    actualizar = st.form_submit_button("Actualizar Cotización")
                    if actualizar:
                        actualizar_cotizacion(
                            id_sel, proveedor, str(fecha_envio), importe, estatus, orden_compra
                        )
                        st.success("✅ Cotización actualizada")

        st.subheader("📊 Todas las Cotizaciones")
        st.dataframe(df, use_container_width=True)

        with st.expander("🗑️ Eliminar registro"):
            id_borrar = st.number_input("ID del registro a eliminar", min_value=1, step=1)
            if st.button("Eliminar Registro"):
                eliminar_cotizacion(id_borrar)
                st.warning(f"Registro con ID {id_borrar} eliminado.")

        excel_data, nombre_archivo = exportar_excel(df)
        st.download_button(
            label="📥 Descargar Excel",
            data=excel_data,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay registros disponibles.")

elif opcion == "Seguimiento":
    st.header("⏱️ Seguimiento de Cotizaciones")
    df = pd.read_sql_query("SELECT * FROM cotizaciones", conn)

    if not df.empty:
        df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'], errors='coerce')
        hoy = pd.to_datetime(datetime.today().date())
        df['dias_transcurridos'] = (hoy - df['fecha_solicitud']).dt.days

        resumen = df[['requisicion', 'descripcion', 'fecha_solicitud', 'dias_transcurridos', 'planta', 'usuario']]

        plantas = resumen['planta'].dropna().unique().tolist()
        usuarios = resumen['usuario'].dropna().unique().tolist()

        col1, col2 = st.columns(2)
        with col1:
            planta_sel = st.selectbox("Filtrar por Planta", ["Todas"] + plantas)
        with col2:
            usuario_sel = st.selectbox("Filtrar por Usuario", ["Todos"] + usuarios)

        if planta_sel != "Todas":
            resumen = resumen[resumen['planta'] == planta_sel]
        if usuario_sel != "Todos":
            resumen = resumen[resumen['usuario'] == usuario_sel]

        def destacar_fila(row):
            color = 'background-color: #ffcccc' if row['dias_transcurridos'] > 5 else ''
            return [color] * len(row)

        st.dataframe(resumen.style.apply(destacar_fila, axis=1), use_container_width=True)
    else:
        st.info("No hay registros para mostrar.")

elif opcion == "Cotizaciones Completadas":
    st.header("✅ Cotizaciones Completadas")
    df = pd.read_sql_query("SELECT * FROM cotizaciones WHERE proveedor != ''", conn)

    if not df.empty:
        df['fecha_solicitud'] = pd.to_datetime(df['fecha_solicitud'], errors='coerce')
        df['fecha_envio'] = pd.to_datetime(df['fecha_envio'], errors='coerce')
        df['dias_respuesta'] = (df['fecha_envio'] - df['fecha_solicitud']).dt.days
        df['orden_compra_generada'] = df['orden_compra'].apply(lambda x: "Sí" if x else "No")

        st.subheader("📋 Resumen por PR")
        resumen = df[['requisicion', 'fecha_solicitud']].copy()
        hoy = pd.to_datetime(datetime.today().date())
        resumen['dias_transcurridos'] = (hoy - resumen['fecha_solicitud']).dt.days

        def destacar_fila(row):
            color = 'background-color: #ffcccc' if row['dias_transcurridos'] > 5 else ''
            return [color] * len(row)

        st.dataframe(resumen.style.apply(destacar_fila, axis=1))

        st.subheader("📊 Detalle de Cotizaciones")
        st.dataframe(df, use_container_width=True)

        excel_data, nombre_archivo = exportar_excel(df)
        st.download_button(
            label="📥 Descargar Excel",
            data=excel_data,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay cotizaciones completadas aún.")



