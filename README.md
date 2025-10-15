
## 📨 Chat with Gmail 

LLM app with RAG to chat with Gmail. The app uses Retrieval Augmented Generation (RAG) to provide accurate answers to questions based on the content of your Gmail Inbox.

### Features

- Connect to your Gmail Inbox
- Ask questions about the content of your emails
- Get accurate answers using RAG and the selected LLM

### Settings

#### 1.設定Google Cloud專案

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

#### 2. 設定OAuth同意畫面

- 前往「APIs & Services」>「OAuth consent screen」
- 選擇「External」並填寫必要資訊
- 添加你的Gmail地址到測試使用者清單
- 發布應用程式（如果只是測試，可以保持為測試狀態）


### Start your app

#### Linux ver.
```bash
chmod +x start.sh
start.sh
```

#### Windows ver.
```bash
start.bat
```