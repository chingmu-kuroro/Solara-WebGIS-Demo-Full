import solara


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
    
    with solara.Column(align="center"):
        markdown = """
        ## 3D Mapping with Leafmap and MapLibre
        This is a Solara template for a 3D mapping application using Leafmap and MapLibre. Click on the menu above to see the different examples.
        <br>
        Source code: <https://github.com/opengeos/solara-maplibre>
        ![image](https://github.com/user-attachments/assets/efc9e43b-99c0-40b4-af08-4971e8b96919)
        """

        solara.Markdown(markdown)

    

    
