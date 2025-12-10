import solara
import geopandas as gpd
import pandas as pd
# 引入 geoai 套件 (用於使用其互動式視覺化API)
import geoai 
# CRITICAL FIX: 切換到 leafmap.maplibregl 後端
import leafmap.maplibregl as leafmap 
import warnings
import os
from pathlib import Path
from typing import Tuple, List, Optional, Any
# 移除 ipyleaflet 相關元件，因為 maplibregl 不使用它們
# import ipyleaflet 

# 忽略 geopandas/shapely 相關的未來警告
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. 數據載入與狀態管理 (全域/模組級) ---

# 假設這是您的 GeoAI 推論成果檔案 (已包含 'area_m2' 的屬性)
# CRITICAL FIX: 在 Hugging Face Spaces 中，靜態檔案通常直接位於根目錄 /code/。
APP_ROOT = Path(__file__).parent.parent
GEOJSON_FILENAME = "solar_panels_final_results.geojson"
# 修正: 確保在 /code/ 根目錄下能夠找到檔案
GEOJSON_PATH = Path("/code") / GEOJSON_FILENAME

# 由於 TIFF 檔案太大，我們將使用 Web 服務瓦片來代表原始影像。
# 註解: 由於 Leafmap 不直接接受 GeoTIFF URL，我們使用 USGS NAIP 瓦片來代表高解析度影像
NAIP_TILE_URL = "https://server.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


# 定義一個類型別名，用於邊界框 (minx, miny, maxx, maxy)
BboxType = Tuple[float, float, float, float] 

# 檢查檔案是否存在，如果不存在則創建空的 GeoDataFrame 作為 fallback
def get_initial_data() -> Tuple[gpd.GeoDataFrame, Optional[BboxType]]:
    """載入 GeoJSON 數據，並返回 GeoDataFrame 和其邊界框 (bbox)。"""
    data = None
    bbox = None
    if GEOJSON_PATH.exists():
        try:
            # 使用 Path 物件讀取檔案
            data = gpd.read_file(GEOJSON_PATH)
            if not data.empty:
                minx, miny, maxx, maxy = data.total_bounds
                bbox = (minx, miny, maxx, maxy)
        except Exception as e:
            # 讀取失敗，data 仍為 None
            print(f"Error reading GeoJSON at {GEOJSON_PATH}: {e}")
            
    # 邏輯修正: 只有在 data 為 None (檔案不存在或讀取失敗) 時，才使用空的 GeoDataFrame
    if data is None: 
        print(f"Warning: {GEOJSON_PATH} not found or corrupted. Using empty data.")
        data = gpd.GeoDataFrame(
            pd.DataFrame({'area_m2': []}), 
            geometry=[], 
            crs="EPSG:4326"
        )
    
    return data, bbox

# 核心狀態: 儲存所有 GeoAI 結果 (GeoDataFrame) 和 BBOX。
initial_gdf, initial_bbox = get_initial_data()
all_solar_data = solara.reactive(initial_gdf)
map_bounds = solara.reactive(initial_bbox)


def calculate_filtered_data(min_area_value):
    # 這裡只需要檢查 GeoDataFrame 是否為空即可。
    if all_solar_data.value.empty: 
        return gpd.GeoDataFrame()
    
    # 執行篩選 (area_m2 >= min_area)
    try:
        return all_solar_data.value[all_solar_data.value['area_m2'] >= min_area_value]
    except KeyError:
        print("Error: 'area_m2' column not found in GeoJSON. Cannot filter.")
        return all_solar_data.value
    except Exception as e:
        print(f"Error during filtering: {e}")
        return all_solar_data.value

# --- 2. Leafmap 地圖元件 ---

@solara.component
def GeoAI_MapView(current_filtered_data, initial_bounds): # 修正函式名稱
    
    # 1. 創建地圖實例：由於我們要使用 geoai.view_vector_interactive，Map 實例創建邏輯將被簡化
    def create_map_and_load_data():
        if current_filtered_data.empty:
            # 如果數據為空，則返回一個基礎 Map 實例
            m = leafmap.Map(center=[120.9, 23.7], zoom=5, style="satellite")
            m.layout.height = "70vh"
            return m
            
        # CRITICAL FIX: 使用 geoai.view_vector_interactive 進行一鍵疊加和縮放
        # 該函式會返回一個已經配置好 GeoJSON 和 Tiles 的 Leafmap 實例
        # 注意: 這裡我們使用 NAIP_TILE_URL 作為原始影像的代表
        m = geoai.view_vector_interactive(
            current_filtered_data, 
            tiles=NAIP_TILE_URL,
            # 確保 Leafmap 使用 MapLibre GL 後端所需的 to_solara() 屬性
            backend="maplibregl" 
        )
        m.layout.height = "70vh"
        
        # 由於 geoai.view_vector_interactive 會自動縮放，我們不需要手動 set_center 或 fit_bounds
        return m
        
    # 2. 使用 solara.use_memo 來創建地圖，並將 filtered_data 作為依賴
    # 當 filtered_data 改變時，會重建地圖實例 (這是 Leafmap/Solara 響應式圖層更新的最佳方式)
    m = solara.use_memo(
        create_map_and_load_data, 
        dependencies=[current_filtered_data] # 數據改變時，強制重新生成地圖
    )
    
    # 3. 由於縮放和圖層疊加已經在 create_map_and_load_data 內部完成，
    # 這裡只需要將地圖實例轉換為 Solara 元件
    
    return m.to_solara() 


# --- 4. 應用程式頁面佈局 ---

@solara.component
def Page():
    # 修正: 使用 solara.use_state 解構，將狀態值和設定器分開。
    min_area_value, set_min_area = solara.use_state(10.0)
    
    # FINAL FIX: 在元件內部使用 solara.use_memo 鉤子來記憶化計算結果。
    current_filtered_data = solara.use_memo(
        lambda: calculate_filtered_data(min_area_value), 
        dependencies=[min_area_value]
    )
    
    # 獲取總數據量
    total_count = len(all_solar_data.value) if all_solar_data.value is not None else 0
    filtered_count = len(current_filtered_data) if current_filtered_data is not None else 0
    
    # 確保最大值不會超過實際數據中的最大面積
    max_area = 500.0
    if total_count > 0 and 'area_m2' in all_solar_data.value.columns:
         max_area = all_solar_data.value['area_m2'].max() * 1.1 
         # 取最大值的 110%，這是刻意為之，目的是為 Solara UI 的 SliderFloat 元件提供一個視覺上的安全上限和操作緩衝區，而非為了數據計算。
         
    
    # 使用上下文管理器 (with) 來定義 Column 佈局，這在 Solara 中是更簡潔的推薦寫法。
    with solara.Column(align="stretch", style={"padding": "20px"}):
        solara.Title("GeoAI 光電板成果服務化") # 瀏覽器 Tab 標題
        
        solara.Markdown("# 🌞 光電板 GeoAI 成果篩選器")
        solara.Markdown("---")
        
        # 滑塊控制元件
        # 修正: 傳遞 value=狀態值 和 on_value=設定器，避免將 setter 函數包裝在 value 屬性中。
        solara.SliderFloat(
            label=f"最小光電板面積 ({filtered_count}/{total_count} 個顯示中)", 
            value=min_area_value,       # 傳遞值
            on_value=set_min_area,      # 傳遞設定器
            min=0.0, 
            max=max_area,
            step=10.0,
            thumb_label="always",
        )
        
        # 統計資訊
        # 修正: 使用 min_area_value
        solara.Info(f"總共偵測到 **{total_count}** 個地物。目前顯示 **{filtered_count}** 個面積大於 **{min_area_value:.2f} m²** 的光電板。")
        
        # 修正文字
        solara.Markdown("## 🌐 GeoAI 成果視覺化：影像與向量")
        
        # 修正元件名稱
        GeoAI_MapView(current_filtered_data, map_bounds.value)
        
        solara.Markdown(
            """
            **提示：**
            * **單一地圖模式：** 地圖已設定為高解析度影像底圖，並直接疊加 GeoJSON 成果，圖幅已自動縮放至數據範圍。
            * 拖動滑塊即可即時篩選和更新地圖圖層，體驗空間數據的互動式分析。
            """
        )
        
        # 數據下載按鈕 (作為 GeoAI 成果服務化的最終步驟)
        # 修正: 將 icon="download" 替換為 icon_name="download"
        solara.Button(
            "下載篩選後的 GeoJSON",
            # Solara 的下載功能 (需確保數據不為空)
            on_click=lambda: solara.file_download(
                current_filtered_data.to_json(),
                filename="filtered_solar_panels.geojson",
                mime_type="application/json"
            ),
            disabled=filtered_count == 0,
            icon_name="download"
        )