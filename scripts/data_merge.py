import geopandas as gpd
import pandas as pd
import os

# ================= CONFIGURATION =================
SHP_NAME = "MasterFile_241127.shp"  # Replace with your filename
CSV_NAME = "annual_energy_data.csv"         # Replace with your filename
ID_LINK = "ID"                   # Common ID column name
# =================================================

def main():
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shp_path = os.path.join(base_dir, "data/raw_shp", SHP_NAME)
    csv_path = os.path.join(base_dir, "data", CSV_NAME)
    output_dir = os.path.join(base_dir, "processed")
    output_file = os.path.join(output_dir, "buildings_final.gpkg")

    os.makedirs(output_dir, exist_ok=True)

    print("🚀 Loading Geographic Data (Shapefile)...")
    try:
        gdf = gpd.read_file(shp_path)
        print("🚀 Loading Energy Performance Data (CSV)...")
        df = pd.read_csv(csv_path)

        print(f"🔗 Merging datasets based on [{ID_LINK}]...")
        merged = gdf.merge(df, on=ID_LINK, how='left')

        print("🌍 Transforming Coordinate Reference System to EPSG:4326 (WGS84)...")
        if merged.crs is not None:
            merged = merged.to_crs(epsg=4326)
        else:
            print("⚠️ Warning: No CRS found in source. Please check projection.")

        print(f"💾 Saving merged database to {output_file}...")
        merged.to_file(output_file, driver="GPKG")
        
        print("\n" + "="*40)
        print(f"✅ DATA MERGE SUCCESSFUL!")
        print(f"Total Buildings Processed: {len(merged)}")
        print("="*40)

    except Exception as e:
        print(f"❌ Error during execution: {e}")

if __name__ == "__main__":
    main()
