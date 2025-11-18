import solara
import leafmap.leafmap as leafmap

def create_split_map():
    # 直接使用 split_map，傳入底圖名稱字串
    split_control = leafmap.split_map(
        left_layer="Esri.WorldImagery",  # 左邊：衛星圖 只能底圖圖層  不能是物件
        right_layer="OpenStreetMap",     # 右邊：街道圖 只能底圖圖層  不能是物件
        left_label="衛星影像",
        right_label="街道地圖",
        center=[25.03, 121.5], # 台北
        zoom=12,
        # ipyleaflet 的 split_map 本身就會回傳一個地圖物件，不需要額外設定 height
    )
    
    # (可選) 如果您想調整高度，可以在回傳的地圖物件上設定
    split_control.layout.height = "650px"

    return split_control

@solara.component
def Page():
    solara.Markdown("## 2D 捲簾比對 (Split Map)")
    
    split_widget = solara.use_memo(create_split_map, dependencies=[])
    
    with solara.Column(style={"width": "100%", "height": "700px"}):
        solara.display(split_widget)