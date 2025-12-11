import solara
import geopandas as gpd
import pandas as pd
# FIX 1: 改回標準 leafmap (基於 ipyleaflet)，這是 Solara 中最穩定、不會白屏的後端
import leafmap 
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

# 影像瓦片 (使用 Esri World Imagery 替代 NAIP，覆蓋全球且穩定)
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

BboxType = Tuple[float, float, float, float] 

def get_initial_data() -> Tuple[gpd.GeoDataFrame, Optional[BboxType]]:
    data = None
    bbox = None
    if GEOJSON_PATH.exists():
        try:
            data = gpd.read_file(GEOJSON_PATH)
            if not data.empty:
                # 轉換為 EPSG:4326 以確保地圖疊加正確
                if data.crs and data.crs.to_string() != "EPSG:4326":
                    data = data.to_crs("EPSG:4326")
                bbox = tuple(data.total_bounds)
        except Exception as e:
            print(f"Error reading GeoJSON: {e}")
            
    if data is None:
        print(f"Warning: {GEOJSON_PATH} not found. Using empty data.")
        data = gpd.GeoDataFrame(
            pd.DataFrame({'area_m2': []}), 
            geometry=[], 
            crs="EPSG:4326"
        )
    return data, bbox

initial_gdf, initial_bbox = get_initial_data()
all_solar_data = solara.reactive(initial_gdf)
map_bounds = solara.reactive(initial_bbox)

def calculate_filtered_data(min_area_value):
    """計算篩選後的 GeoDataFrame"""
    if all_solar_data.value.empty:
        return gpd.GeoDataFrame()
    
    try:
        # 篩選資料
        filtered = all_solar_data.value[all_solar_data.value['area_m2'] >= min_area_value].copy()
        return filtered
    except Exception as e:
        print(f"Filter error: {e}")
        return all_solar_data.value

# --- 2. Leafmap 地圖元件 (核心修復) ---

@solara.component
def GeoAI_MapView(current_filtered_data, initial_bounds):
    
    # FIX 2: 建立地圖實例
    # 使用標準 leafmap (ipyleaflet)，它是原生的 Widget，不需要 to_solara()
    def create_map_instance():
        m = leafmap.Map(
            center=[23.7, 120.9], 
            zoom=7,
            draw_control=False,
            measure_control=False,
            height="70vh" # 設定高度
        )
        # 加入底圖
        m.add_tile_layer(url=TILE_URL, name="Satellite Imagery", attribution="Esri")
        return m

    # 只在初始化時建立一次地圖
    m = solara.use_memo(create_map_instance, dependencies=[]) 

    # FIX 3: 使用 use_effect 處理圖層更新與縮放
    def update_map():
        if m is None: return
        
        # 清除舊的 GeoJSON 圖層 (名稱必須對應)
        layer_name = "Filtered Solar Panels"
        existing_layer = m.find_layer(layer_name)
        if existing_layer:
            m.remove_layer(existing_layer)

        # 如果有資料，加入新圖層
        if current_filtered_data is not None and not current_filtered_data.empty:
            # 定義樣式 (Standard ipyleaflet style dict)
            style = {
                "stroke": True,
                "color": "#FF4500",  # 橘紅色邊框
                "weight": 2,
                "opacity": 1,
                "fill": True,
                "fillColor": "#FFD700", # 金色填充
                "fillOpacity": 0.6,
            }
            
            # 加入 GeoJSON
            m.add_gdf(
                current_filtered_data, 
                layer_name=layer_name,
                style=style,
                hover_style={"fillOpacity": 0.8, "color": "#FFF"}
            )
            
            # 自動縮放到資料範圍
            # 注意: 這裡使用 bounds 檢查避免縮放到空數據導致錯誤
            try:
                minx, miny, maxx, maxy = current_filtered_data.total_bounds
                # ipyleaflet 格式: [[south, west], [north, east]]
                m.fit_bounds([[miny, minx], [maxy, maxx]])
            except:
                pass

    solara.use_effect(update_map, dependencies=[current_filtered_data])

    # FIX 4: 直接回傳地圖物件 m (它是 ipywidget)，不要呼叫 .to_solara()
    return m

# --- 3. 頁面佈局 ---

@solara.component
def Page():
    min_area_value, set_min_area = solara.use_state(10.0)
    
    current_filtered_data = solara.use_memo(
        lambda: calculate_filtered_data(min_area_value), 
        dependencies=[min_area_value]
    )
    
    total_count = len(all_solar_data.value) if all_solar_data.value is not None else 0
    filtered_count = len(current_filtered_data) if current_filtered_data is not None else 0
    
    max_area = 500.0
    if total_count > 0 and 'area_m2' in all_solar_data.value.columns:
         max_area = float(all_solar_data.value['area_m2'].max()) * 1.1

    # 定義下載內容
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
        
        # 呼叫地圖元件
        GeoAI_MapView(current_filtered_data, map_bounds.value)
        
        solara.Markdown("**提示：** 拖動滑塊即可即時篩選並自動縮放至圖資範圍。")
        
        # FIX 5: 使用 solara.FileDownload 元件替代 Button+lambda
        # 這是 Solara 處理文件下載的正確方式
        if filtered_count > 0:
            solara.FileDownload(
                data=get_data_string, # 傳遞函數或字串
                filename="filtered_solar_panels.geojson",
                label=f"下載篩選後的 GeoJSON ({filtered_count} 筆)",
                icon_name="mdi-download", # 使用 mdi icon
            )
        else:
            solara.Button("無資料可下載", disabled=True, icon_name="mdi-download")