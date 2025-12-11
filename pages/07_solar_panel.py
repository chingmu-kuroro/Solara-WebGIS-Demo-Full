import solara
import geopandas as gpd
import pandas as pd
# FIX: 改用 foliumap 後端，它生成靜態 HTML，比 ipyleaflet 在 Web App 中更穩健，不會白屏
import leafmap.foliumap as leafmap 
import warnings
from pathlib import Path
from typing import Tuple, Optional

# 忽略 geopandas 警告
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. 數據載入與狀態管理 ---

APP_ROOT = Path(__file__).parent.parent
GEOJSON_FILENAME = "solar_panels_final_results.geojson"
# 確保路徑指向 /code/ (Hugging Face Spaces 環境)
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

# 載入初始數據
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

# --- 2. Leafmap 地圖元件 (使用 Folium + IFrame 解決白屏問題) ---

@solara.component
def GeoAI_MapView(current_filtered_data):
    
    # 每次數據改變時，重新生成地圖 HTML
    # 雖然這是全量刷新，但對於 <100 個多邊形來說速度很快，且能保證顯示
    
    # 1. 創建地圖實例 (Folium 後端)
    # location=[緯度, 經度]
    m = leafmap.Map(
        location=[23.7, 120.9], 
        zoom_start=7,
        height="100%", # 高度由 iframe 控制
        control_scale=True
    )
    
    # 2. 加入底圖
    m.add_tile_layer(
        tiles=TILE_URL, 
        attr="Esri World Imagery", 
        name="Satellite Imagery"
    )

    # 3. 加入篩選後的光電板圖層
    if current_filtered_data is not None and not current_filtered_data.empty:
        
        # 定義樣式函數
        style_function = lambda x: {
            'fillColor': '#FFD700', # 金色填充
            'color': '#FF4500',     # 橘紅色邊框
            'weight': 2,
            'fillOpacity': 0.6
        }
        
        # 加入 GeoDataFrame
        m.add_gdf(
            gdf=current_filtered_data,
            layer_name="Filtered Solar Panels",
            style_function=style_function,
            zoom_to_layer=True # Folium 後端支持自動縮放到圖層
        )
    
    # 4. 關鍵修復：將地圖轉為 HTML 字串
    map_html = m.to_html()

    # 5. 使用 iframe 渲染 HTML
    # srcdoc 屬性允許我們直接將 HTML 字串嵌入 iframe 中
    solara.HTML(
        tag="iframe",
        attributes={
            "srcdoc": map_html,
            "style": "width: 100%; height: 70vh; border: none; border-radius: 8px;"
        }
    )

# --- 3. 頁面佈局 ---

@solara.component
def Page():
    min_area_value, set_min_area = solara.use_state(10.0)
    
    # 計算篩選結果
    current_filtered_data = calculate_filtered_data(min_area_value)
    
    # 計算統計數字
    total_count = len(all_solar_data.value) if all_solar_data.value is not None else 0
    filtered_count = len(current_filtered_data) if current_filtered_data is not None else 0
    
    max_area = 500.0
    if total_count > 0 and 'area_m2' in all_solar_data.value.columns:
         max_area = float(all_solar_data.value['area_m2'].max()) * 1.1

    # 定義下載內容函數
    def get_data_string():
        if current_filtered_data is not None:
            return current_filtered_data.to_json()
        return "{}"

    with solara.Column(align="stretch", style={"padding": "20px"}):
        solara.Title("GeoAI 光電板成果服務化")
        
        solara.Markdown("# 🌞 光電板 GeoAI 成果篩選器")
        solara.Markdown("---")
        
        # 滑塊
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
        
        # 呼叫地圖元件 (已改為 IFrame 渲染)
        GeoAI_MapView(current_filtered_data)
        
        solara.Markdown("**提示：** 拖動滑塊即可即時篩選並自動縮放至圖資範圍。")
        
        # 下載按鈕
        if filtered_count > 0:
            solara.FileDownload(
                data=get_data_string, 
                filename="filtered_solar_panels.geojson",
                label=f"下載篩選後的 GeoJSON ({filtered_count} 筆)",
                icon_name="mdi-download",
            )
        else:
            solara.Button("無資料可下載", disabled=True, icon_name="mdi-download")