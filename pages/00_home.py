import solara


# 準備資料
df = pd.DataFrame(
    {"x": [1, 2, 3, 4], "y": [10, 11, 12, 13]}
)
fig = px.scatter(df, x="x", y="y", title="我的 Plotly 圖表")

@solara.component
def Page():
    
    solara.Markdown("### 水平排列 (Row)")

    # 'with' 語法會自動將內部的所有元件放入 Row 容器
    with solara.Row():
        solara.Markdown("欄位 1", style={"width": "30%", "border": "1px solid red"})
        solara.Markdown("欄位 2", style={"width": "70%", "border": "1px solid blue"})

    solara.Markdown("---")
    
    solara.Markdown("### 垂直排列 (Column)")
    
    # 'with' 語法會自動將內部的所有元件放入 Column 容器
    with solara.Column():
        solara.Markdown("這個元件在 Row 的下面")
        solara.Markdown("這個元件在更下面")
    
    solara.Markdown("### 這是另一個置中的垂直排列容器 (Column)")

    # 'with' 語法會自動將內部的所有元件放入 Column 容器
    with solara.Column(align="center"):
        solara.Markdown("## 顯示 DataFrame")
        solara.DataFrame(df)
        solara.Markdown("## 顯示 Plotly 圖表")
        solara.FigurePlotly(fig)

    

    
