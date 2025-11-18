import solara
import leafmap.maplibregl as leafmap
import os

# 1. 從 Hugging Face Secret 讀取 API Key
# 如果未設定，提供一個預設值，但地圖將無法正常載入
MAPTILER_KEY = os.environ.get("MAPTILER_API_KEY", "") 

def create_3d_map():
    # 檢查 API Key 是否存在
    if not MAPTILER_KEY:
        # 如果沒有 Key，回傳一個基礎地圖，但不會有地形
        m = leafmap.Map(
            center=[120.9, 23.7], 
            zoom=7, 
            style="OpenStreetMap",
            layout_height="700px"
        )
        return m
    
    # MapTiler Outdoor-v2 Style 內建支援地形資料
    style_url = f"https://api.maptiler.com/maps/outdoor-v2/style.json?key={MAPTILER_KEY}"
    
    m = leafmap.Map(
        style=style_url,
        center=[121.2, 23.8], # 台灣中心偏向山區，方便觀察地形
        zoom=9,
        pitch=65,  # 傾斜角度 (65度)
        bearing=15, # 旋轉角度 (15度)
        # 啟用地形：當使用 MapTiler Style 時，通常只需設定 style URL，
        # Leafmap 會自動處理 style.json 內定義的地形源。
        # 如果需要明確設定，通常是: terrain={"source": "mapbox-dem"}
        layout_height="700px"
    )
    return m

@solara.component
def Page():
    # 2. 警示使用者如果金鑰未設定
    if not MAPTILER_KEY:
        solara.Warning(
            "MapTiler API Key 未設定。請在 Hugging Face Space Settings 中加入 'MAPTILER_API_KEY' Secret，否則 3D 地形無法載入。"
        )
    
    solara.Markdown("## 3D 地形展示 (MapLibre GL)")
    
    # 3. 使用 solara.use_memo 快取地圖物件
    # 依賴於 MAPTILER_KEY，當 Key 改變時地圖會重新生成
    map_object = solara.use_memo(create_3d_map, dependencies=[MAPTILER_KEY])

    # 4. 渲染地圖
    return map_object.to_solara()