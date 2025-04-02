import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
from io import BytesIO
import numpy as np

st.set_page_config(page_title="Control de Cotizaciones", layout="wide")

# --- Lista de correos autorizados ---
usuarios_autorizados = {
    "v-ledezma@axisarquitectura.com": "Vicente Ledezma",
    "r-gonzalez@axisarquitectura.com": "Rebeca Gonzalez",
    "e-mendez@axisarqutiectura.com": "Esteban Mendez",
    "j-duran@axisarquitectura.com": "Juan Gabino Duran"
}

# --- Autenticación por correo con sesión ---
st.sidebar.title("Autenticación")
if "correo" not in st.session_state:
    st.session_state["correo"] = ""

correo_ingresado = st.sidebar.text_input("Ingresa tu correo corporativo", value=st.session_state["correo"])
st.session_state["correo"] = correo_ingresado

autenticado = correo_ingresado in usuarios_autorizados

if not autenticado:
    st.warning("⚠️ Ingresa un correo autorizado para acceder a la app.")
    st.stop()

# --- Mensaje de bienvenida personalizado ---
nombre_usuario = usuarios_autorizados[correo_ingresado]
st.sidebar.success(f"Bienvenido, {nombre_usuario} 👋")

# --- Base de datos ---
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

# --- Funciones ---
def insertar_cotizacion(data):
    cursor.execute("""
        INSERT INTO cotizaciones (
            requisicion, fecha_solicitud, descripcion, planta, usuario,
            proveedor, fecha_envio, importe, estatus, orden_compra, responsable, email_responsable
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

def obtener_cotizaciones():
    return pd.read_sql_query("SELECT * FROM cotizaciones", conn)

# --- Interfaz ---
st.title("📋 Control de Cotizaciones")

correo_usuario = st.session_state["correo"]
menu_completo = ["Capturar PR", "Operación", "Seguimiento", "Cotizaciones Completadas"]
menu_colaborador = ["Operación", "Seguimiento", "Cotizaciones Completadas"]
menu = menu_completo if correo_usuario == "j-duran@axisarquitectura.com" else menu_colaborador
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

if opcion == "Operación":
    st.header("🔧 Registro de Cotización")
    df = obtener_cotizaciones()
    pendientes = df[df["proveedor"] == ""]
    seleccion = st.selectbox("Selecciona PR sin cotización", pendientes["requisicion"] if not pendientes.empty else [])

    if seleccion:
        fila = pendientes[pendientes["requisicion"] == seleccion].iloc[0]
        with st.form("form_operacion"):
            proveedor = st.text_input("Proveedor")
            fecha_envio = st.date_input("Fecha de Cotización", value=date.today())
            importe = st.number_input("Importe", min_value=0.0, step=100.0)
            estatus = st.selectbox("Estatus", ["En Proceso", "Con Orden de Compra", "Cancelada"])
            orden_compra = st.text_input("Orden de Compra")

            submitted = st.form_submit_button("Actualizar Cotización")
            if submitted:
                actualizar_cotizacion(
                    fila["id"], proveedor, str(fecha_envio), importe, estatus, orden_compra
                )
                st.success("✅ Cotización actualizada correctamente")

if opcion == "Seguimiento":
    st.header("⏱️ Seguimiento de PRs Abiertas")
    df = obtener_cotizaciones()
    df_abiertas = df[df["proveedor"] == ""]
    if not df_abiertas.empty:
        df_abiertas = df_abiertas[["requisicion", "descripcion", "fecha_solicitud"]].copy()
        df_abiertas["fecha_solicitud"] = pd.to_datetime(df_abiertas["fecha_solicitud"])
        df_abiertas["días transcurridos"] = (pd.to_datetime("today") - df_abiertas["fecha_solicitud"]).dt.days

        def color_dias(val):
            return 'background-color: #ffa1a1' if val > 5 else ''

        st.dataframe(df_abiertas.style.applymap(color_dias, subset=["días transcurridos"]))
    else:
        st.info("No hay PRs abiertas en seguimiento.")

if opcion == "Cotizaciones Completadas":
    st.header("✅ Cotizaciones Completadas")
    df = obtener_cotizaciones()
    completadas = df[df["proveedor"] != ""]
    st.dataframe(completadas)
    if not completadas.empty:
        output, nombre_archivo = exportar_excel(completadas)
        st.download_button(
            label="📥 Descargar Excel",
            data=output,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


