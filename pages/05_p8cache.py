import solara
import pandas as pd
import geopandas as gpd
import time

# 1. 定義一個「繁重」的函式 (在元件外部)
def load_data():
    print("...正在從網路下載資料 (這很慢)...")
    time.sleep(3) # 模擬 3 秒的下載
    tw_counties_url = "https://raw.githubusercontent.com/g0v/twgeojson/master/json/twCounty2010.geo.json"
    gdf = gpd.read_file(tw_counties_url)
    return gdf

@solara.component
def Page():
    # 2. 使用 use_memo 來呼叫並快取結果
    gdf = solara.use_memo(load_data, dependencies=[])

    # 3. 建立一個純粹的 DataFrame 副本。
    # 移除 'geometry' 欄位，這會強制 GeoDataFrame 降級為 pandas.DataFrame。
    display_df = gdf.drop(columns=['geometry'], errors='ignore')

    solara.Markdown(f"成功載入 {len(gdf)} 筆台灣縣市資料！")
    solara.DataFrame(display_df) # 傳遞降級後的 DataFrame