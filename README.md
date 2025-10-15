## 📨 Chat with Gmail Inbox 

LLM app with RAG to chat with Gmail. The app uses Retrieval Augmented Generation (RAG) to provide accurate answers to questions based on the content of your Gmail Inbox.

### Features

- Connect to your Gmail Inbox
- Ask questions about the content of your emails
- Get accurate answers using RAG and the selected LLM

### Settings

1. Install the required dependencies
```bash
uv venv
```
```bash
uv pip install -r requirements.txt
```

2.設定Google Cloud專案

- 前往 [Google Cloud Console](https://console.cloud.google.com/)
- 建立新專案或選擇現有專案
- 啟用Gmail API：
    - 前往「APIs & Services」>「Library」
    - 搜尋「Gmail API」並啟用
iv. 建立OAuth 2.0憑證：
- 前往「APIs & Services」>「Credentials」
- 點擊「Create Credentials」>「OAuth client ID」
- 選擇「Desktop application」
- 下載憑證檔案並重新命名為 `credentials.json`
- 將檔案放在與 `gmail_fetcher.py` 相同的目錄中

3. 設定OAuth同意畫面

- 前往「APIs & Services」>「OAuth consent screen」
- 選擇「External」並填寫必要資訊
- 添加你的Gmail地址到測試使用者清單
- 發布應用程式（如果只是測試，可以保持為測試狀態）

4.  啟用Embedding model
```bash
git clone https://huggingface.co/intfloat/multilingual-e5-large
```
```bash
uv run .\api.py
```

### Start your app

#### Step1. 抓取信件
```bash
uv run gmail_fetcher.py
```
抓取信件的結果會放在gmail_emails.json"

##### Step2. 信件資料處理
讀取gmail_emails.json轉換為chunks
輸出路徑./agent_builder_client/test_data/gmail_chunks.json
```bash
uv run gmail_to_chunks_converter.py
```

讀取gmail_emails.json 並轉換為.txt 
輸出路徑: chat_with_gmail/agent_builder_client/test_data/ptest9109
```bash
uv run gmail_to_txt_converter.py
```

#### Step3. Create DB
```bash
uv run create_db.py
```

##### Step4. Start Web App

```bash
uv run streamlit run .\streamlit_chat_ui.py --server.headless true
```
