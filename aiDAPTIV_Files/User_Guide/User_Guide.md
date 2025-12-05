# Chat with Gmail User Guide


## Overview
LLM app with RAG to chat with Gmail. The app uses Retrieval Augmented Generation (RAG) to provide accurate answers to questions based on the content of your Gmail Inbox.


---

## Chapter 1: Installation and Setting

### Installation Steps

1. Download the `Installer.zip` file and extract its contents.
2. Navigate to the `Installer` folder and double-click on `setup.bat` to initiate the model download. Once the download is complete, the model files will be located in the `./multilingual-e5-large` directory.
3. Before you run `app.exe`, ensure that the following files are present in the same directory:
```
Installer/
    ├── app.exe
    ├── multilingual-e5-large/
    ├── config.yaml
    ├── credentials.json (optional)
    ├── gmail_emails.json (optional)
    └── previous_emails.json (optional)
```
4. Launch the application by clicking on `app.exe`. The chat room will be automatically opened in your web browser.
  
## Chapter 2: How to Use?

### Usage Workflow

#### A. **Initial Setup**

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

#### Step 2: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" and fill in the required information
3. Add your Gmail address to the test users list
4. Publish the application (you can keep it in testing mode for personal use)

#### Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application"
4. Download the credentials file `credentials.json`

#### Step 4: Scope Settings
1. Go to "Data Access" 
2. Click "Add or remove scopes"
3. Search "https://www.googleapis.com/auth/gmail.send" and enable it
4. Update and save 


### B. **Basic Operation**

1. Go to `./aiDAPTIV_Files/Installer` folder and click `app.exe`. This scripts will:
- Check all prerequisites
- Install dependencies automatically
- Start both the API server and Streamlit UI
- The chat room will be automatically opened at http://localhost:8501 (default).

![image](img/fig_1.PNG)


2. Fill in the vllm endpoint and the model name.

![image](img/fig_2.PNG)


3. Upload your `credentials.json`.

![image](img/fig_3.PNG)


4. Click on `Fetch Emails` button. All your emails will be listed below.

![image](img/fig_4.PNG)


5. Ask questions related to your emails in the chat room.

![image](img/fig_5.PNG)
