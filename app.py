import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import json
import pandas as pd
from io import BytesIO
import datetime

st.set_page_config(
    page_title="Agricultural Land Control",
    page_icon="🗺️",
    layout="wide"
)

# ── GitHub sozlamalari ──────────────────────────────────────────────
GITHUB_USER = "murod-one"
GITHUB_REPO = "agricultural-land-control"
GITHUB_BRANCH = "main"

# Tumanlar ro'yxati: faqat Xonobot
TUMANLAR = {
    "Xonobot": "xonobod",
}

EKIN_TURLARI = ["Paxta", "Bug'doy", "Shudgor"]

EKIN_RANGLAR = {
    "Paxta":   "#EF9F27",
    "Bug'doy": "#639922",
    "Shudgor": "#378ADD",
    None:      "#aac090",
}

# ── Session state ───────────────────────────────────────────────────
if "belgilangan" not in st.session_state:
    st.session_state.belgilangan = {}
if "tanlangan_dala" not in st.session_state:
    st.session_state.tanlangan_dala = None

# ── Yordamchi funksiyalar ───────────────────────────────────────────
def github_raw_url(fayl_nomi: str) -> str:
    return f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{fayl_nomi}.geojson"

@st.cache_data(ttl=300, show_spinner=False)
def geojson_yukla(tuman_kodi: str):
    url = github_raw_url(tuman_kodi)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Yuklash xatosi: {e}")
        return None

def dala_id(feature):
    props = feature.get("properties", {})
    return str(props.get("id") or props.get("ID") or props.get("fid") or id(feature))

def dala_nom(feature):
    props = feature.get("properties", {})
    for key in ["nom", "name", "NAME", "NOM", "dala_nom", "field_name"]:
        if key in props and props[key]:
            return str(props[key])
    return "Nomsiz dala"

def dala_gektar(feature):
    props = feature.get("properties", {})
    for key in ["gektar", "ha", "HA", "area", "AREA", "maydoni"]:
        if key in props and props[key] is not None:
            try:
                return float(props[key])
            except:
                pass
    return 0.0

def centroid(feature):
    coords = feature["geometry"]["coordinates"]
    gtype = feature["geometry"]["type"]
    if gtype == "Polygon":
        ring = coords[0]
    elif gtype == "MultiPolygon":
        ring = coords[0][0]
    else:
        return [41.3, 69.2]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return [sum(lats)/len(lats), sum(lons)/len(lons)]

def excel_yuklab_olish():
    rows = []
    for did, info in st.session_state.belgilangan.items():
        rows.append({
            "Dala nomi": info["nom"],
            "Maydoni (ga)": info["gektar"],
            "Ekin turi": info["ekin"],
            "Sana": info.get("sana", ""),
        })
    if not rows:
        return None
    df = pd.DataFrame(rows)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dalalar")
        ws = writer.sheets["Dalalar"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)
    buf.seek(0)
    return buf

# ── UI ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container{padding-top:1rem}
.stButton>button{width:100%}
.alc-header{display:flex;align-items:center;gap:10px;padding:4px 0 12px 0}
.alc-icon{width:36px;height:36px;border-radius:8px;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.alc-title{font-size:14px;font-weight:600;color:inherit;line-height:1.2}
.alc-sub{font-size:10px;opacity:0.55;margin-top:1px}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="alc-header">
  <div class="alc-icon">🗺️</div>
  <div>
    <div class="alc-title">Agricultural Land Control</div>
    <div class="alc-sub">Geofazoviy Monitoring Tizimi</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.divider()

    tuman_nom = st.selectbox("Tuman tanlang", options=list(TUMANLAR.keys()), index=0)
    tuman_kodi = TUMANLAR[tuman_nom]
    st.divider()

    belg = st.session_state.belgilangan
    jami = len(belg)
    paxta_soni  = sum(1 for v in belg.values() if v["ekin"] == "Paxta")
    bugdoy_soni = sum(1 for v in belg.values() if v["ekin"] == "Bug'doy")
    shudgor_soni= sum(1 for v in belg.values() if v["ekin"] == "Shudgor")

    col1, col2 = st.columns(2)
    col1.metric("Belgilangan", jami)
    col2.metric("Paxta", paxta_soni)
    col1.metric("Bug'doy", bugdoy_soni)
    col2.metric("Shudgor", shudgor_soni)
    st.divider()

    st.markdown("**Kalit**")
    for ekin, rang in EKIN_RANGLAR.items():
        label = ekin or "Belgilanmagan"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            f'<div style="width:14px;height:14px;background:{rang};border-radius:3px"></div>'
            f'<span style="font-size:13px">{label}</span></div>',
            unsafe_allow_html=True,
        )
    st.divider()

    excel_data = excel_yuklab_olish()
    if excel_data:
        st.download_button(
            label="📥 Excel yuklab olish",
            data=excel_data,
            file_name=f"ALC_{tuman_nom}_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("Hali dala belgilanmagan")

    if jami > 0:
        if st.button("🗑 Hammasini tozalash", use_container_width=True):
            st.session_state.belgilangan = {}
            st.session_state.tanlangan_dala = None
            st.rerun()

# ── Main area ────────────────────────────────────────────────────────
col_map, col_panel = st.columns([3, 1])

with col_map:
    with st.spinner(f"{tuman_nom} dalalari yuklanmoqda..."):
        gj = geojson_yukla(tuman_kodi)

    if gj is None:
        st.error(f"❌ **{tuman_nom}** uchun GeoJSON topilmadi.\n\nIltimos, `{tuman_kodi}.geojson` fayli GitHub repozitoriyangizda mavjudligini tekshiring.")
        st.stop()

    features = gj.get("features", [])
    if not features:
        st.warning("GeoJSON bo'sh — polygonlar topilmadi.")
        st.stop()

    center = centroid(features[0])
    st.caption(f"Xarita markazi: {center[0]:.4f}, {center[1]:.4f} | Dalar soni: {len(features)}")

    # Xarita yaratish
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # Sun'iy yo'ldosh qatlami
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Sun'iy yo'ldosh",
        overlay=False,
        control=True,
    ).add_to(m)

    # Ko'cha xaritasi qatlami (asosiy)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        name="Xarita",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.LayerControl(position="topright").add_to(m)

    # Polygonlarni chizish
    for feat in features:
        did   = dala_id(feat)
        nom   = dala_nom(feat)
        ga    = dala_gektar(feat)
        info  = st.session_state.belgilangan.get(did)
        ekin  = info["ekin"] if info else None
        rang  = EKIN_RANGLAR[ekin]

        popup_html = f"""
        <div style="font-family:sans-serif;min-width:160px">
          <b style="font-size:14px">{nom}</b><br>
          <span style="color:#666;font-size:12px">{ga:.1f} gektar</span><br>
          <hr style="margin:6px 0">
          <span style="font-size:12px">Ekin: <b>{ekin or "Belgilanmagan"}</b></span>
        </div>
        """

        folium.GeoJson(
            feat,
            name=nom,
            style_function=lambda x, r=rang: {
                "fillColor": r,
                "color": "#fff",
                "weight": 1.5,
                "fillOpacity": 0.65,
            },
            highlight_function=lambda x: {
                "weight": 3,
                "color": "#333",
                "fillOpacity": 0.85,
            },
            tooltip=folium.Tooltip(f"{nom} — {ga:.1f} ga"),
            popup=folium.Popup(popup_html, max_width=220),
        ).add_to(m)

    # Xaritani ko'rsatish (kritik qism)
    map_data = st_folium(
        m,
        width=700,
        height=550,
        returned_objects=["last_object_clicked"],
        key="xonobot_map",
    )

    # Bosilgan polygonni aniqlash
    clicked = map_data.get("last_object_clicked")
    if clicked:
        lat, lon = clicked.get("lat"), clicked.get("lng")
        if lat and lon:
            try:
                from shapely.geometry import Point, shape
                pt = Point(lon, lat)
                for feat in features:
                    try:
                        if shape(feat["geometry"]).contains(pt):
                            st.session_state.tanlangan_dala = dala_id(feat)
                            st.rerun()
                            break
                    except:
                        pass
            except Exception as e:
                st.error(f"Tanlash xatosi: {e}")

with col_panel:
    st.markdown("### Dala ma'lumoti")
    td = st.session_state.tanlangan_dala

    if td is None:
        st.info("Belgilash uchun dalani bosing")
    else:
        feat = next((f for f in features if dala_id(f) == td), None)
        if feat is None:
            st.warning("Dala topilmadi")
        else:
            nom = dala_nom(feat)
            ga  = dala_gektar(feat)
            info = st.session_state.belgilangan.get(td, {})

            st.markdown(f"**{nom}**")
            st.markdown(f"Maydon: `{ga:.1f} ga`")

            mavjud_ekin = info.get("ekin")
            if mavjud_ekin:
                st.success(f"✅ Belgilangan: **{mavjud_ekin}**")

            st.markdown("**Ekin turini tanlang:**")
            for ekin in EKIN_TURLARI:
                rang_map = {"Paxta": "🟡", "Bug'doy": "🟢", "Shudgor": "🔵"}
                if st.button(f"{rang_map[ekin]} {ekin}", key=f"ekin_{ekin}_{td}"):
                    st.session_state.belgilangan[td] = {
                        "nom": nom,
                        "gektar": round(ga, 2),
                        "ekin": ekin,
                        "sana": str(datetime.date.today()),
                    }
                    st.rerun()

            if mavjud_ekin:
                st.divider()
                if st.button("🗑 Belgilashni olib tashlash", key=f"del_{td}"):
                    del st.session_state.belgilangan[td]
                    st.session_state.tanlangan_dala = None
                    st.rerun()

    if st.session_state.belgilangan:
        st.divider()
        st.markdown("**Belgilangan dalalar**")
        rows = []
        for did, v in st.session_state.belgilangan.items():
            rows.append({"Dala": v["nom"], "Ga": v["gektar"], "Ekin": v["ekin"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
