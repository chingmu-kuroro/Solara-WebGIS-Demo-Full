# 1. 選擇 Python 3.11 標準版 作為基礎
FROM python:3.11

# 2. 設定工作目錄
WORKDIR /code

# 3. 複製 requirements 並安裝
# (利用 Docker cache 機制，先裝套件再複製程式碼)
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 4. 建立一個非 Root 使用者 (User ID 1000)
# 這是 Hugging Face Spaces 最關鍵的一步！
RUN useradd -m -u 1000 user

# 5. 手動建立快取資料夾，並把權限設給 user
# 我們不讓 Python 程式去猜，直接用 Linux 指令建好給它
RUN mkdir -p /home/user/.cache/solara && chown -R user:user /home/user

# 6. 切換到該使用者
USER user

# 7. 設定環境變數
# 加入 SOLARA_PROXY_CACHE_DIR 指向使用者的家目錄，目的為提升效能
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    SOLARA_PROXY_CACHE_DIR=/home/user/.cache/solara

# 8. 複製所有程式碼到工作目錄
# --chown=user 確保新使用者有權限讀取這些檔案
COPY --chown=user . /code

# 9. 啟動指令
# 注意：一定要指定 host 為 0.0.0.0 和 port 為 7860
CMD ["solara", "run", "./pages", "--host=0.0.0.0", "--port=7860"]