import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def render_reservas(api_url, headers, rol):
    st.header("📅 Gestión de Reservaciones")
    
    # 1. Obtener datos de la DB
    res_r = requests.get(f"{api_url}/reservations/", headers=headers)
    res_c = requests.get(f"{api_url}/customers/", headers=headers)
    res_m = requests.get(f"{api_url}/tables/", headers=headers)

    if res_r.status_code == 200 and res_c.status_code == 200 and res_m.status_code == 200:
        reservas_list = res_r.json()
        clientes_list = res_c.json()
        mesas_list = res_m.json()

        st.subheader("Listado Actual en XAMPP")
        st.dataframe(pd.DataFrame(reservas_list), use_container_width=True)
        st.divider()

        # 2. Diccionarios de apoyo
        dict_clientes = {f"{c['full_name']} (ID: {c['id']})": c['id'] for c in clientes_list}
        dict_mesas = {f"Mesa {m['number']} | Cap: {m['capacity']}": m for m in mesas_list}
        
        # 3. Buscador de Reservas
        opciones_res = {f"Reserva #{r['id']} - Cliente ID: {r['customer_id']}": r for r in reservas_list}
        sel_res = st.selectbox("🔍 Cargar reserva para editar:", ["-- Nueva Reserva --"] + list(opciones_res.keys()))
        
        r_sel = opciones_res.get(sel_res, {"id": 0, "customer_id": None, "table_id": None, "pax": 1, "status": "confirmada"})

        # 4. Formulario con Lógica de Negocio
        with st.form("form_reservas_validado"):
            st.markdown("### 📝 Datos de la Reserva")
            col1, col2 = st.columns(2)
            
            with col1:
                # Selector de Cliente
                c_nombres = list(dict_clientes.keys())
                c_ids = list(dict_clientes.values())
                idx_c = c_ids.index(r_sel['customer_id']) if r_sel['customer_id'] in c_ids else 0
                f_cliente = st.selectbox("Nombre del Cliente", c_nombres, index=idx_c)
                
                # Selector de Mesa
                m_nombres = list(dict_mesas.keys())
                idx_m = 0
                for i, m_name in enumerate(m_nombres):
                    if dict_mesas[m_name]['id'] == r_sel['table_id']:
                        idx_m = i
                        break
                f_mesa_label = st.selectbox("Asignar Mesa", m_nombres, index=idx_m)

            with col2:
                f_pax = st.number_input("Número de personas (Pax)", min_value=1, value=int(r_sel['pax']))
                f_status = st.selectbox("Estado", ["confirmada", "cancelada", "completada"], 
                                       index=["confirmada", "cancelada", "completada"].index(r_sel['status']))
                f_date = st.date_input("Fecha de Reserva")

            if st.form_submit_button("💾 Guardar Reservación"):
                # --- LÓGICA DE VALIDACIÓN ---
                mesa_datos = dict_mesas[f_mesa_label]
                
                if f_pax > mesa_datos['capacity']:
                    st.warning(f"⚠️ **Capacidad superada**: La {f_mesa_label} solo permite {mesa_datos['capacity']} personas y quieres registrar {f_pax}.")
                else:
                    payload = {
                        "customer_id": dict_clientes[f_cliente],
                        "table_id": mesa_datos['id'],
                        "reservation_date": str(f_date),
                        "reservation_time": "12:00",
                        "pax": f_pax,
                        "status": f_status
                    }
                    
                    if r_sel['id'] == 0:
                        res = requests.post(f"{api_url}/reservations/", json=payload, headers=headers)
                    else:
                        res = requests.put(f"{api_url}/reservations/{r_sel['id']}", json=payload, headers=headers)
                    
                    if res.status_code in [200, 201]:
                        st.success("✅ ¡Reserva procesada correctamente!")
                        st.rerun()
                    else:
                        st.error("❌ No se pudo guardar. Revisa la conexión al Backend.")

    # 5. Opción de borrar (Solo para registros existentes)
    if r_sel['id'] != 0 and rol == "admin":
        st.divider()
        if st.button("🗑️ Eliminar esta reserva definitivamente"):
            if st.checkbox("Confirmo que deseo borrar este registro de XAMPP"):
                res_del = requests.delete(f"{api_url}/reservations/{r_sel['id']}", headers=headers)
                if res_del.status_code == 200:
                    st.success("Reserva eliminada.")
                    st.rerun()