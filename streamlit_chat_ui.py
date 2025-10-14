#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail 信件聊天室 UI
使用 Streamlit 建立聊天室介面，讓使用者可以對自己的信件內容問問題
"""

import streamlit as st
import requests
import json
import time
from typing import List, Dict, Optional
import os
from datetime import datetime
import subprocess
import sys

# 配置頁面
st.set_page_config(
    page_title="Gmail 信件聊天室",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 配置
API_BASE_URL = "http://localhost:8080"

# 自定義 CSS 樣式
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
    }
    .chat-message.user {
        background-color: #2b313e;
        margin-left: 20%;
    }
    .chat-message.assistant {
        background-color: #475063;
        margin-right: 20%;
    }
    .chat-message .avatar {
        width: 2rem;
        height: 2rem;
        border-radius: 50%;
        margin-right: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
    }
    .chat-message.user .avatar {
        background-color: #1f77b4;
    }
    .chat-message.assistant .avatar {
        background-color: #ff7f0e;
    }
    .stTextInput > div > div > input {
        background-color: #2b313e;
        color: white;
    }
    .stTextArea > div > div > textarea {
        background-color: #2b313e;
        color: white;
    }
    .sidebar .sidebar-content {
        background-color: #1e1e1e;
    }
    .typing-cursor {
        animation: blink 1s infinite;
        color: #ff7f0e;
        font-weight: bold;
    }
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    .chat-container {
        max-height: 70vh;
        overflow-y: auto;
        padding-bottom: 20px;
    }
    .input-container {
        position: sticky;
        bottom: 0;
        background-color: #0e1117;
        padding: 10px 0;
        border-top: 1px solid #262730;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health():
    """檢查 API 服務是否正常運行"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_collections():
    """獲取可用的集合列表"""
    try:
        fname = [folder for folder in os.listdir("./agent_builder_client/test_data") if os.path.isdir(os.path.join("./agent_builder_client/test_data", folder))]
        return [f"{user_name}@gmail.com" for user_name in fname]
    except:
        return []

def query_database(question: str, collection_name: str):
    """查詢數據庫"""
    try:
        url = f"{API_BASE_URL}/query_group"
        data = {
            "question": question,
            "collection_name": collection_name
        }
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        return {"success": False, "error": f"查詢失敗: {str(e)}"}

def load_email_data():
    """載入郵件數據"""
    try:
        # 嘗試載入 gmail_emails.json
        emails_file = "./gmail_emails.json"
        if os.path.exists(emails_file):
            with open(emails_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 如果沒有找到，嘗試載入 chunks 文件
        chunks_file = "./agent_builder_client/test_data/gmail_chunks.json"
        if os.path.exists(chunks_file):
            with open(chunks_file, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
                # 將 chunks 轉換為郵件格式
                emails = []
                for chunk in chunks_data:
                    email = {
                        "id": chunk.get("id", ""),
                        "subject": chunk.get("metadata", {}).get("subject", "無標題"),
                        "from": chunk.get("metadata", {}).get("from", "未知發件人"),
                        "date": chunk.get("metadata", {}).get("date", ""),
                        "snippet": chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", ""),
                        "body": chunk.get("text", "")
                    }
                    emails.append(email)
                return emails
        
        return []
    except Exception as e:
        st.error(f"載入郵件數據失敗: {str(e)}")
        return []


def display_email_detail(email):
    """顯示郵件詳情"""
    st.subheader("📧 郵件詳情")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"**標題:** {email.get('subject', '無標題')}")
        st.write(f"**發件人:** {email.get('from', '未知')}")
        st.write(f"**日期:** {email.get('date', '未知')}")
        st.write(f"**郵件ID:** {email.get('id', '未知')}")
    
    with col2:
        if st.button("返回列表"):
            st.session_state.show_email_detail = False
            st.session_state.selected_email = None
            st.rerun()
    
    st.markdown("---")
    st.write("**郵件內容:**")
    st.text_area("", email.get('body', '無內容'), height=400, disabled=True)

def display_sidebar_email_list():
    """在側邊欄顯示郵件列表"""
    emails = load_email_data()
    
    if not emails:
        st.warning("沒有找到郵件數據")
        return
    
    st.info(f"共 {len(emails)} 封郵件")
    
    # 搜索功能
    search_term = st.text_input("🔍 搜索郵件", placeholder="輸入關鍵詞...", key="sidebar_search")
    
    # 篩選郵件
    filtered_emails = emails
    if search_term:
        filtered_emails = [
            email for email in emails 
            if search_term.lower() in email.get("subject", "").lower() 
            or search_term.lower() in email.get("from", "").lower()
            or search_term.lower() in email.get("snippet", "").lower()
        ]
    
    if filtered_emails:
        # st.write(f"找到 {len(filtered_emails)} 封郵件")
        
        # 顯示所有郵件（不分頁）
        for i, email in enumerate(filtered_emails):
            subject = email.get('subject', '無標題')
            from_email = email.get('from', '未知')
            date = email.get('date', '未知')
            
            # 使用主旨作為 expander 標題
            with st.expander(f"📧 {subject}"):
                st.write(f"**主旨:** {subject}")
                st.write(f"**發件人:** {from_email}")
                st.write(f"**日期:** {date}")
                
                # 顯示郵件預覽
                snippet = email.get('snippet', '無內容')
                if len(snippet) > 100:
                    snippet = snippet[:100] + "..."
                st.write(f"**預覽:** {snippet}")
                
                # 查看詳情按鈕
                if st.button(f"查看詳情", key=f"sidebar_view_{i}"):
                    st.session_state.selected_email = email
                    st.session_state.show_email_detail = True
                    st.rerun()
    else:
        st.warning("沒有找到匹配的郵件")

def display_chat_message(message: str, is_user: bool = False):
    """顯示聊天消息"""
    if is_user:
        st.markdown(f"""
        <div class="chat-message user">
            <div class="avatar">👤</div>
            <div>{message}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant">
            <div class="avatar">🤖</div>
            <div>{message}</div>
        </div>
        """, unsafe_allow_html=True)

def add_to_chat_history(role: str, content: str):
    """添加消息到聊天歷史"""
    st.session_state.chat_history.append({
        "content": content,
        "is_user": role == "user",
        "timestamp": datetime.now()
    })


def fetch_gmail_emails():
    """執行Gmail信件抓取"""
    ##############################################
    if os.path.exists("gmail_emails.json"):
        return True, "Gmail信件抓取成功！"
    ###############################################
    try:
        # 檢查是否存在credentials.json
        if not os.path.exists("credentials.json"):
            return False, "找不到credentials.json文件，請先設置Google OAuth2憑證"
        
        # 執行gmail_fetcher.py，使用UI模式
        result = subprocess.run([sys.executable, "gmail_fetcher.py", "--ui-mode"], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # 檢查是否生成了gmail_emails.json
            if os.path.exists("gmail_emails.json"):
                return True, "Gmail信件抓取成功！"
            else:
                return False, "抓取完成但未生成gmail_emails.json文件"
        else:
            return False, f"抓取失敗: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "抓取超時，請稍後再試"
    except Exception as e:
        return False, f"抓取過程中發生錯誤: {str(e)}"

def convert_emails_to_txt():
    """將抓取的郵件轉換為txt格式"""
    try:
        # 執行gmail_to_txt_converter.py
        result = subprocess.run([sys.executable, "gmail_to_txt_converter.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return True, "郵件轉換為txt文件成功！"
        else:
            return False, f"txt轉換失敗: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "txt轉換超時，請稍後再試"
    except Exception as e:
        return False, f"txt轉換過程中發生錯誤: {str(e)}"

def convert_emails_to_chunks():
    """將抓取的郵件轉換為chunks格式"""
    try:
        # 執行gmail_to_chunks_converter.py
        result = subprocess.run([sys.executable, "gmail_to_chunks_converter.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return True, "郵件轉換為chunks成功！"
        else:
            return False, f"轉換失敗: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "轉換超時，請稍後再試"
    except Exception as e:
        return False, f"轉換過程中發生錯誤: {str(e)}"

def call_vllm_api_streaming(user_prompt: str, endpoint: str):
    """Call vLLM API for Q&A with streaming support"""
    try:
        # Prepare the prompt with email context
        system_prompt = """你是一個有用的助手，專門回答基於提供的郵件內容的問題。
        請僅使用郵件內容中的信息來回答用戶的問題。
        如果在郵件內容中找不到答案，請明確說明。"""
        
        # Prepare the request payload with streaming enabled
        payload = {
            "model": "Qwen2.5-72B-Instruct-AWQ", # "Qwen2.5-32B-Instruct-AWQ",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": True
        }
        
        # Make the streaming API request
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
            stream=True
        )
        
        if response.status_code == 200:
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    yield content  # Yield each chunk for real-time display
                        except json.JSONDecodeError:
                            continue
        else:
            yield f"❌ 調用 vLLM API 錯誤: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        yield f"❌ 連接 vLLM 端點錯誤: {str(e)}"
    except Exception as e:
        yield f"❌ 處理響應錯誤: {str(e)}"

def call_vllm_api_non_streaming(user_prompt: str, endpoint: str):
    """Call vLLM API for Q&A without streaming support"""
    try:
        # Prepare the prompt with email context
        system_prompt = """你是一個有用的助手，專門回答基於提供的郵件內容的問題。
        請僅使用郵件內容中的信息來回答用戶的問題。
        如果在郵件內容中找不到答案，請明確說明。"""
        
        # Prepare the request payload without streaming
        payload = {
            "model": "Qwen2.5-72B-Instruct-AWQ",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        # Make the API request
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                return "❌ 無法獲取回應內容"
        else:
            return f"❌ 調用 vLLM API 錯誤: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ 連接 vLLM 端點錯誤: {str(e)}"
    except Exception as e:
        return f"❌ 處理響應錯誤: {str(e)}"

def detect_new_emails():
    """檢測新增的信件"""
    try:
        # 檢查是否存在之前的信件記錄
        previous_emails_file = "previous_emails.json"
        current_emails_file = "gmail_emails.json"
        
        if not os.path.exists(current_emails_file):
            return [], "沒有找到當前信件文件"
        
        # 讀取當前信件
        with open(current_emails_file, 'r', encoding='utf-8') as f:
            current_emails = json.load(f)
        
        # 如果沒有之前的記錄，則所有信件都是新的
        if not os.path.exists(previous_emails_file):
            return current_emails, f"檢測到 {len(current_emails)} 封新信件"
        
        # 讀取之前的信件記錄
        with open(previous_emails_file, 'r', encoding='utf-8') as f:
            previous_emails = json.load(f)
        
        # 創建之前信件的ID集合
        previous_ids = {email.get('id', '') for email in previous_emails}
        
        # 找出新增的信件
        new_emails = []
        for email in current_emails:
            if email.get('id', '') not in previous_ids:
                new_emails.append(email)
        
        return new_emails, f"檢測到 {len(new_emails)} 封新信件"
        
    except Exception as e:
        return [], f"檢測新信件時發生錯誤: {str(e)}"

def update_previous_emails(successfully_processed_emails):
    """將成功處理的信件加入 previous_emails.json"""
    try:
        previous_emails_file = "previous_emails.json"
        
        # 讀取現有的 previous_emails
        existing_emails = []
        if os.path.exists(previous_emails_file):
            with open(previous_emails_file, 'r', encoding='utf-8') as f:
                existing_emails = json.load(f)
        
        # 創建現有信件的ID集合
        existing_ids = {email.get('id', '') for email in existing_emails}
        
        # 只添加成功處理且不在現有記錄中的信件
        new_processed_emails = []
        for email in successfully_processed_emails:
            if email.get('id', '') not in existing_ids:
                new_processed_emails.append(email)
        
        # 合併現有信件和新處理的信件
        updated_emails = existing_emails + new_processed_emails
        
        # 保存更新後的記錄
        with open(previous_emails_file, 'w', encoding='utf-8') as f:
            json.dump(updated_emails, f, ensure_ascii=False, indent=2)
        
        return len(new_processed_emails)
        
    except Exception as e:
        print(f"更新 previous_emails 時發生錯誤: {str(e)}")
        return 0

def process_new_email_automatically(email, collection_name, vllm_endpoint):
    """自動處理新信件：查詢數據庫並調用vLLM API進行總結"""
    try:
        # 步驟1: 查詢數據庫
        user_question = '總結內容'
        result = query_database(user_question, collection_name.split("@")[0])
        
        if not result.get("success"):
            return False, f"查詢數據庫失敗: {result.get('error', '未知錯誤')}"
        
        # 步驟2: 獲取聊天消息
        chat_messages = result.get("chat_messages", [])
        if not chat_messages:
            return False, "沒有獲取到聊天消息"
        
        # 找到用戶消息
        user_message = None
        for msg in chat_messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            return False, "沒有找到用戶消息"
        
        # 步驟3: 調用vLLM API進行總結（非streaming）
        summary = call_vllm_api_non_streaming(user_message, vllm_endpoint)
        
        if summary.startswith("❌"):
            return False, f"vLLM API調用失敗: {summary}"
        
        return True, summary
        
    except Exception as e:
        return False, f"自動處理信件時發生錯誤: {str(e)}"

def main():
    # 標題
    st.title("📧 Gmail 信件聊天室")
    st.markdown("---")
    
    # 側邊欄 - 配置和狀態
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # API 狀態檢查
        if check_api_health():
            st.success("✅ API 服務正常")
        else:
            st.error("❌ API 服務離線")
            st.stop()
        
        # vLLM API 端點配置
        st.subheader("🔗 vLLM API 配置")
        default_endpoint = "http://10.102.196.26:8799/vllm/v1/chat/completions"
        vllm_endpoint = st.text_input(
            "vLLM API 端點:",
            value=default_endpoint,
            help="輸入 vLLM API 的完整端點 URL",
            key="vllm_endpoint"
        )
        
        # 集合選擇
        st.subheader("📁 選擇信件集合")
        collections = get_collections()
        if collections:
            selected_collection = st.selectbox(
                "選擇要查詢的gmail信箱:",
                collections,
                key="collection_select"
            )
        else:
            st.warning("沒有可用的信件集合")
            selected_collection = None
        
        # Gmail信件抓取
        st.subheader("📥 Gmail信件抓取")
        
        # 檢查credentials.json
        if os.path.exists("credentials.json"):
            st.success("✅ 找到Google OAuth2憑證")
            
            # 抓取按鈕
            if st.button("🔄 抓取Gmail信件", use_container_width=True):
                # 創建進度條
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 步驟1: 抓取Gmail信件
                status_text.text("步驟 1/4: 正在抓取Gmail信件...")
                progress_bar.progress(15)
                
                success, message = fetch_gmail_emails()
                
                if success:
                    progress_bar.progress(25)
                    status_text.text("步驟 1/4: Gmail信件抓取完成")
                    st.success(message)
                    
                    # 步驟2: 轉換為txt文件
                    status_text.text("步驟 2/4: 正在轉換為txt文件...")
                    progress_bar.progress(40)
                    
                    txt_success, txt_message = convert_emails_to_txt()
                    
                    if txt_success:
                        progress_bar.progress(55)
                        status_text.text("步驟 2/4: txt文件轉換完成")
                        st.success(txt_message)
                        
                        # 步驟3: 轉換為chunks
                        status_text.text("步驟 3/4: 正在轉換為chunks格式...")
                        progress_bar.progress(70)
                        
                        chunks_success, chunks_message = convert_emails_to_chunks()
                        status_text.text(f"chunks_success: {chunks_success}...")
                        # 步驟4: 檢測新信件並自動處理
                        if chunks_success:
                            status_text.text("步驟 4/4: 檢測新信件並自動處理...")
                            progress_bar.progress(90)
                            
                            # 檢測新信件
                            new_emails, detect_message = detect_new_emails()
                            
                            if new_emails:
                                st.info(f"🔍 {detect_message}")
                                
                                # 對每封新信件進行自動處理
                                processed_count = 0
                                successfully_processed_emails = []  # 收集成功處理的信件
                                
                                for i, new_email in enumerate(new_emails):
                                    try:
                                        st.write(f"📧 正在處理新信件 {i+1}/{len(new_emails)}: {new_email.get('subject', '無標題')}")
                                        
                                        # 自動處理信件
                                        success, result_message = process_new_email_automatically(new_email, selected_collection, vllm_endpoint)
                                        
                                        if success:
                                            processed_count += 1
                                            successfully_processed_emails.append(new_email)  # 添加到成功處理列表
                                            st.success(f"✅ 信件 {i+1} 處理成功")
                                            # 可以在這裡添加總結結果的顯示，但根據需求不顯示結果
                                        else:
                                            st.warning(f"⚠️ 信件 {i+1} 處理失敗: {result_message}")
                                            
                                    except Exception as e:
                                        st.error(f"❌ 處理信件 {i+1} 時發生錯誤: {str(e)}")
                                
                                # 只有成功處理的信件才加入 previous_emails.json
                                if successfully_processed_emails:
                                    updated_count = update_previous_emails(successfully_processed_emails)
                                    st.success(f"🎉 成功自動處理了 {processed_count} 封新信件，已更新處理記錄")
                                else:
                                    st.info("ℹ️ 沒有信件處理成功，處理記錄未更新")
                            else:
                                st.info(f"ℹ️ {detect_message}")
                        
                        if chunks_success:
                            progress_bar.progress(100)
                            status_text.text("完成: 所有步驟已完成")
                            st.success(chunks_message)
                            st.info("信件數據已更新，頁面將自動刷新")
                            
                            # 清理進度條
                            progress_bar.empty()
                            status_text.empty()
                            
                            # 自動刷新
                            time.sleep(2)
                            st.rerun()
                        else:
                            progress_bar.empty()
                            status_text.empty()
                            st.error(f"chunks轉換失敗: {chunks_message}")
                    else:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"txt轉換失敗: {txt_message}")
                else:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"抓取失敗: {message}")
        else:
            st.error("❌ 找不到credentials.json文件")
            st.info("請先下載Google OAuth2憑證文件並命名為credentials.json")
            st.markdown("""
            **設置步驟:**
            1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
            2. 創建或選擇項目
            3. 啟用Gmail API
            4. 創建OAuth2憑證
            5. 下載憑證文件並重命名為 `credentials.json`
            """)
        
        # 郵件列表
        st.subheader("📧 郵件列表")
        display_sidebar_email_list()


    # 初始化聊天歷史
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "show_email_detail" not in st.session_state:
        st.session_state.show_email_detail = False
    if "selected_email" not in st.session_state:
        st.session_state.selected_email = None
    
    # 檢查是否要顯示郵件詳情
    if st.session_state.show_email_detail and st.session_state.selected_email:
        display_email_detail(st.session_state.selected_email)
    else:
        # 正常的聊天界面
        st.markdown("---")
        
        # 顯示聊天歷史
        if st.session_state.chat_history:
            st.subheader("💬 與您的信件對話")
            
            # 創建聊天容器
            chat_container = st.container()
            
            with chat_container:
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                
                # 顯示聊天歷史（從上到下按順序顯示）
                for message in st.session_state.chat_history:
                    # 確保消息有正確的格式
                    is_user = message.get("is_user", False)
                    content = message.get("content", "")
                    display_chat_message(content, is_user)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
        
        # 聊天輸入區域
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        user_question = st.text_input("Ask a question about your gmail:", placeholder="")
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button("Send", use_container_width=True):
                if user_question:
                    # Add user question to chat history
                    add_to_chat_history("user", user_question)
                    
                    # 查詢數據庫
                    with st.spinner("🎨 正在分析您的信件..."):
                        result = query_database(user_question, selected_collection.split("@")[0])
                    
                    # Get answer from video content
                    full_answer = ""  # 初始化 full_answer
                    if result.get("success"):
                        chat_messages = result.get("chat_messages", [])
                        if chat_messages:
                            user_message = None
                            for msg in chat_messages:
                                if msg.get("role") == "user":
                                    user_message = msg.get("content", "")
                                    break
                            
                            # 生成回答（使用流式輸出）
                            if user_message:
                                # 創建一個容器來顯示流式回答
                                streaming_container = st.empty()
                                full_answer = ""
                                
                                # 顯示正在生成的提示
                                streaming_container.markdown("""
                                <div class="chat-message assistant">
                                    <div class="avatar">🤖</div>
                                    <div>🤔 正在思考中...</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # 使用流式 API 生成回答
                                try:
                                    for chunk in call_vllm_api_streaming(user_message, vllm_endpoint):
                                        if chunk:
                                            full_answer += chunk
                                            # 實時更新顯示，添加打字機效果
                                            streaming_container.markdown(f"""
                                            <div class="chat-message assistant">
                                                <div class="avatar">🤖</div>
                                                <div>{full_answer}<span class="typing-cursor">|</span></div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            # 添加小延遲以模擬打字效果
                                            time.sleep(0.05)
                                    
                                    # 最終顯示完整回答（移除游標）
                                    streaming_container.markdown(f"""
                                    <div class="chat-message assistant">
                                        <div class="avatar">🤖</div>
                                        <div>{full_answer}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                except Exception as e:
                                    full_answer = f"❌ 生成回答時發生錯誤: {str(e)}"
                                    streaming_container.markdown(f"""
                                    <div class="chat-message assistant">
                                        <div class="avatar">🤖</div>
                                        <div>{full_answer}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                full_answer = "抱歉，我無法從您的信件中找到相關信息。"
                                st.markdown(f"""
                                <div class="chat-message assistant">
                                    <div class="avatar">🤖</div>
                                    <div>{full_answer}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            full_answer = "抱歉，我無法從您的信件中找到相關信息。"
                            st.markdown(f"""
                            <div class="chat-message assistant">
                                <div class="avatar">🤖</div>
                                <div>{full_answer}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        error_msg = result.get("error", "信件查詢失敗")
                        st.error(f"❌ {error_msg}")
                        
                        # 添加錯誤消息到歷史
                        st.session_state.chat_history.append({
                            "content": error_msg,
                            "is_user": False,
                            "timestamp": datetime.now()
                        })
                    
                    if result.get("success"):
                        # 流式輸出完成後，添加到聊天歷史
                        st.session_state.chat_history.append({
                            "content": full_answer,
                            "is_user": False,
                            "timestamp": datetime.now()
                        })
                    
                    # 不需要重新渲染，聊天歷史已經在頁面頂部顯示
                    
                    # 顯示詳細信息
                    with st.expander("🔍 查詢詳情"):
                        st.json(result)
                    
                    # Rerun to update the chat display
                    st.rerun()
        
        with col2:
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
