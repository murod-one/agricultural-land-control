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
GITHUB_USER = "YOUR_USERNAME"        # o'zgartiring
GITHUB_REPO = "YOUR_REPO"           # o'zgartiring
GITHUB_BRANCH = "main"

# Tumanlar ro'yxati: ko'rsatiladigan nom → GitHub fayl nomi
TUMANLAR = {
    "Chirchiq": "chirchiq",
    "Angren": "angren",
    "Ohangaron": "ohangaron",
    "Parkent": "parkent",
    "Bo'stonliq": "bostonliq",
    "Qibray": "qibray",
    "Yuqorichirchiq": "yuqorichirchiq",
    "O'rtachirchiq": "ortachirchiq",
    "Quyi Chirchiq": "quyichirchiq",
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
    st.session_state.belgilangan = {}   # {dala_id: {nom, gektar, ekin}}
if "tanlangan_dala" not in st.session_state:
    st.session_state.tanlangan_dala = None
if "geojson_cache" not in st.session_state:
    st.session_state.geojson_cache = {}

# ── Yordamchi funksiyalar ───────────────────────────────────────────
def github_raw_url(fayl_nomi: str) -> str:
    return (
        f"https://raw.githubusercontent.com/"
        f"{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{fayl_nomi}.geojson"
    )

@st.cache_data(ttl=300, show_spinner=False)
def geojson_yukla(tuman_kodi: str):
    url = github_raw_url(tuman_kodi)
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None

def dala_id(feature):
    props = feature.get("properties", {})
    return props.get("id") or props.get("ID") or props.get("fid") or str(id(feature))

def dala_nom(feature):
    props = feature.get("properties", {})
    for key in ["nom", "name", "NAME", "NOM", "dala_nom", "field_name"]:
        if props.get(key):
            return str(props[key])
    return "Nomsiz dala"

def dala_gektar(feature):
    props = feature.get("properties", {})
    for key in ["gektar", "ha", "HA", "area", "AREA", "maydoni"]:
        if props.get(key) is not None:
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
    <div class="alc-sub">Geospatial Monitoring System</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.divider()

    tuman_nom = st.selectbox(
        "Select district",
        options=list(TUMANLAR.keys()),
        index=0,
    )
    tuman_kodi = TUMANLAR[tuman_nom]

    st.divider()

    # Belgilangan dalalar statistikasi
    belg = st.session_state.belgilangan
    jami = len(belg)
    paxta_soni  = sum(1 for v in belg.values() if v["ekin"] == "Paxta")
    bugdoy_soni = sum(1 for v in belg.values() if v["ekin"] == "Bug'doy")
    shudgor_soni= sum(1 for v in belg.values() if v["ekin"] == "Shudgor")

    col1, col2 = st.columns(2)
    col1.metric("Tagged", jami)
    col2.metric("Cotton", paxta_soni)
    col1.metric("Wheat", bugdoy_soni)
    col2.metric("Fallow", shudgor_soni)

    st.divider()

    # Legend
    st.markdown("**Legend**")
    label_en = {"Paxta": "Cotton", "Bug'doy": "Wheat", "Shudgor": "Fallow", None: "Not tagged"}
    for ekin, rang in EKIN_RANGLAR.items():
        label = label_en.get(ekin, ekin)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            f'<div style="width:14px;height:14px;background:{rang};border-radius:3px"></div>'
            f'<span style="font-size:13px">{label}</span></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Excel download
    excel_data = excel_yuklab_olish()
    if excel_data:
        st.download_button(
            label="📥 Download Excel",
            data=excel_data,
            file_name=f"ALC_{tuman_nom}_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("No fields tagged yet")

    if jami > 0:
        if st.button("🗑 Clear all", use_container_width=True):
            st.session_state.belgilangan = {}
            st.session_state.tanlangan_dala = None
            st.rerun()

# ── Main area ────────────────────────────────────────────────────────
col_map, col_panel = st.columns([3, 1])

with col_map:
    with st.spinner(f"Loading {tuman_nom} fields..."):
        gj = geojson_yukla(tuman_kodi)

    if gj is None:
        st.error(
            f"❌ GeoJSON not found for **{tuman_nom}**.\n\n"
            f"Please make sure `{tuman_kodi}.geojson` exists in your GitHub repository."
        )
        st.stop()

    features = gj.get("features", [])
    if not features:
        st.warning("GeoJSON is empty — no polygons found.")
        st.stop()

    center = centroid(features[0])

    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles="OpenStreetMap",
    )

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
    ).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)
    folium.LayerControl().add_to(m)

    folium.plugins.LocateControl(
        auto_start=True,
        fly_to=False,
        strings={"title": "My location", "popup": "You are here"},
    ).add_to(m)

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
          <span style="color:#666;font-size:12px">{ga:.1f} hectares</span><br>
          <hr style="margin:6px 0">
          <span style="font-size:12px">Crop: <b>{ekin or "Not tagged"}</b></span>
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
            tooltip=folium.Tooltip(f"{nom} — {ga:.1f} ha"),
            popup=folium.Popup(popup_html, max_width=220),
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=550, returned_objects=["last_object_clicked"])

    clicked = map_data.get("last_object_clicked")
    if clicked:
        lat, lon = clicked.get("lat"), clicked.get("lng")
        if lat and lon:
            from shapely.geometry import Point, shape
            pt = Point(lon, lat)
            for feat in features:
                try:
                    if shape(feat["geometry"]).contains(pt):
                        st.session_state.tanlangan_dala = dala_id(feat)
                        break
                except:
                    pass

with col_panel:
    st.markdown("### Field Info")

    td = st.session_state.tanlangan_dala

    if td is None:
        st.info("Click on a field to tag it")
    else:
        feat = next((f for f in features if dala_id(f) == td), None)
        if feat is None:
            st.warning("Field not found")
        else:
            nom = dala_nom(feat)
            ga  = dala_gektar(feat)
            info = st.session_state.belgilangan.get(td, {})

            st.markdown(f"**{nom}**")
            st.markdown(f"Area: `{ga:.1f} ha`")

            mavjud_ekin = info.get("ekin")
            if mavjud_ekin:
                st.success(f"✅ Tagged: **{mavjud_ekin}**")

            st.markdown("**Select crop type:**")

            for ekin in EKIN_TURLARI:
                rang_map = {"Paxta": "🟡", "Bug'doy": "🟢", "Shudgor": "🔵"}
                label_map = {"Paxta": "Cotton", "Bug'doy": "Wheat", "Shudgor": "Fallow"}
                if st.button(f"{rang_map[ekin]} {label_map[ekin]}", key=f"ekin_{ekin}_{td}"):
                    st.session_state.belgilangan[td] = {
                        "nom": nom,
                        "gektar": round(ga, 2),
                        "ekin": label_map[ekin],
                        "sana": str(datetime.date.today()),
                    }
                    st.rerun()

            if mavjud_ekin:
                st.divider()
                if st.button("🗑 Remove tag", key=f"del_{td}"):
                    del st.session_state.belgilangan[td]
                    st.session_state.tanlangan_dala = None
                    st.rerun()

    if st.session_state.belgilangan:
        st.divider()
        st.markdown("**Tagged fields**")
        rows = []
        for did, v in st.session_state.belgilangan.items():
            rows.append({
                "Field": v["nom"],
                "Ha": v["gektar"],
                "Crop": v["ekin"],
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
