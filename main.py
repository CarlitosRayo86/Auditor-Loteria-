import asyncio
import aiohttp
import pandas as pd
import streamlit as st

# Configuración de página
st.set_page_config(page_title="Auditor de Lotería", page_icon="🎫", layout="centered")

st.title("🎫 Auditor de Secuencias - Lotería Nacional")
st.markdown("Escanea la secuencia (00000 - 59999) para detectar billetes no emitidos o no disponibles.")

# Formulario de entrada
sorteo = st.text_input("Número de Sorteo", placeholder="Ejemplo: 3850")
limite_concurrencia = st.slider("Velocidad de escaneo (Concurrencia)", min_value=10, max_value=100, value=40, step=10)

async def consultar_numero(session, sorteo, numero):
    num_fmt = f"{numero:05d}"
    url = f"https://alegrialoteria.gob.mx/api/v1/billetes/disponibilidad/{sorteo}/{num_fmt}"
    try:
        async with session.get(url, timeout=3) as res:
            if res.status == 404:
                return num_fmt
            elif res.status == 200:
                data = await res.json()
                if not data.get("emitido", True) or not data.get("disponible_online", False):
                    return num_fmt
    except Exception:
        pass
    return None

async def escanear_rango(sorteo, concurrencia, progress_bar, status_text):
    connector = aiohttp.TCPConnector(limit=concurrencia)
    headers = {"User-Agent": "Mozilla/5.0"}
    faltantes = []
    total = 60000
    lote_tamano = 2000

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for i in range(0, total, lote_tamano):
            tareas = [consultar_numero(session, sorteo, num) for num in range(i, min(i + lote_tamano, total))]
            resultados = await asyncio.gather(*tareas)
            
            for res in resultados:
                if res is not None:
                    faltantes.append(res)
            
            # Actualizar progreso en pantalla
            progreso = min((i + lote_tamano) / total, 1.0)
            progress_bar.progress(progreso)
            status_text.text(f"Escaneando... {int(progreso * 100)}% procesado ({len(faltantes)} fuera de secuencia).")

    return faltantes

if st.button("🚀 Iniciar Auditoría", type="primary"):
    if not sorteo.strip():
        st.warning("Por favor ingresa un número de sorteo válido.")
    else:
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        with st.spinner("Conectando con el servidor..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            faltantes = loop.run_until_complete(escanear_rango(sorteo, limite_concurrencia, progress_bar, status_text))

        st.success(f"¡Auditoría finalizada! Se encontraron {len(faltantes)} cachitos fuera de secuencia.")
        
        if faltantes:
            df = pd.DataFrame(faltantes, columns=["Número de Billete / Cachito"])
            st.dataframe(df, use_container_width=True)
            
            # Botón para descargar el reporte en TXT
            txt_data = "\n".join(faltantes)
            st.download_button(
                label="📥 Descargar reporte en TXT",
                data=txt_data,
                file_name=f"sorteo_{sorteo}_faltantes.txt",
                mime="text/plain"
            )
        else:
            st.info("Secuencia completa: Todos los billetes del 00000 al 59999 se encuentran disponibles.")
          
