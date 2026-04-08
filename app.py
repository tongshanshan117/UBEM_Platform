import streamlit as st
import geopandas as gpd
import leafmap.foliumap as leafmap
import plotly.express as px
import pandas as pd
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
    st.title("🏙️ NUS Campus: Building Energy Dashboard")

    # --- SIDEBAR: Archetype Filter ---
    st.sidebar.header("Select Building Archetypes")
    raw_types = gdf['Archetype'].unique()
    unique_archetypes = sorted([str(t) for t in raw_types if t is not None and str(t).lower() != 'nan'])
    
    if 'selected_types' not in st.session_state:
        st.session_state.selected_types = unique_archetypes

    if st.sidebar.button("Select/Deselect All"):
        st.session_state.selected_types = [] if len(st.session_state.selected_types) > 0 else unique_archetypes

    selected_archetypes = st.sidebar.multiselect("Filter by Archetype", options=unique_archetypes, key='selected_types')
    display_name = st.sidebar.selectbox("Select Annual Energy Metric", list(METRICS_MAPPING.keys()))
    target_column = METRICS_MAPPING[display_name]

    filtered_gdf = gdf[gdf['Archetype'].astype(str).isin(selected_archetypes)]

    # --- MAIN LAYOUT ---
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader(f"📊 Top 5 buildings: {display_name}")
        if not filtered_gdf.empty:
            top_5 = filtered_gdf.nlargest(5, target_column)[[ID_LINK, 'Name_2', target_column]]
            fig_top = px.bar(
                top_5, x=ID_LINK, y=target_column, hover_data=['Name_2'], 
                color=target_column, color_continuous_scale="Reds", text_auto='.1f',
                labels={target_column: "kWh/m²", ID_LINK: "Building ID"}
            )
            fig_top.update_layout(xaxis={'categoryorder':'total descending'}, showlegend=False, height=350, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.warning("No data found.")

    with col_right:
        tab_map, tab_detail = st.tabs(["🗺️ Campus Map", "🔍 Building Details & Scenarios"])
        
        with tab_map:
            if not filtered_gdf.empty:
                center_y = filtered_gdf.geometry.centroid.y.mean()
                center_x = filtered_gdf.geometry.centroid.x.mean()
                m = leafmap.Map(center=[center_y, center_x], zoom=17)
                m.add_data(filtered_gdf, column=target_column, scheme="Quantiles", cmap="YlOrRd", legend_title="kWh/m²")
                m.to_streamlit(height=600)

        with tab_detail:
            if not filtered_gdf.empty:
                search_id = st.selectbox("Search/Select Building ID", filtered_gdf[ID_LINK].unique())
                bldg = filtered_gdf[filtered_gdf[ID_LINK] == search_id].iloc[0]

                d1, d2 = st.columns(2)
                with d1:
                    st.info(f"**Description:** {bldg['Name_2']}\n\n**Archetype:** {bldg['Archetype']}")

                    st.write("### Baseline Energy Breakdown")

                    # 1. Define your labels and values
                    labels = ["Cooling", "Lighting", "Equipment", "Hot Water"]
                    # Assuming these are the EUI values you want to show in the labels
                    eui_values = [
                        round(bldg.get('EUI_Cooling_kWh_m2', 0), 1),
                        round(bldg.get('EUI_Lighting_kWh_m2', 0), 1),
                        round(bldg.get('EUI_Equipment_kWh_m2', 0), 1),
                        round(bldg.get('EUI_Hot_Water_kWh_m2', 0), 1)
                    ]
                    
                    breakdown_data = {
                        "Type": labels,
                        "Value": [
                            bldg.get('Cooling_Energy_kWh', 0), 
                            bldg.get('Lighting_kWh', 0), 
                            bldg.get('Equipment_kWh', 0), 
                            bldg.get('Hot_Water_kWh', 0)
                        ],
                        "EUI": eui_values
                    }
                    
                    fig_pie = px.pie(
                        breakdown_data, 
                        values='Value', 
                        names='Type', 
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3,
                        custom_data=['EUI'] # This passes the EUI values to the chart
                    )
                    
                    # 2. Configure the labels to show: Name, Percentage, and EUI
                    # Force labels outside and add a small 'pull' for visibility
                    fig_pie.update_traces(
                        textposition='outside',
                        domain={'x': [0.2, 0.8], 'y': [0.2, 0.8]}, 
                        texttemplate="<b>%{label}</b><br>%{percent}<br>EUI: %{customdata:.1f} kWh/m²/yr"
                        textfont_size=11,
                        # This ensures the text isn't cut off by the container
                        insidetextorientation='horizontal' 
                    )
                    
                    fig_pie.update_layout(
                        height=380, # Increased slightly to give room for outside labels
                        margin=dict(l=10, r=10, b=10, t=10), # Added side margins so text doesn't hit the edge
                    )
                    
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                with d2:                    
                    st.write("### ❄️ Increase Cooling Setpoint")
                    scenario_csv = "FOE5_scenario_setpoints.csv"
                    
                    if os.path.exists(scenario_csv):
                        df_scen = pd.read_csv(scenario_csv)
                        df_scen.columns = df_scen.columns.str.strip() 
                        
                        potential_cols = ["Cooling EUI", "Lighting EUI", "Equipment EUI", "Hot Water EUI"]
                        available_cols = [c for c in potential_cols if c in df_scen.columns]
                        
                        scenario_order = ["Baseline", "Scenario A", "Scenario B", "Scenario C"]
                        
                        # Calculate totals and round to 1 digit
                        df_scen['Total_Stacked'] = df_scen[available_cols].sum(axis=1).round(1)
                        
                        fig_scen = px.bar(
                            df_scen, 
                            y="ScenarioID", 
                            x=available_cols,
                            orientation='h',
                            category_orders={"ScenarioID": scenario_order},
                            color_discrete_sequence=px.colors.qualitative.Pastel,
                            labels={"value": "kWh/m²", "ScenarioID": "Scenario", "variable": "End Use"}
                        )

                        # Add labels BELOW the bars
                        for _, row in df_scen.iterrows():
                            # Format: "Total EUI kWh/m² (Reduction %)"
                            reduction_text = f" ({row['Reduction']})" if 'Reduction' in df_scen.columns else ""
                            label = f"<b>{row['Total_Stacked']:.1f} kWh/m²</b>{reduction_text}"
                            
                            fig_scen.add_annotation(
                                x=row['Total_Stacked'] / 2, # Centered under the bar
                                y=row['ScenarioID'],
                                text=label,
                                showarrow=False,
                                yanchor="top",    # Anchors text top to the bar
                                yshift=-12,       # Shifts text down by 12 pixels
                                font=dict(size=11, color="#333333")
                            )

                        fig_scen.update_layout(
                            height=420, # Increased height to accommodate labels below bars
                            margin=dict(l=0, r=20, t=40, b=40), 
                            barmode='stack',
                            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig_scen, use_container_width=True)
                    else:
                        st.info("Scenario data file not found.")
    st.markdown("---")
    with st.expander("📂 View Filtered Attribute Table"):
        st.dataframe(filtered_gdf.drop(columns='geometry'), use_container_width=True)

else:
    st.info("Check 'processed/buildings_final.gpkg'.")
