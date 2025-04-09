import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

st.set_page_config(page_title="Water Quality Explorer", layout="wide")
st.title("💧 Water Quality Contaminant Explorer")

# --- Upload Files ---
st.sidebar.header("Upload Your CSV Files")
station_file = st.sidebar.file_uploader("Upload Station Locations (Part 1)", type=["csv"])
data_file = st.sidebar.file_uploader("Upload Contaminant Data (Part 2)", type=["csv"])

if station_file and data_file:
    # Load datasets
    station_df = pd.read_csv(station_file)
    data_df = pd.read_csv(data_file)

    # Clean & prepare data
    data_df["ActivityStartDate"] = pd.to_datetime(data_df["ActivityStartDate"], errors='coerce')
    data_df["ResultMeasureValue"] = pd.to_numeric(data_df["ResultMeasureValue"], errors='coerce')
    data_df.dropna(subset=["ActivityStartDate", "ResultMeasureValue"], inplace=True)

    # --- Contaminant Selector ---
    contaminant_options = sorted(data_df["CharacteristicName"].dropna().unique())
    selected_contaminant = st.sidebar.selectbox("Select Contaminant", contaminant_options)

    # Filter by contaminant
    contaminant_df = data_df[data_df["CharacteristicName"] == selected_contaminant]

    # Date and Value Range Filters
    min_date = contaminant_df["ActivityStartDate"].min()
    max_date = contaminant_df["ActivityStartDate"].max()
    date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    min_val = float(contaminant_df["ResultMeasureValue"].min())
    max_val = float(contaminant_df["ResultMeasureValue"].max())
    value_range = st.sidebar.slider("Select Value Range", min_value=min_val, max_value=max_val,
                                    value=(min_val, max_val))

    # Final filter
    filtered_df = contaminant_df[
        (contaminant_df["ActivityStartDate"] >= pd.to_datetime(date_range[0])) &
        (contaminant_df["ActivityStartDate"] <= pd.to_datetime(date_range[1])) &
        (contaminant_df["ResultMeasureValue"] >= value_range[0]) &
        (contaminant_df["ResultMeasureValue"] <= value_range[1])
    ]

    # Merge with station data
    merged = pd.merge(filtered_df, station_df, left_on="MonitoringLocationIdentifier", right_on="MonitoringLocationIdentifier", how="inner")

    st.subheader("🗺️ Map of Stations Within Range")
    if merged.empty:
        st.warning("No matching stations found in this range.")
    else:
        # Create folium map
        avg_lat = merged["LatitudeMeasure"].mean()
        avg_lon = merged["LongitudeMeasure"].mean()
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=7)
        marker_cluster = MarkerCluster().add_to(m)

        for _, row in merged.iterrows():
            popup_text = f"<b>{row['MonitoringLocationName']}</b><br>{selected_contaminant}: {row['ResultMeasureValue']} {row.get('ResultMeasure/MeasureUnitCode', '')}"
            folium.Marker(
                location=[row["LatitudeMeasure"], row["LongitudeMeasure"]],
                popup=popup_text
            ).add_to(marker_cluster)

        st_folium(m, width=800, height=500)

        # --- Trend Over Time ---
        st.subheader(f"📈 {selected_contaminant} Trend Over Time")
        fig, ax = plt.subplots(figsize=(10, 4))
        for site, group in merged.groupby("MonitoringLocationIdentifier"):
            ax.plot(group["ActivityStartDate"], group["ResultMeasureValue"], label=site, marker='o', linestyle='-')
        ax.set_xlabel("Date")
        ax.set_ylabel(f"{selected_contaminant} ({merged['ResultMeasure/MeasureUnitCode'].dropna().unique()[0] if not merged['ResultMeasure/MeasureUnitCode'].dropna().empty else 'units'})")
        ax.set_title(f"{selected_contaminant} Levels Over Time at Matching Stations")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title="Station")
        ax.grid(True)
        st.pyplot(fig)
