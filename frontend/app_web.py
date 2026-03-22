import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
from modulos.gestion_reservas import render_reservas

# --- CONFIGURACIÓN INICIAL ---
LOGO_PATH = os.path.join("frontend", "logo_restaurante.jpg")
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Restaurante Don Juan - Gestión", layout="wide", page_icon="🍽️")

# --- FUNCIONES DE APOYO ---
def pie_de_pagina():
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "© 2026 Restaurante Don Juan - Sistema de Gestión Interna.</div>", 
        unsafe_allow_html=True
    )

# --- ESTADO DE SESIÓN ---
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# ==========================================
#                PANTALLA DE LOGIN
# ==========================================
if st.session_state.token is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=200)
        st.title("🔐 Acceso al Sistema")
        
        with st.form("login_form"):
            u = st.text_input("Correo electrónico", placeholder="ejemplo@correo.com")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                try:
                    res = requests.post(f"{API_URL}/users/login", data={"username": u, "password": p})
                    if res.status_code == 200:
                        d = res.json()
                        st.session_state.token = d["access_token"]
                        st.session_state.role = d["role"]
                        st.session_state.user_name = u.split('@')[0]
                        st.success("✅ ¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas o cuenta inactiva.")
                except:
                    st.error("📡 Error de conexión con el servidor.")
        pie_de_pagina()

# ==========================================
#         DASHBOARD PRINCIPAL (LOGUEADO)
# ==========================================
else:
    # --- PROTECCIÓN DE SEGURIDAD ---
    # Si por alguna razón el token se pierde, volvemos al login
    if not st.session_state.token:
        st.session_state.token = None
        st.rerun()

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    rol = st.session_state.role
    
    # --- BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=150)
        st.write(f"### 👋 Hola, {st.session_state.user_name}")
        st.caption(f"Rol: {str(rol).upper()}")
        st.divider()
        if st.button("🚪 Cerrar Sesión", width='stretch'):
            st.session_state.token = None
            st.session_state.role = None
            st.rerun()

    # Definición de pestañas según rol
    if rol == "admin":
        menu = ["🪑 Mesas", "👥 Clientes", "📅 Reservas", "📋 Auditoría", "⚙️ Usuarios"]
    elif rol == "mesero":
        menu = ["🪑 Mesas", "👥 Clientes", "📅 Reservas"]
    else:
        menu = ["🔍 Mis Reservas", "👤 Mi Perfil"]
    
    tabs = st.tabs(menu)

    # --- PESTAÑA 0: MESAS ---
    with tabs[0]:
        if rol in ["admin", "mesero"]:
            st.header("🪑 Gestión de Mesas")
            res_t = requests.get(f"{API_URL}/tables/", headers=headers)
            if res_t.status_code == 200:
                mesas_list = res_t.json()
                st.dataframe(pd.DataFrame(mesas_list), width='stretch')
                
                st.divider()
                st.subheader("🔍 Cargar Mesa para Editar")
                opciones_m = {f"Mesa {m['number']} | Cap: {m['capacity']}": m for m in mesas_list}
                sel_m = st.selectbox("Busca una mesa:", ["-- Nueva Mesa --"] + list(opciones_m.keys()))
                m_data = opciones_m.get(sel_m, {"id": 0, "number": 1, "capacity": 2, "status": "libre"})

                col1, col2 = st.columns(2)
                with col1:
                    with st.form("form_mesas"):
                        st.info("Editando..." if m_data['id'] != 0 else "Creando Nueva")
                        n_num = st.number_input("Número", value=int(m_data['number']), min_value=1)
                        n_cap = st.number_input("Capacidad", value=int(m_data['capacity']), min_value=1)
                        # Validamos que el estado exista en la lista
                        lista_estados = ["libre", "ocupada", "reservada"]
                        idx_est = lista_estados.index(m_data['status']) if m_data['status'] in lista_estados else 0
                        n_stat = st.selectbox("Estado", lista_estados, index=idx_est)
                        
                        if st.form_submit_button("💾 Guardar Mesa"):
                            payload = {"number": n_num, "capacity": n_cap, "status": n_stat}
                            if m_data['id'] == 0:
                                requests.post(f"{API_URL}/tables/", json=payload, headers=headers)
                            else:
                                requests.put(f"{API_URL}/tables/{m_data['id']}", json=payload, headers=headers)
                            st.rerun()
                with col2:
                    if rol == "admin" and m_data['id'] != 0:
                        st.subheader("🗑️ Eliminar")
                        if st.button("🔴 Borrar Mesa") and st.checkbox("Confirmar borrado"):
                            requests.delete(f"{API_URL}/tables/{m_data['id']}", headers=headers)
                            st.rerun()
        else:
            st.header("🔍 Tus Reservaciones")
            res_me = requests.get(f"{API_URL}/reservations/me", headers=headers)
            if res_me.status_code == 200:
                st.table(res_me.json()) if res_me.json() else st.info("No tienes reservas.")

    # --- PESTAÑA 1: CLIENTES ---
    if rol in ["admin", "mesero"]:
        with tabs[1]:
            st.header("👥 Gestión de Clientes")
            res_c = requests.get(f"{API_URL}/customers/", headers=headers)
            if res_c.status_code == 200:
                c_list = res_c.json()
                st.dataframe(pd.DataFrame(c_list), width='stretch')
                st.divider()
                opciones_c = {f"{c['full_name']} | 📱 {c.get('phone','')}": c for c in c_list}
                sel_c = st.selectbox("Busca por nombre o teléfono:", ["-- Seleccionar --"] + list(opciones_c.keys()))
                c_sel = opciones_c.get(sel_c, {"id": 0, "full_name": "", "phone": "", "whatsapp": "", "address": "", "user_id": 0})
                c1, c2 = st.columns(2)
                with c1:
                    with st.form("form_cliente"):
                        f_name = st.text_input("Nombre Completo", value=c_sel['full_name'])
                        f_phone = st.text_input("Teléfono", value=c_sel['phone'])
                        f_ws = st.text_input("WhatsApp", value=c_sel['whatsapp'])
                        f_dir = st.text_input("Dirección", value=c_sel.get('address',''))
                        if st.form_submit_button("💾 Actualizar Ficha"):
                            if c_sel['id'] != 0:
                                p = {"full_name": f_name, "phone": f_phone, "whatsapp": f_ws, "address": f_dir}
                                requests.put(f"{API_URL}/customers/{c_sel['id']}", json=p, headers=headers)
                                st.rerun()

    # --- PESTAÑA 2: RESERVAS (MODULAR) ---
    with tabs[2]:
        if rol in ["admin", "mesero"]:
            # Solo llamamos si el rol está definido para evitar el TypeError
            if rol:
                render_reservas(API_URL, headers, rol)
        else:
            st.header("👤 Mi Perfil")
            st.info("Completa tus datos para agilizar tus reservas.")

    # --- PESTAÑA 3: AUDITORÍA (ADMIN) ---
    if rol == "admin":
        with tabs[3]:
            st.header("📋 Auditoría de XAMPP")
            if st.button("🔄 Consultar Logs Recientes", key="btn_logs_final"):
                res_l = requests.get(f"{API_URL}/reservations/logs", headers=headers)
                if res_l.status_code == 200:
                    st.dataframe(pd.DataFrame(res_l.json()), width='stretch')

    # --- PESTAÑA 4: USUARIOS (ADMIN) ---
    if rol == "admin":
        with tabs[4]:
            st.header("⚙️ Gestión de Usuarios")
            res_u = requests.get(f"{API_URL}/users/", headers=headers)
            if res_u.status_code == 200:
                u_list = res_u.json()
                st.dataframe(pd.DataFrame(u_list), width='stretch')
                st.divider()
                op_u = {u['email']: u for u in u_list}
                sel_u = st.selectbox("Editar usuario:", ["-- Nuevo --"] + list(op_u.keys()))
                u_dat = op_u.get(sel_u, {"id": 0, "email": "", "role": "cliente", "is_active": True})
                with st.form("u_form_final"):
                    u_em = st.text_input("Email", value=u_dat['email'])
                    u_ro = st.selectbox("Rol", ["admin", "mesero", "cliente"], 
                                      index=["admin", "mesero", "cliente"].index(u_dat['role']))
                    u_ac = st.checkbox("Activo", value=u_dat['is_active'])
                    if st.form_submit_button("Guardar Usuario"):
                        p_u = {"username": u_em.split('@')[0], "email": u_em, "role": u_ro, "is_active": u_ac}
                        if u_dat['id'] == 0:
                            p_u["password"] = "123456" 
                            requests.post(f"{API_URL}/users/", json=p_u, headers=headers)
                        else:
                            requests.put(f"{API_URL}/users/{u_dat['id']}", json=p_u, headers=headers)
                        st.rerun()

    pie_de_pagina()