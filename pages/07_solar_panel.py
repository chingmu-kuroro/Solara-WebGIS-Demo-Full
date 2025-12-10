import solara
import geopandas as gpd
import pandas as pd
# CRITICAL FIX: 切換到 leafmap.maplibregl 後端 (更穩定且支持 to_solara)
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
# 遠端瓦片服務 URL (示例：從 GeoTIFF 轉換而來的 XYZ 瓦片服務 URL)
# 註解: 由於 Leafmap 不直接接受 GeoTIFF URL，我們使用 USGS NAIP 瓦片來代表高解析度影像
NAIP_TILE_URL = "https://server.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


# 定義一個類型別名，用於邊界框 (minx, miny, maxx, maxy)
# 注意：這裡的 Bbox 仍然是 (minx, miny, maxx, maxy) 格式的 Tuple
BboxType = Tuple[float, float, float, float] 

# 檢查檔案是否存在，如果不存在則創建空的 GeoDataFrame 作為 fallback
def get_initial_data() -> Tuple[gpd.GeoDataFrame, Optional[BboxType]]:
    """載入 GeoJSON 數據，並返回 GeoDataFrame 和其邊界框 (bbox)。"""
    data = None
    bbox = None
    # 這裡 GEOJSON_PATH 應該是 /code/solar_panels_final_results.geojson
    if GEOJSON_PATH.exists():
        try:
            # 使用 Path 物件讀取檔案
            data = gpd.read_file(GEOJSON_PATH)
            # 成功讀取後計算邊界框 (minx, miny, maxx, maxy)
            if not data.empty:
                # CRITICAL FIX: 確保我們導出的是 [minx, miny, maxx, maxy] 格式的 Tuple，
                # 以便與 zoom_to_extent(*bounds) 兼容
                minx, miny, maxx, maxy = data.total_bounds
                bbox = (minx, miny, maxx, maxy)
        except Exception as e:
            # 讀取失敗，data 仍為 None
            print(f"Error reading GeoJSON at {GEOJSON_PATH}: {e}")
            
    # 邏輯修正: 只有在 data 為 None (檔案不存在或讀取失敗) 時，才使用空的 GeoDataFrame
    if data is None: # None指的是無物件，沒有任何東西
        # 警告會讓使用者確認檔案未找到
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
# 新增: 用於儲存地圖初始化邊界框的響應式狀態 (使用 maplibregl 格式)
map_bounds = solara.reactive(initial_bbox)


# FINAL FIX: 移除 @solara.use_memo 裝飾器，使 filtered_data 成為一個普通的輔助函式。
# 這樣在模組載入時就不會報錯 "No render context"。
def calculate_filtered_data(min_area_value):
    # 由於 get_initial_data() 確保了 GeoDataFrame 實例總會被返回，
    # 這裡只需要檢查 GeoDataFrame 是否為空即可。
    if all_solar_data.value.empty: # empty指的是有物件，但為空，沒有任何資料
        return gpd.GeoDataFrame()  # 若總數據為空 (Empty GeoJSON)，快速返回空結果，跳過 try/except。
    
    # 執行篩選 (area_m2 >= min_area)
    try:
        # 確保 'area_m2' 欄位存在且是數值類型
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
    
    # 1. 創建 Leafmap 實例 (使用 solara.use_memo 確保只運行一次)
    def create_map_instance():
        # 預設中心點 (如果沒有 GeoJSON 數據則使用台灣中心點)
        default_center = [120.9, 23.7] # maplibregl 使用 [lon, lat]
        m = leafmap.Map(
            center=default_center, 
            zoom=5, # 初始縮放較小
            style="satellite", # 使用 maplibregl 內建的影像底圖
        )
        m.layout.height = "70vh"
        return m
        
    m = solara.use_memo(create_map_instance, dependencies=[])
    
    # 2. CRITICAL FIX: 整合所有圖層操作和 fit_bounds 到一個 effect 中
    # 這個 effect 確保在組件掛載 (dependencies=[]) 和數據改變 (current_filtered_data) 時都更新地圖
    solara.use_effect(
        lambda: update_map_layer_and_view(m, current_filtered_data, initial_bounds), 
        dependencies=[current_filtered_data, initial_bounds]
    )

    # 3. 處理 GeoJSON 疊加和視圖縮放 (所有操作都應在 map_instance 準備好後執行)
    def update_map_layer_and_view(map_instance, gdf, bounds):
        if map_instance is None:
            return
        
        # 3a. 設置/重設底圖和瓦片圖層 (底圖已在 Map 構造函數中設置為 'satellite')
        
        # 3b. 疊加 GeoJSON (篩選後的結果)
        LAYER_NAME = "GeoAI_Filtered_Solar_Panels"

        # 移除舊的 GeoJSON 圖層 (如果存在)
        try:
             # 移除舊 GeoJSON 數據源和圖層
             map_instance.remove_layer(LAYER_NAME)
        except Exception:
             pass
        
        if gdf is not None and not gdf.empty:
            # CRITICAL FIX: 移除所有不兼容的 Layer 參數，只傳遞 GeoJSON 數據本身。
            map_instance.add_geojson(
                gdf.__geo_interface__, # 將 GeoDataFrame 轉換為 GeoJSON 字典
                # 移除 layer_id 參數，解決 Pydantic 錯誤。
            )

        # 3c. 執行 fit_bounds (最後執行以確保正確縮放)
        if bounds:
            # 修正: 使用 zoom_to_extent，這在 MapLibre 後端更可靠，且直接接受 Bbox Tuple/List
            # 格式: zoom_to_extent(minx, miny, maxx, maxy)
            map_instance.zoom_to_extent(*bounds) 
    
    # 修正: maplibregl 後端必須使用 to_solara()
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