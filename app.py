import streamlit as st
import geopandas as gpd
import leafmap.foliumap as leafmap
import plotly.express as px
import os

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="UBEM Platform")

# 2. Configuration & Constants
ID_LINK = "ID" 
METRICS_MAPPING = {
    "Total Energy Consumption (kWh)": "Total_Energy_kWh",
    "Cooling Energy (kWh)": "Cooling_Energy_kWh",
    "Lighting Energy (kWh)": "Lighting_kWh",
    "Equipment Energy (kWh)": "Equipment_kWh",
    "Total EUI": "EUI_Gross_kWh_m2",
    "Cooling EUI": "EUI_Cooling_kWh_m2",
}

# 3. Data Loading
@st.cache_data
def load_data():
    path = "processed/buildings_final.gpkg"
    if not os.path.exists(path):
        return None
    gdf = gpd.read_file(path)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    return gdf

gdf = load_data()

if gdf is not None:
    st.title("🏙️ NUS Kent Ridge Campus: Building Energy Dashboard")

    # --- SIDEBAR: Archetype Filter ---
    st.sidebar.header("Select Building Archetypes")
    
    raw_types = gdf['Archetype'].unique()
    unique_archetypes = sorted([str(t) for t in raw_types if t is not None and str(t).lower() != 'nan'])
    
    if 'selected_types' not in st.session_state:
        st.session_state.selected_types = unique_archetypes

    if st.sidebar.button("Select/Deselect All"):
        if len(st.session_state.selected_types) > 0:
            st.session_state.selected_types = []
        else:
            st.session_state.selected_types = unique_archetypes

    selected_archetypes = st.sidebar.multiselect(
        "Filter by Archetype",
        options=unique_archetypes,
        key='selected_types'
    )

    display_name = st.sidebar.selectbox("Select Annual Energy Metric", list(METRICS_MAPPING.keys()))
    target_column = METRICS_MAPPING[display_name]

    # Apply Filter
    filtered_gdf = gdf[gdf['Archetype'].astype(str).isin(selected_archetypes)]

    # --- MAIN LAYOUT ---
    col_left, col_right = st.columns([1, 2]) # Adjusted ratio for better look

        # --- LEFT PANEL: Dynamic Ranking (Top 5 Left-to-Right) ---
    with col_left:
        st.subheader(f"📊 Top 5 buildings: {display_name}")
        if not filtered_gdf.empty:
            # 1. Get Top 5 sorted by value
            top_5 = filtered_gdf.nlargest(5, target_column)[[ID_LINK, 'Name_2', target_column]]
            
            # 2. Vertical Bar Chart (Left-to-Right)
            fig_top = px.bar(
                top_5, 
                x=ID_LINK,            # Show ID on the X-axis for brevity
                y=target_column,      
                hover_data=['Name_2'], # Show Name_2 when hovering over bars
                color=target_column,
                color_continuous_scale="Reds",
                text_auto='.1f',      
                labels={target_column: "kWh/m²", ID_LINK: "Building ID"}
            )
            
            fig_top.update_layout(
                xaxis={'categoryorder':'total descending'}, 
                showlegend=False, 
                height=350,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig_top, use_container_width=True)
            
            # 3. Leaderboard List: ID with Name_2 as description
            st.markdown("**Building Details:**")
            for i, row in enumerate(top_5.itertuples()):
                # Format: #1 ID (Name_2): Value
                st.write(f"**#{i+1}** {getattr(row, ID_LINK)}")
        else:
            st.warning("No data found for current filters.")


    # --- RIGHT PANEL: Map and Details ---
    with col_right:
        tab_map, tab_detail = st.tabs(["🗺️ Campus Map", "🔍 Building Detail"])
        
        with tab_map:
            st.subheader("Building Energy Map")
            center_y = filtered_gdf.geometry.centroid.y.mean() if not filtered_gdf.empty else gdf.geometry.centroid.y.mean()
            center_x = filtered_gdf.geometry.centroid.x.mean() if not filtered_gdf.empty else gdf.geometry.centroid.x.mean()
            
            m = leafmap.Map(center=[center_y, center_x], zoom=17)
            
            if not filtered_gdf.empty:
                m.add_data(
                    filtered_gdf,
                    column=target_column,
                    scheme="Quantiles",
                    cmap="YlOrRd",
                    legend_title="kWh/m²"
                )
               
            m.to_streamlit(height=600)

        with tab_detail:
            if not filtered_gdf.empty:
                search_id = st.selectbox("Search/Select Building ID", filtered_gdf[ID_LINK].unique())
                
                # FIX: Added .iloc[0] to correctly select the single row
                bldg = filtered_gdf[filtered_gdf[ID_LINK] == search_id].iloc[0]

                d1, d2 = st.columns(2)
                with d1:
                     st.info(f"**Description:** {bldg['Name_2']}\n\n**Archetype:** {bldg['Archetype']}")
                     
                     # Using a clean list format
                     st.write("### Energy Performance")
                     st.write(f"📊 **Total Energy:** `{bldg['Total_Energy_kWh']:.0f} kWh`")
                     st.write(f"❄️ **Cooling:** `{bldg['Cooling_Energy_kWh']:.0f} kWh`")
                     st.write(f"💡 **Lighting:** `{bldg['Lighting_kWh']:.0f} kWh`")
                     st.write(f"🔌 **Equipment:** `{bldg['Equipment_kWh']:.0f} kWh`")
                     st.write(f"🔥 **Hot Water:** `{bldg['Hot_Water_kWh']:.0f} kWh`")
                     st.markdown("---")
                     st.write(f"🏠 **Gross EUI:** {bldg['EUI_Gross_kWh_m2']:.0f} kWh/m²`")
                     st.write(f"❄️ **Cooling EUI:** `{bldg['EUI_Cooling_kWh_m2']:.0f} kWh/m²`")
                     st.write(f"💡 **Lighting EUI:** `{bldg['EUI_Lighting_kWh_m2']:.0f} kWh/m²`")
                     st.write(f"🔌 **Equipment EUI:** `{bldg['EUI_Equipment_kWh_m2']:.0f} kWh/m²`")
                     st.write(f"🔥 **Hot Water EUI:** `{bldg['EUI_Hot_Water_kWh_m2']:.0f} kWh/m²`")

                with d2:
                    breakdown = {
                        "Type": ["Cooling", "Lighting", "Equipment", "Hot Water"],
                        "Value": [
                            bldg.get('Cooling_Energy_kWh', 0), 
                            bldg.get('Lighting_kWh', 0), 
                            bldg.get('Equipment_kWh', 0), 
                            bldg.get('Hot_Water_kWh', 0)
                        ]
                    }
                    fig_pie = px.pie(breakdown, values='Value', names='Type', hole=0.4, 
                                     color_discrete_sequence=px.colors.qualitative.Set3)
                    fig_pie.update_layout(height=300, margin=dict(l=0, r=0, b=0, t=30))
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("Please select at least one Archetype from the sidebar.")

    # --- RAW DATA TABLE ---
    st.markdown("---")
    with st.expander("📂 View Filtered Attribute Table"):
        # Dropping geometry column for display to avoid errors
        table_df = filtered_gdf.drop(columns='geometry')
        st.dataframe(table_df, use_container_width=True)

else:
    st.info("Check 'processed/buildings_final.gpkg'. Run 'scripts/data_merge.py' if missing.")
