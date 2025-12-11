import solara
import geopandas as gpd
import pandas as pd
# 使用 foliumap 後端 (靜態 HTML)，解決白屏問題
import leafmap.foliumap as leafmap 
import warnings
from pathlib import Path
from typing import Tuple, Optional

# 忽略 geopandas 警告
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. 數據載入與狀態管理 ---

APP_ROOT = Path(__file__).parent.parent
GEOJSON_FILENAME = "solar_panels_final_results.geojson"
GEOJSON_PATH = Path("/code") / GEOJSON_FILENAME

# 影像瓦片 (使用 Esri World Imagery)
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

def get_initial_data():
    data = None
    if GEOJSON_PATH.exists():
        try:
            data = gpd.read_file(GEOJSON_PATH)
            if not data.empty:
                # 確保 CRS 為 WGS84
                if data.crs and data.crs.to_string() != "EPSG:4326":
                    data = data.to_crs("EPSG:4326")
        except Exception as e:
            print(f"Error reading GeoJSON: {e}")
            
    if data is None:
        data = gpd.GeoDataFrame(
            pd.DataFrame({'area_m2': []}), 
            geometry=[], 
            crs="EPSG:4326"
        )
    return data

initial_gdf = get_initial_data()
all_solar_data = solara.reactive(initial_gdf)

def calculate_filtered_data(min_area_value):
    """計算篩選後的 GeoDataFrame"""
    if all_solar_data.value.empty:
        return gpd.GeoDataFrame()
    
    try:
        filtered = all_solar_data.value[all_solar_data.value['area_m2'] >= min_area_value].copy()
        return filtered
    except Exception as e:
        print(f"Filter error: {e}")
        return all_solar_data.value

# --- 2. Leafmap 地圖元件 (使用 IFrame 渲染) ---

@solara.component
def GeoAI_MapView(current_filtered_data):
    
    # 1. 初始化地圖
    # height 必須是像素字串 (如 "600px")，這是 foliumap 的要求
    m = leafmap.Map(
        location=[23.7, 120.9], 
        zoom_start=7,
        height="600px", 
        control_scale=True
    )
    
    # 2. 加入底圖 (FIXED: 修正參數名稱)
    # 錯誤寫法: tiles=..., attr=...
    # 正確寫法: url=..., attribution=...
    m.add_tile_layer(
        url=TILE_URL, 
        attribution="Esri World Imagery", 
        name="Satellite Imagery"
    )

    # 3. 加入篩選後的光電板圖層
    if current_filtered_data is not None and not current_filtered_data.empty:
        style_function = lambda x: {
            'fillColor': '#FFD700', 
            'color': '#FF4500',     
            'weight': 2,
            'fillOpacity': 0.6
        }
        
        try:
            m.add_gdf(
                gdf=current_filtered_data,
                layer_name="Filtered Solar Panels",
                style_function=style_function,
                zoom_to_layer=True 
            )
        except Exception as e:
            print(f"Error adding GDF: {e}")
    
    # 4. 生成 HTML
    map_html = m.to_html()

    # 5. 使用 iframe 顯示
    solara.HTML(
        tag="iframe",
        attributes={
            "srcdoc": map_html,
            "style": "width: 100%; height: 610px; border: none; border-radius: 8px;"
        }
    )

# --- 3. 頁面佈局 ---

@solara.component
def Page():
    min_area_value, set_min_area = solara.use_state(10.0)
    
    current_filtered_data = calculate_filtered_data(min_area_value)
    
    total_count = len(all_solar_data.value) if all_solar_data.value is not None else 0
    filtered_count = len(current_filtered_data) if current_filtered_data is not None else 0
    
    max_area = 500.0
    if total_count > 0 and 'area_m2' in all_solar_data.value.columns:
         max_area = float(all_solar_data.value['area_m2'].max()) * 1.1

    def get_data_string():
        if current_filtered_data is not None:
            return current_filtered_data.to_json()
        return "{}"

    with solara.Column(align="stretch", style={"padding": "20px"}):
        solara.Title("GeoAI 光電板成果服務化")
        
        solara.Markdown("# 🌞 光電板 GeoAI 成果篩選器")
        solara.Markdown("---")
        
        solara.SliderFloat(
            label=f"最小光電板面積 ({filtered_count}/{total_count} 個顯示中)", 
            value=min_area_value,
            on_value=set_min_area,
            min=0.0, 
            max=max_area,
            step=10.0,
            thumb_label="always",
        )
        
        solara.Info(f"總共偵測到 **{total_count}** 個地物。目前顯示 **{filtered_count}** 個面積大於 **{min_area_value:.2f} m²** 的光電板。")
        
        solara.Markdown("## 🌐 GeoAI 成果視覺化：影像與向量")
        
        GeoAI_MapView(current_filtered_data)
        
        solara.Markdown("**提示：** 拖動滑塊即可即時篩選並自動縮放至圖資範圍。")
        
        if filtered_count > 0:
            solara.FileDownload(
                data=get_data_string, 
                filename="filtered_solar_panels.geojson",
                label=f"下載篩選後的 GeoJSON ({filtered_count} 筆)",
                icon_name="mdi-download",
            )
        else:
            solara.Button("無資料可下載", disabled=True, icon_name="mdi-download")