import solara
import geopandas as gpd
import pandas as pd
# 修正: 改為使用 leafmap.leafmap 以啟用 SplitMap 功能 (通常基於 ipyleaflet 或 folium)
import leafmap.leafmap as leafmap
import warnings
import os
from pathlib import Path
from typing import Tuple, List, Optional, Any
# 引入 ipyleaflet 相關元件，以便更精確地控制圖層
import ipyleaflet

# 忽略 geopandas/shapely 相關的未來警告
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. 數據載入與狀態管理 (全域/模組級) ---

# 假設這是您的 GeoAI 推論成果檔案 (已包含 'area_m2' 屬性)
# CRITICAL FIX: 在 Hugging Face Spaces 中，靜態檔案通常直接位於根目錄 /code/。
# 移除 .parent.parent，直接嘗試從當前執行目錄尋找，或確保檔案位於 /code/
# 由於檔案在 pages/05_solar_panel.py，根目錄在上一級。
APP_ROOT = Path(__file__).parent.parent
GEOJSON_FILENAME = "solar_panels_final_results.geojson"
# 修正: 確保在 /code/ 根目錄下能夠找到檔案
# 注意：Hugging Face Spaces 運行環境的工作目錄在 /code/，因此路徑應該是 /code/filename
GEOJSON_PATH = Path("/code") / GEOJSON_FILENAME

# 由於 TIFF 檔案太大，我們將使用 Web 服務瓦片來代表左側的原始影像。
ORIGINAL_IMAGE_URL = "https://huggingface.co/datasets/giswqs/geospatial/resolve/main/solar_panels_davis_ca.tif"
ORIGINAL_IMAGE_PATH = APP_ROOT / "original_image.tif" # 僅作為占位符

# 定義一個類型別名，用於邊界框 (minx, miny, maxx, maxy)
BboxType = Tuple[float, float, float, float]

# 檢查檔案是否存在，如果不存在則創建空的 GeoDataFrame 作為 fallback
def get_initial_data() -> Tuple[gpd.GeoDataFrame, Optional[List[List[float]]]]:
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
                # Leafmap (ipyleaflet) 需要 [[miny, minx], [maxy, maxx]] 的格式
                minx, miny, maxx, maxy = data.total_bounds
                bbox = [[miny, minx], [maxy, maxx]] 
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
# 修正: 初始化時調用 get_initial_data() 獲取數據和 BBOX
initial_gdf, initial_bbox = get_initial_data()
all_solar_data = solara.reactive(initial_gdf)
# 新增: 用於儲存地圖初始化邊界框的響應式狀態
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
def GeoAI_SplitMap(current_filtered_data, initial_bounds):
    
    # 1. 創建 Leafmap 實例 (使用 solara.use_memo 確保只運行一次)
    def create_split_map():
        # 預設中心點 (如果沒有 GeoJSON 數據則使用台灣中心點)
        default_center = [23.7, 120.9] 
        m = leafmap.Map(
            center=default_center, 
            zoom=10, 
            # 關鍵修正：將 controls 設置為空列表，以避免 Leafmap 嘗試初始化衝突的控制項
            controls=[] 
        )
        m.layout.height = "70vh"
        
        # 關鍵修復：手動添加 SplitMap 所需的圖層，並移除 Leafmap 默認加載的圖層
        # 由於我們將 controls=[]，地圖應該是空的，但為保險起見，我們繼續移除
        if len(m.layers) > 0 and isinstance(m.layers[0], ipyleaflet.TileLayer):
             m.remove_layer(m.layers[0])
        
        # 添加 SplitMap 的兩個底圖
        # 左側：原始影像 (使用 Esri 影像代表高解析度底圖)
        m.add_basemap("Esri World Imagery", name="原始影像 (左)", left=True) 
        # 右側：簡潔地圖，用於顯示 GeoJSON 成果
        m.add_basemap("CartoDB Positron", name="篩選結果 (右)", right=True)
        
        # 修正: 如果有邊界框數據，則將地圖視圖縮放至 GeoJSON 範圍
        if initial_bounds:
            # Leafmap 的 fit_bounds 接受 [[miny, minx], [maxy, maxx]] 格式
            m.fit_bounds(initial_bounds) 
            
        return m
        
    m = solara.use_memo(create_split_map, dependencies=[])
    
    # 2. 響應式效果: 當篩選數據改變時，更新地圖右側的 GeoJSON 圖層
    solara.use_effect(
        lambda: update_map_layer(m, current_filtered_data), 
        dependencies=[current_filtered_data]
    )
    
    # 3. 處理地圖更新邏輯
    def update_map_layer(map_instance, gdf):
        if map_instance is None:
            return
        
        # 定義圖層名稱
        LAYER_NAME = "GeoAI_Filtered_Solar_Panels"
        
        # 移除舊圖層 (無論是否篩選出結果)
        try:
            # 確保移除的是右側圖層
            map_instance.remove_layer(LAYER_NAME, right=True) 
        except Exception:
            pass

        # 如果有篩選結果，則加入新圖層
        if gdf is not None and not gdf.empty:
            
            # 使用 Leafmap 的 add_gdf 方法加入向量數據到右側圖台
            map_instance.add_gdf(
                gdf, 
                layer_name=LAYER_NAME, 
                right=True, # 確保圖層只出現在右側圖台
                style_function={
                    "fillColor": "#FFD700", # 金色填充
                    "color": "#FF4500",      # 橘紅色邊框
                    "weight": 1.5,
                    "fillOpacity": 0.6
                }
            )

    # 修正: 使用 solara.display() 橋接 Leafmap (IPython Widget)
    return solara.display(m)

# --- 3. 應用程式頁面佈局 ---

@solara.component
def Page():
    # 修正: 使用 solara.use_state 解構，將狀態值和設定器分開。
    min_area_value, set_min_area = solara.use_state(100.0)
    
    # FINAL FIX: 在元件內部使用 solara.use_memo 鉤子來記憶化計算結果。
    # 修正: 將 min_area.value 修正為 min_area_value
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
        
        solara.Markdown("## 🌐 對比圖台：左側 (原始影像) vs 右側 (篩選結果)")
        
        # 對比地圖元件：將篩選後的數據傳遞給地圖元件，並傳遞初始化邊界
        GeoAI_SplitMap(current_filtered_data, map_bounds.value)
        
        solara.Markdown(
            """
            **提示：**
            * 左側圖台：顯示原始衛星影像 (Web Tiles)，右側圖台：顯示 GeoAI 推論後的 GeoJSON 成果，並啟用分割捲簾。
            * 拖動滑塊即可即時篩選和更新右側圖層，體驗空間數據的互動式分析。
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