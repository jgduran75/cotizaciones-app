import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date
from io import BytesIO
import numpy as np
import os

st.set_page_config(page_title="Control de Cotizaciones", layout="wide")

def main():
    # --- Lista de correos autorizados ---
    usuarios_autorizados = {
        "v-ledezma@axisarquitectura.com": "Vicente Ledezma",
        "r-gonzalez@axisarquitectura.com": "Rebeca Gonzalez",
        "e-mendez@axisarquitectura.com": "Esteban Mendez",
        "jgd@gmail.com": "Juan Gabino Duran"
    }

    if "correo" not in st.session_state:
        st.session_state["correo"] = ""

    correo_ingresado = st.text_input("Ingresa tu correo corporativo", value=st.session_state["correo"])
    login = st.button("Iniciar sesión")

    if login:
        st.session_state["correo"] = correo_ingresado

    if "correo" not in st.session_state or st.session_state["correo"] not in usuarios_autorizados:
        st.warning("⚠️ Ingresa un correo autorizado y haz clic en 'Iniciar sesión'.")
        st.stop()

    nombre_usuario = usuarios_autorizados[st.session_state["correo"]]
    st.success(f"Bienvenido, {nombre_usuario} 👋")

    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url or raw_url.startswith("${"):
        st.error("❌ La variable DATABASE_URL no está configurada correctamente.")
        st.stop()

    engine = create_engine(raw_url)

    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cotizaciones (
            id SERIAL PRIMARY KEY,
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
        """))

    def insertar_cotizacion(data):
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO cotizaciones (
                    requisicion, fecha_solicitud, descripcion, planta, usuario,
                    proveedor, fecha_envio, importe, estatus, orden_compra, responsable, email_responsable
                ) VALUES (:requisicion, :fecha_solicitud, :descripcion, :planta, :usuario, :proveedor, :fecha_envio,
                          :importe, :estatus, :orden_compra, :responsable, :email_responsable)
            """), data)

    def actualizar_cotizacion(id, proveedor, fecha_envio, importe, estatus, orden_compra):
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE cotizaciones SET
                    proveedor = :proveedor,
                    fecha_envio = :fecha_envio,
                    importe = :importe,
                    estatus = :estatus,
                    orden_compra = :orden_compra
                WHERE id = :id
            """), {
                "id": int(id),
                "proveedor": proveedor,
                "fecha_envio": fecha_envio,
                "importe": importe,
                "estatus": estatus,
                "orden_compra": orden_compra
            })

    def exportar_excel(df):
        output = BytesIO()
        fecha_actual = datetime.today().strftime("%Y-%m-%d")
        nombre_archivo = f"reporte_cotizaciones_{fecha_actual}.xlsx"
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Cotizaciones')
        output.seek(0)
        return output, nombre_archivo

    def eliminar_cotizacion(id):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM cotizaciones WHERE id = :id"), {"id": int(id)})

    def obtener_cotizaciones():
        with engine.begin() as conn:
            return pd.read_sql("SELECT * FROM cotizaciones", conn)

    st.title("📋 Control de Cotizaciones")

    correo_usuario = st.session_state["correo"]
    menu_completo = ["Capturar PR", "Operación", "Seguimiento", "Cotizaciones Completadas"]
    menu_colaborador = ["Operación", "Seguimiento", "Cotizaciones Completadas"]
    menu = menu_completo if correo_usuario == "jgd@gmail.com" else menu_colaborador
    opcion = st.selectbox("Menú", menu)

    if opcion == "Capturar PR":
        st.header("📝 Nueva Solicitud de Cotización (PR)")

        responsables = {
            "Vicente Ledezma": "v-ledezma@axisarquitectura.com",
            "Rebeca Gonzalez": "r-gonzalez@axisarquitectura.com",
            "Esteban Mendez": "e-mendez@axisarqutiectura.com"
        }

        with st.form("form_pr", clear_on_submit=False):
            requisicion = st.text_input("No. de Requisición")
            fecha_solicitud = st.date_input("Fecha de Solicitud", value=datetime.today())
            descripcion = st.text_area("Descripción")
            planta = st.text_input("Planta")
            usuario = st.text_input("Usuario")
            responsable = st.selectbox("Responsable de Cotización", list(responsables.keys()))
            email_responsable = responsables[responsable]

            submitted = st.form_submit_button("Guardar PR")
            if submitted:
                data = {
                    "requisicion": requisicion,
                    "fecha_solicitud": str(fecha_solicitud),
                    "descripcion": descripcion,
                    "planta": planta,
                    "usuario": usuario,
                    "proveedor": "",
                    "fecha_envio": "",
                    "importe": 0.0,
                    "estatus": "Abierta",
                    "orden_compra": "",
                    "responsable": responsable,
                    "email_responsable": email_responsable
                }
                insertar_cotizacion(data)
                st.success("✅ PR registrada correctamente")

    if opcion == "Operación":
        st.header("🔧 Registro de Cotización")
        df = obtener_cotizaciones()
        pendientes = df[df["estatus"] == "Abierta"]
        seleccion = st.selectbox("Selecciona PR sin cotización", pendientes["requisicion"] if not pendientes.empty else [])

        if seleccion:
            fila = pendientes[pendientes["requisicion"] == seleccion].iloc[0]
            with st.form("form_operacion"):
                proveedor = st.text_input("Proveedor")
                fecha_envio = st.date_input("Fecha de Cotización", value=date.today())
                importe = st.number_input("Importe", min_value=0.0, step=100.0)

                submitted = st.form_submit_button("Actualizar Cotización")
                if submitted:
                    actualizar_cotizacion(
                        int(fila["id"]), proveedor, str(fecha_envio), importe, "En Proceso", ""
                    )
                    st.success("✅ Cotización actualizada correctamente")

    if opcion == "Seguimiento":
        st.header("⏱️ Seguimiento de PRs Abiertas")
        df = obtener_cotizaciones()
        df_abiertas = df[(df["proveedor"] != "") & (df["orden_compra"] == "")]

        if not df_abiertas.empty:
            for _, fila in df_abiertas.iterrows():
                with st.expander(f"PR: {fila['requisicion']} - {fila['descripcion']}"):
                    st.write(f"Fecha de Solicitud: {fila['fecha_solicitud']}")
                    motivo = st.text_area("¿Por qué no se generó orden de compra?", key=f"motivo_{fila['id']}").strip()
                    orden = st.text_input("Número de Orden de Compra", key=f"orden_{fila['id']}").strip()
                    if st.button("Guardar seguimiento", key=f"guardar_{fila['id']}"):
                        if orden:
                            estatus_final = "Con Orden de Compra"
                        elif motivo:
                            estatus_final = "Cancelada"
                        else:
                            st.warning("Debes ingresar un número de orden o un motivo de cancelación.")
                            continue
                        actualizar_cotizacion(
                            int(fila["id"]), fila["proveedor"], fila["fecha_envio"], fila["importe"], estatus_final, orden
                        )
                        st.success("Seguimiento actualizado.")
        else:
            st.info("No hay PRs en seguimiento pendientes de orden de compra.")

    if opcion == "Cotizaciones Completadas":
        st.header("📊 Concentrado de Cotizaciones")
        df = obtener_cotizaciones()
        st.dataframe(df)
        if not df.empty:
            output, nombre_archivo = exportar_excel(df)
            st.download_button(
                label="📥 Descargar Excel",
                data=output,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()

