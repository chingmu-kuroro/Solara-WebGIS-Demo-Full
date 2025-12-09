import solara
import geopandas as gpd
import pandas as pd
# 使用 leafmap.leafmap 以啟用 SplitMap 功能 (通常基於 ipyleaflet 或 folium)
import leafmap.leafmap as leafmap
import warnings
import os
from pathlib import Path

# 忽略 geopandas/shapely 相關的未來警告
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. 數據載入與狀態管理 (全域/模組級) ---

# 假設這是您的 GeoAI 推論成果檔案 (已包含 'area_m2' 屬性)
# 路徑邏輯: 應用程式檔案（07_solar_panel.py）在 pages/ 下，但 GeoJSON 檔案應在應用程式的根目錄 (上一層)
# 使用 pathlib 獲取當前檔案所在目錄的上一層目錄 (即應用程式根目錄)
# 這樣無論 07_solar_panel.py 在哪個目錄下，都能穩健地找到位於根目錄的檔案。
APP_ROOT = Path(__file__).parent.parent
GEOJSON_FILENAME = "solar_panels_final_results.geojson"
GEOJSON_PATH = APP_ROOT / GEOJSON_FILENAME

# 假設這是原始遙感影像 (GeoTiff)
# 路徑邏輯: 確保它指向應用程式根目錄下的檔案
ORIGINAL_IMAGE_PATH = APP_ROOT / "original_image.tif" # 此檔案目前僅為佔位符，地圖使用 Web Tiles

# 檢查檔案是否存在，如果不存在則創建空的 GeoDataFrame 作為 fallback
def get_initial_data():
    data = None
    if GEOJSON_PATH.exists():
        try:
            # 使用 Path 物件讀取檔案
            data = gpd.read_file(GEOJSON_PATH)
        except Exception as e:
            # 讀取失敗，data 仍為 None
            print(f"Error reading GeoJSON at {GEOJSON_PATH}: {e}")
            
    # 邏輯: 只有在 data 為 None (檔案不存在或讀取失敗) 時，才使用空的 GeoDataFrame
    if data is None: # None指的是無物件，沒有任何東西
        print(f"Warning: {GEOJSON_PATH} not found or corrupted. Using empty data.")
        data = gpd.GeoDataFrame(
            pd.DataFrame({'area_m2': []}), 
            geometry=[], 
            crs="EPSG:4326"
        )
    
    return data

# 核心狀態: 儲存所有 GeoAI 結果 (GeoDataFrame)。使用 solara.reactive 進行全域狀態管理。
all_solar_data = solara.reactive(get_initial_data())


# 篩選後的數據 (依賴於 min_area 狀態)
# 注意：此函數依賴於 Page() 元件內部傳入的 min_area.value
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
def GeoAI_SplitMap(current_filtered_data):
    
    # 1. 創建 Leafmap 實例 (使用 solara.use_memo 確保只運行一次)
    def create_split_map():
        m = leafmap.Map(
            center=[23.7, 120.9], # 台灣中心點附近
            zoom=10, 
        )
        m.layout.height = "70vh"
        
        # 設置左右兩個地圖的底圖
        m.add_basemap("Esri World Imagery", left=True) # 左邊：原始影像
        m.add_basemap("CartoDB Positron", right=True) # 右邊：簡潔底圖顯示 GeoAI 成果
        return m
        
    m = solara.use_memo(create_split_map, dependencies=[]) 
    # 這種用法是標準的 React/Solara Hook 模式，適用於需要明確指定依賴項並在元件內部呼叫時。
    # 明確的 dependencies=[] 確保create_split_map只運行一次。
    
    # 2. 響應式效果: 當篩選數據改變時，更新地圖右側的 GeoJSON 圖層
    solara.use_effect(
        lambda: update_map_layer(m, current_filtered_data), 
        dependencies=[current_filtered_data]
    )
    # 宣告當依賴項[current_filtered_data]改變時，請執行更新圖層update_map_layer(m, current_filtered_data)這個動作。
    # 但更新圖層這動作在頁面載入之初不可立即執行，要等待地圖實例 m 準備好且依賴項有改變才執行，因此要延遲執行。
    # 於是lambda: update_map_layer(m, current_filtered_data) 創建了一個匿名、無參數的函式。
    # 這個函式將 m 和 current_filtered_data 這兩個變數封裝在它的執行體內部。
    # Solara 接收這個 lambda 匿名函式，並在確認依賴項 [current_filtered_data] 改變後，才執行這個被封裝的函式。
    
    # 3. 處理地圖更新邏輯
    def update_map_layer(map_instance, gdf):
        if map_instance is None:
            return
        
        # 定義圖層名稱
        LAYER_NAME = "GeoAI_Filtered_Solar_Panels"
        
        # 移除舊圖層 (無論是否篩選出結果)
        try:
            map_instance.remove_layer(LAYER_NAME, right=True) 
        except Exception:
            # 忽略移除失敗 (例如圖層不存在)
            pass

        # 如果有篩選結果，則加入新圖層
        if gdf is not None and not gdf.empty:
            
            # 使用 Leafmap 的 add_gdf 方法加入向量數據到右側地圖
            map_instance.add_gdf(
                gdf, 
                layer_name=LAYER_NAME, 
                right=True, # 確保圖層只出現在右側地圖
                style_function={
                    "fillColor": "#FFD700", # 金色填充
                    "color": "#FF4500",      # 橘紅色邊框
                    "weight": 1.5,
                    "fillOpacity": 0.6
                }
            )

    # 使用 solara.display() 橋接 Leafmap (IPython Widget)
    return solara.display(m)


# --- 3. 應用程式頁面佈局 ---

@solara.component
def Page():
    # 移入 Page 元件，符合 Solara/Hook 規範。
    # 處理多使用者的 UI 互動，如滑塊、輸入框、按鈕點擊等個人化狀態。
    # solara.use_state(100) 返回 (value, setter) 的 tuple，例如 (100.0, function)
    min_area_value, set_min_area = solara.use_state(100.0)

    # 在元件內部使用 solara.use_memo 鉤子來記憶化計算結果。
    # 這樣才能確保在有 render context 的情況下執行 Hook。
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
    with solara.Column(align="stretch", style={"padding": "20px"}):   # padding (內邊距) 在內容和容器邊緣之間創建了 20 像素的空間。
        solara.Title("GeoAI 光電板成果服務化") # 瀏覽器 Tab 標題
        
        solara.Markdown("# 🌞 光電板 GeoAI 成果篩選器")
        solara.Markdown("---")
        
        # 滑塊控制元件
        solara.SliderFloat(
            label=f"最小光電板面積 ({filtered_count}/{total_count} 個顯示中)", 
            value=min_area_value, 
            min=0.0, 
            max=max_area,
            step=10.0,
            thumb_label="always",
        )
        
        # 統計資訊
        solara.Info(f"總共偵測到 **{total_count}** 個地物。目前顯示 **{filtered_count}** 個面積大於 **{min_area_value:.2f} m²** 的光電板。")
        
        solara.Markdown("## 🌐 對比圖台：左側 (原始影像) vs 右側 (篩選結果)")
        
        # 對比地圖元件：將篩選後的數據傳遞給地圖元件
        GeoAI_SplitMap(current_filtered_data)
        
        solara.Markdown(
            """
            **提示：**
            * 左側地圖顯示原始衛星影像 (Web Tiles)。
            * 右側地圖顯示 GeoAI 推論後的 GeoJSON 成果。
            * 拖動滑塊即可即時篩選和更新右側圖層，體驗空間數據的互動式分析。
            """
        )
        
        # 數據下載按鈕 (作為 GeoAI 成果服務化的最終步驟)
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
 