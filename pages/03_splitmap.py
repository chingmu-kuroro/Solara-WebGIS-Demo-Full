import solara
import leafmap.leafmap as leafmap

# 1. 定義建立捲簾的函式
def create_split_map():
    # --- 建立左側地圖 ---
    # 注意：必須使用 ipyleaflet 支援的底圖名稱
    m1 = leafmap.Map(
        center=[25.03, 121.5], 
        zoom=12, 
        basemap="Esri.WorldImagery", # 衛星圖
        layout_height="600px"
    )

    # --- 建立右側地圖 ---
    m2 = leafmap.Map(
        center=[25.03, 121.5], 
        zoom=12, 
        basemap="OpenStreetMap", # 街道圖
        layout_height="600px"
    )

    # --- 建立捲簾控制項 ---
    # 這會回傳一個 ipywidget 元件
    split_control = leafmap.split_map(
        m1, m2,
        left_label="衛星影像",
        right_label="街道地圖"
    )
    
    return split_control

@solara.component
def Page():
    solara.Markdown("## 2D 捲簾比對 (Split Map)")
    
    # 2. 使用 use_memo 快取
    #    (注意：split_map 包含兩個地圖，建立成本較高，務必快取)
    split_widget = solara.use_memo(create_split_map, dependencies=[])
    
    # 3. 使用 solara.display 渲染
    #    這是在 HF Docker 環境中最穩健的 ipywidget 顯示方式
    with solara.Column(style={"width": "100%", "height": "650px"}):
        solara.display(split_widget)