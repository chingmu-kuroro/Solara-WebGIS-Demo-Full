import solara

# 1. 建立「狀態」來儲存使用者的輸入
username = solara.reactive("Guest")
age = solara.reactive(20)

@solara.component
def Page():
    # 2. 將狀態「綁定」到 Input 元件
    #    (value=username，而不是 value=username.value)
    solara.InputText("請輸入您的名字:", value=username)
    solara.SliderFloat("請選擇您的年齡:", min=1, max=100, value=age)

    solara.Markdown("---")

    # 3. 這些 Markdown 會「自動」響應上面的輸入
    solara.Markdown(f"### 你好, {username.value}!")
    solara.Markdown(f"你的年齡是: {age.value}")