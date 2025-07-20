import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors

def bersihkan_nama_kabupaten(nama):
    return nama.replace("Kab. ", "").replace("Kota ", "").strip().upper()

if "selected_kabupaten_from_map" not in st.session_state:
    st.session_state.selected_kabupaten_from_map = None

@st.cache_data(show_spinner=False)
def load_data(excel_file, geojson_path):
    df = pd.read_excel(excel_file)
    df.columns = df.columns.str.strip()
    df["Kabupaten"] = df["Kabupaten"].astype(str).apply(bersihkan_nama_kabupaten)
    df["Tipe Akun"] = df["Tipe Akun"].str.strip().str.lower()

    gdf = gpd.read_file(geojson_path)
    gdf["nm_dati2"] = gdf["nm_dati2"].astype(str).str.strip().str.upper()

    return df, gdf

def get_kabupaten_colors(gdf_filtered, cmap_name="tab20"):
    kabupaten_names = gdf_filtered["nm_dati2"].unique()
    cmap = cm.get_cmap(cmap_name, len(kabupaten_names))
    return dict(zip(kabupaten_names, [mcolors.to_hex(cmap(i)) for i in range(len(kabupaten_names))]))

def tampilkan_data_filter(df):
    st.markdown("### 🌟 Filter Data Akun Belajar.id")

    jenjang_list = ["Seluruh Jenjang"] + sorted(df["jenjang"].dropna().unique())
    kabupaten_list = ["Seluruh Kabupaten"] + sorted(df["Kabupaten"].dropna().unique())
    tipe_list = ["Guru dan Tenaga Kependidikan", "Guru", "Tenaga Kependidikan"]

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_jenjang = st.selectbox("📚 Pilih Jenjang", jenjang_list)
    with col2:
        if st.session_state.selected_kabupaten_from_map and st.session_state.selected_kabupaten_from_map in kabupaten_list:
            index_kab = kabupaten_list.index(st.session_state.selected_kabupaten_from_map)
        else:
            index_kab = 0
        selected_kab = st.selectbox("🏩 Pilih Kabupaten", kabupaten_list, index=index_kab)
    with col3:
        selected_tipe = st.selectbox("👥 Pilih Tipe Akun", tipe_list)

    if selected_kab != st.session_state.get("selected_kabupaten_from_map"):
        st.session_state.selected_kabupaten_from_map = selected_kab

    df_filtered = df.copy()
    if selected_jenjang != "Seluruh Jenjang":
        df_filtered = df_filtered[df_filtered["jenjang"] == selected_jenjang]
    if selected_kab != "Seluruh Kabupaten":
        df_filtered = df_filtered[df_filtered["Kabupaten"] == selected_kab.upper()]
    if selected_tipe == "Guru":
        df_filtered = df_filtered[df_filtered["Tipe Akun"] == "guru"]
    elif selected_tipe == "Tenaga Kependidikan":
        df_filtered = df_filtered[df_filtered["Tipe Akun"] == "tenaga kependidikan"]
    elif selected_tipe == "Guru dan Tenaga Kependidikan":
        df_filtered = df_filtered[df_filtered["Tipe Akun"].isin(["guru", "tenaga kependidikan"])]

    if df_filtered.empty:
        st.warning("⚠️ Tidak ada data yang cocok dengan filter.")
        return None

    st.markdown("### 📅 Rekapitulasi Data")
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("🔐 Total Akun Login", f"{df_filtered['Total Akun Login'].sum():,}")
    with col4:
        st.metric("📦 Total Akun Tersedia", f"{df_filtered['Total Akun Tersedia'].sum():,}")
    with col5:
        st.metric("📍 Total Akun Terdaftar Dapodik", f"{df_filtered['Total Akun Terdaftar Dapodik'].sum():,}")

    return df_filtered, selected_kab, selected_jenjang, selected_tipe

def buat_peta_terfilter(gdf, df_filtered):
    st.markdown("### 🗺️ Peta Interaktif")
    df_agg = df_filtered.groupby("Kabupaten")[["Total Akun Login", "Total Akun Tersedia", "Total Akun Terdaftar Dapodik"]].sum().reset_index()
    df_agg["Kabupaten"] = df_agg["Kabupaten"].str.upper()

    gdf_filtered = gdf.merge(df_agg, left_on="nm_dati2", right_on="Kabupaten", how="inner")
    colors = get_kabupaten_colors(gdf_filtered)

    m = folium.Map(location=[-5.2, 105.3], zoom_start=8, scrollWheelZoom=False)
    geojson = folium.GeoJson(
        gdf_filtered,
        name="Kabupaten",
        style_function=lambda x: {
            "fillColor": colors.get(x["properties"]["nm_dati2"], "#ccc"),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7
        },
        highlight_function=lambda x: {
            "fillColor": "#ffff00",     # warna kuning saat hover
            "color": "black",
            "weight": 3,
            "fillOpacity": 0.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["nm_dati2", "Total Akun Login", "Total Akun Tersedia", "Total Akun Terdaftar Dapodik"],
            aliases=["Kabupaten", "Total Akun Login", "Total Akun Tersedia", "Total Akun Terdaftar Dapodik"],
        )
    )
    geojson.add_to(m)
    return m, gdf_filtered, geojson

def tampilkan_bar_chart_persentase_login(df_filtered, selected_kab, selected_jenjang):
    st.markdown("### 📊 Persentase Login")
    if selected_kab == "Seluruh Kabupaten":
        group = df_filtered.groupby("Kabupaten")[["Total Akun Login", "Total Akun Terdaftar Dapodik"]].sum().reset_index()
        group["Persentase Login"] = (group["Total Akun Login"] / group["Total Akun Terdaftar Dapodik"]) * 100
        x, y = group["Kabupaten"], group["Persentase Login"]

        fig = go.Figure()
        fig.add_bar(x=x, y=y, marker_color="teal", text=[f"{v:.2f}%" for v in y], textposition="auto")
        fig.update_layout(title="Persentase Login per Kabupaten", xaxis_title="Kabupaten", yaxis_title="%", height=400)
        st.plotly_chart(fig, use_container_width=True)

    elif selected_jenjang == "Seluruh Jenjang":
        group = df_filtered[df_filtered["Kabupaten"] == selected_kab.upper()].groupby("jenjang")[["Total Akun Login", "Total Akun Terdaftar Dapodik"]].sum().reset_index()
        group["Persentase Login"] = (group["Total Akun Login"] / group["Total Akun Terdaftar Dapodik"]) * 100
        x, y = group["jenjang"], group["Persentase Login"]

        fig = go.Figure()
        fig.add_bar(x=x, y=y, marker_color="blue", text=[f"{v:.2f}%" for v in y], textposition="auto")
        fig.update_layout(title=f"Persentase Login per Jenjang di {selected_kab}", xaxis_title="Jenjang", yaxis_title="%", height=400)
        st.plotly_chart(fig, use_container_width=True)

    else:
        data = df_filtered[
            (df_filtered["Kabupaten"] == selected_kab.upper()) &
            (df_filtered["jenjang"] == selected_jenjang)
        ]
        login = data["Total Akun Login"].sum()
        terdaftar = data["Total Akun Terdaftar Dapodik"].sum()
        persentase = (login / terdaftar) * 100 if terdaftar > 0 else 0

        st.markdown(f"### 📌 Rekapitulasi Login - {selected_kab.title()} | Jenjang {selected_jenjang}")
        col1, col2, col3 = st.columns(3)
        col1.metric("🧾 Total Terdaftar", f"{terdaftar:,}")
        col2.metric("🔐 Total Login", f"{login:,}")
        col3.metric("📊 Persentase Login", f"{persentase:.2f}%")

def tampilkan_pie_chart(df, kab, tipe):
    if kab:
        df_kab = df[df["Kabupaten"] == kab]
        df_group = df_kab.groupby("jenjang")["Total Akun Login"].sum()
        fig = go.Figure(data=[go.Pie(labels=df_group.index, values=df_group.values, hole=0.4)])
        st.markdown("### 🥧 Distribusi Jenjang")
        st.plotly_chart(fig, use_container_width=True)

def tampilkan_seluruh_data(df):
    st.markdown("### 📄 Seluruh Data (Raw)")
    with st.expander("🔍 Klik untuk melihat seluruh data yang diunggah"):
        jumlah_baris = st.slider("Jumlah baris ditampilkan", 5, min(100, len(df)), 20)
        st.dataframe(df.head(jumlah_baris), use_container_width=True)
        st.caption(f"Menampilkan {jumlah_baris} dari total {len(df):,} baris")

def tampilkan_rekap_sekolah_per_jenjang(df_filtered, selected_kab, selected_jenjang):
    st.markdown("### 🏫 Rekapitulasi Jumlah Sekolah")

    total_sekolah = df_filtered["nama_sekolah"].nunique()

    # 🟢 Kondisi: Seluruh Kabupaten & Seluruh Jenjang
    if selected_kab == "Seluruh Kabupaten" and selected_jenjang == "Seluruh Jenjang":
        df_bar = df_filtered.groupby("Kabupaten")["nama_sekolah"].nunique().reset_index()
        df_bar = df_bar.rename(columns={"nama_sekolah": "Jumlah Sekolah"})

        # Tooltip jenjang per kabupaten
        df_tooltip = df_filtered.groupby(["Kabupaten", "jenjang"])["nama_sekolah"].nunique().reset_index()
        df_tooltip = df_tooltip.pivot(index="Kabupaten", columns="jenjang", values="nama_sekolah").fillna(0).astype(int)
        df_tooltip_text = df_tooltip.apply(
            lambda row: "<br>".join([f"{jenjang}: {jumlah}" for jenjang, jumlah in row.items()]),
            axis=1
        )

        fig = go.Figure()
        fig.add_bar(
            x=df_bar["Kabupaten"],
            y=df_bar["Jumlah Sekolah"],
            text=df_bar["Jumlah Sekolah"],
            textposition="auto",
            marker_color="green",
            hovertext=df_tooltip_text[df_bar["Kabupaten"]].values,
            hoverinfo="text"
        )
        fig.update_layout(
            title="Jumlah Sekolah per Kabupaten",
            xaxis_title="Kabupaten",
            yaxis_title="Jumlah Sekolah",
            height=400
        )

    # 🔵 Kondisi: Seluruh Kabupaten & Salah Satu Jenjang
    elif selected_kab == "Seluruh Kabupaten" and selected_jenjang != "Seluruh Jenjang":
        df_bar = df_filtered.groupby("Kabupaten")["nama_sekolah"].nunique().reset_index()
        df_bar = df_bar.rename(columns={"nama_sekolah": "Jumlah Sekolah"})

        fig = go.Figure()
        fig.add_bar(
            x=df_bar["Kabupaten"],
            y=df_bar["Jumlah Sekolah"],
            text=df_bar["Jumlah Sekolah"],
            textposition="auto",
            marker_color="green",
        )
        fig.update_layout(
            title=f"Jumlah Sekolah Jenjang {selected_jenjang} per Kabupaten",
            xaxis_title="Kabupaten",
            yaxis_title="Jumlah Sekolah",
            height=400
        )

    # 🔴 Kondisi: Satu Kabupaten & Seluruh Jenjang
    elif selected_kab != "Seluruh Kabupaten" and selected_jenjang == "Seluruh Jenjang":
        df_bar = df_filtered[df_filtered["Kabupaten"] == selected_kab.upper()]
        df_bar = df_bar.groupby("jenjang")["nama_sekolah"].nunique().reset_index()
        df_bar = df_bar.rename(columns={"nama_sekolah": "Jumlah Sekolah"})

        fig = go.Figure()
        fig.add_bar(
            x=df_bar["jenjang"],
            y=df_bar["Jumlah Sekolah"],
            text=df_bar["Jumlah Sekolah"],
            textposition="auto",
            marker_color="green",
        )
        fig.update_layout(
            title=f"Jumlah Sekolah di {selected_kab.title()} per Jenjang",
            xaxis_title="Jenjang",
            yaxis_title="Jumlah Sekolah",
            height=400
        )

    # 🔘 Kondisi: Satu Kabupaten & Satu Jenjang
    else:
        jumlah_sekolah = df_filtered["nama_sekolah"].nunique()
        st.markdown(f"#### 📍 Jumlah Sekolah di {selected_kab.title()} | Jenjang {selected_jenjang}")
        st.metric("🏫 Jumlah Sekolah", f"{jumlah_sekolah:,}")
        return  # Tidak menampilkan bar chart

    # Tampilkan card + bar chart
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("🏫 Total Sekolah", f"{total_sekolah:,}")
    with col2:
        st.plotly_chart(fig, use_container_width=True)

def main():
    st.set_page_config(
        page_title="Dashboard Visualisasi Data",
        page_icon="📊",
        layout="wide"
    )
    # CSS untuk mengurangi jarak kosong container peta
    st.markdown("""
        <style>
        .element-container:has(iframe) {
            margin-bottom: -20px !important;
        }
        iframe {
            height: 400px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title(":bar_chart: Dashboard Aktivasi Akun Belajar.id Provinsi Lampung")

    uploaded_excel = st.file_uploader("📄 Upload File Excel (.xlsx)", type=["xlsx"])
    geojson_path = "kape/data/lpg.geojson"

    if uploaded_excel:
        df, gdf = load_data(uploaded_excel, geojson_path)
        hasil = tampilkan_data_filter(df)

        if hasil:
            df_filtered, selected_kab, selected_jenjang, selected_tipe = hasil

            m, gdf_filtered, geojson_layer = buat_peta_terfilter(gdf, df_filtered)
            st_data = st_folium(m, width=750, height=400)

            clicked_kab = None
            if st_data and "last_active_drawing" in st_data and st_data["last_active_drawing"]:
                clicked_kab = st_data["last_active_drawing"]["properties"].get("nm_dati2", "").upper()

            if clicked_kab and clicked_kab != st.session_state.selected_kabupaten_from_map:
                st.session_state.selected_kabupaten_from_map = clicked_kab
                st.rerun()

            tampilkan_bar_chart_persentase_login(df_filtered, selected_kab, selected_jenjang)
            tampilkan_rekap_sekolah_per_jenjang(df_filtered, selected_kab, selected_jenjang)
            tampilkan_pie_chart(df, selected_kab if selected_kab != "Seluruh Kabupaten" else None, selected_tipe)
            tampilkan_seluruh_data(df)
            
    else:
        st.info("Silakan unggah file Excel untuk memulai.")

    st.markdown("""
        <hr style="margin-top: 50px; margin-bottom: 10px;">

        <div style='text-align: center; font-size: 14px; color: gray;'>
            © 2025 - Dashboard Aktivasi Akun Belajar.id | UPTD Balai TIK Dinas Pendidikan dan Kebudayaan Provinsi Lampung
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
