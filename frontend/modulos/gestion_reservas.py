import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
import time as python_time

def sincronizar_estados_mesas(api_url, headers, reservas_raw, mesas_list):
    """Verifica que las mesas con reservas confirmadas no aparezcan como LIBRES."""
    for mesa in mesas_list:
        # Buscamos si esta mesa tiene alguna reserva CONFIRMADA
        tiene_reserva_activa = any(
            r['table_id'] == mesa['id'] and r['status'] == 'confirmada' 
            for r in reservas_raw
        )
        
        # Si tiene reserva pero la mesa dice 'libre', forzamos la actualización en la DB
        if tiene_reserva_activa and mesa['status'] == 'libre':
            requests.patch(f"{api_url}/tables/{mesa['id']}/status", 
                           json={"status": "reservada"}, headers=headers)

def render_reservas(api_url, headers, rol):
    st.header("📅 Gestión de Reservaciones")
    
    # 1. Carga de datos de XAMPP
    res_r = requests.get(f"{api_url}/reservations/", headers=headers)
    res_c = requests.get(f"{api_url}/customers/", headers=headers)
    res_m = requests.get(f"{api_url}/tables/", headers=headers)

    if res_r.status_code == 200 and res_c.status_code == 200 and res_m.status_code == 200:
        reservas_raw = res_r.json()
        clientes = res_c.json()
        mesas = res_m.json()

        # --- SINCRONIZACIÓN AUTOMÁTICA (Tu petición de coherencia) ---
        sincronizar_estados_mesas(api_url, headers, reservas_raw, mesas)

        dict_c_id_nom = {c['id']: c['full_name'] for c in clientes}
        dict_c_nom_id = {f"{c['full_name']} (ID: {c['id']})": c['id'] for c in clientes}
        dict_m_label = {m['id']: f"Mesa {m['number']} | Cap: {m['capacity']}" for m in mesas}
        dict_m_data = {f"Mesa {m['number']} | Cap: {m['capacity']}": m for m in mesas}

        # Filtro de búsqueda
        opciones = {f"Reserva #{r['id']} - {dict_c_id_nom.get(r['customer_id'], 'S/N')}": r for r in reservas_raw}
        sel_res = st.selectbox("🔍 Cargar reserva para editar:", ["-- Nueva Reserva --"] + list(opciones.keys()))
        
        df = pd.DataFrame(reservas_raw)
        if not df.empty:
            df['Nombre Cliente'] = df['customer_id'].map(dict_c_id_nom)
            st.dataframe(df[['id', 'customer_id', 'Nombre Cliente', 'table_id', 'reservation_date', 'reservation_time', 'status']], width='stretch')

        st.divider()

        # Lógica del formulario (Margen de 2 horas y carga de datos fiel)
        if sel_res == "-- Nueva Reserva --":
            r_sel = {"id": 0, "customer_id": None, "table_id": None, "pax": 1, "status": "confirmada", 
                     "reservation_date": str(datetime.now().date()), "reservation_time": "12:00:00"}
        else:
            r_sel = opciones[sel_res]

        with st.form("form_reservas_final"):
            st.markdown(f"### 📝 Datos de la Reserva")
            col1, col2, col3 = st.columns(3)
            with col1:
                idx_c = list(dict_c_nom_id.values()).index(r_sel['customer_id']) if r_sel['customer_id'] in dict_c_nom_id.values() else 0
                f_cliente = st.selectbox("Cliente", list(dict_c_nom_id.keys()), index=idx_c)
                idx_m = list(dict_m_data.keys()).index(dict_m_label[r_sel['table_id']]) if r_sel['table_id'] in dict_m_label else 0
                f_mesa = st.selectbox("Mesa", list(dict_m_data.keys()), index=idx_m)
            with col2:
                f_date = st.date_input("Fecha", value=datetime.strptime(r_sel['reservation_date'], '%Y-%m-%d').date())
                f_time = st.time_input("Hora", value=datetime.strptime(r_sel['reservation_time'], '%H:%M:%S').time())
            with col3:
                f_pax = st.number_input("Pax", min_value=1, value=int(r_sel['pax']))
                f_status = st.selectbox("Estado", ["confirmada", "cancelada", "completada"], 
                                       index=["confirmada", "cancelada", "completada"].index(r_sel['status']))

            if st.form_submit_button("💾 Guardar Reservación"):
                m_sel = dict_m_data[f_mesa]
                nueva_fh = datetime.combine(f_date, f_time)
                
                # REGLA DE 2 HORAS
                choque = False
                for r in reservas_raw:
                    if r['table_id'] == m_sel['id'] and r['id'] != r_sel['id'] and r['status'] == 'confirmada':
                        r_fh = datetime.combine(datetime.strptime(r['reservation_date'], '%Y-%m-%d').date(),
                                               datetime.strptime(r['reservation_time'], '%H:%M:%S').time())
                        if abs((nueva_fh - r_fh).total_seconds()) < 7200:
                            choque = True; break
                
                if choque: st.error("🚫 Conflicto: La mesa ya tiene una reserva en ese horario.")
                else:
                    payload = {"customer_id": dict_c_nom_id[f_cliente], "table_id": m_sel['id'], 
                               "reservation_date": str(f_date), "reservation_time": str(f_time), "pax": f_pax, "status": f_status}
                    
                    # Guardamos la reserva
                    res = requests.post(f"{api_url}/reservations/", json=payload, headers=headers) if r_sel['id'] == 0 \
                          else requests.put(f"{api_url}/reservations/{r_sel['id']}", json=payload, headers=headers)
                    
                    if res.status_code in [200, 201]:
                        # Si confirmamos, la mesa pasa a RESERVADA. Si cancelamos, pasa a LIBRE.
                        nuevo_estado_mesa = "reservada" if f_status == "confirmada" else "libre"
                        requests.patch(f"{api_url}/tables/{m_sel['id']}/status", 
                                       json={"status": nuevo_estado_mesa}, headers=headers)
                        st.success("✅ Sistema sincronizado correctamente."); python_time.sleep(1); st.rerun()

    # --- LIBERACIÓN MANUAL PROTEGIDA ---
    st.divider()
    st.subheader("🔓 Liberación Manual")
    m_lib = st.selectbox("Mesa a liberar:", list(dict_m_data.keys()), key="lib_manual_res")
    if st.button("Confirmar Liberación"):
        m_obj = dict_m_data[m_lib]
        # Impedimos liberar si XAMPP dice que hay reserva confirmada
        if any(r['table_id'] == m_obj['id'] and r['status'] == 'confirmada' for r in reservas_raw):
            st.error("🚫 No se puede liberar: Hay una reserva confirmada activa.")
        else:
            requests.patch(f"{api_url}/tables/{m_obj['id']}/release", headers=headers)
            st.success("Mesa liberada."); python_time.sleep(1); st.rerun()