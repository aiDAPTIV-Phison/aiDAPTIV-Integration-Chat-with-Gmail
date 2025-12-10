#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail Email Chat UI
Using Streamlit to create a chat interface for users to ask questions about their email content
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
import multiprocessing
from pathlib import Path
import logging
from agent_builder_client.config import settings

# 檢查是否在 multiprocessing 子進程中（Windows spawn 模式）
# 如果是子進程，不執行主程序代碼
if __name__ != "__main__":
    try:
        if hasattr(multiprocessing, 'current_process'):
            current_process = multiprocessing.current_process()
            if hasattr(current_process, 'name') and current_process.name != 'MainProcess':
                # 這是 multiprocessing 子進程，不執行主程序
                sys.exit(0)
    except:
        pass

# Configure page
st.set_page_config(
    page_title="Gmail Chat Room",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_BASE_URL = f"http://{settings.API_HOST}:{settings.API_PORT}"

# Runtime paths (credentials/emails live next to the executable)
APP_BASE_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.resolve()
CREDENTIALS_FILE = APP_BASE_DIR / "credentials.json"
GMAIL_EMAILS_FILE = APP_BASE_DIR / "gmail_emails.json"
PREVIOUS_EMAILS_FILE = APP_BASE_DIR / "previous_emails.json"
LOG_FILE = APP_BASE_DIR / "streamlit.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Custom CSS styles
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
    """Check if API service is running normally"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def validate_credential_file(file_content):
    """Validate uploaded credential file"""
    try:
        # Parse JSON
        cred_data = json.loads(file_content.decode('utf-8'))
        
        # Check required fields
        if "installed" not in cred_data and "web" not in cred_data:
            return False, "Credential file format is incorrect, missing 'installed' or 'web' field"
        
        # Check OAuth2 credential key fields
        if "installed" in cred_data:
            required_fields = ["client_id", "client_secret", "auth_uri", "token_uri"]
            for field in required_fields:
                if field not in cred_data["installed"]:
                    return False, f"Credential file missing required field: {field}"
        
        return True, "Credential file format is correct"
        
    except json.JSONDecodeError:
        return False, "File is not a valid JSON format"
    except Exception as e:
        return False, f"Error occurred while validating credential file: {str(e)}"

def get_collections():
    """Get available collection list"""
    try:
        fname = [folder for folder in os.listdir("./agent_builder_client/test_data") if os.path.isdir(os.path.join("./agent_builder_client/test_data", folder))]
        return [f"{user_name}@gmail.com" for user_name in fname]
    except:
        return []

def query_database(question: str, collection_name: str):
    """Query database"""
    try:
        url = f"{API_BASE_URL}/query_group"
        data = {
            "question": question,
            "collection_name": collection_name
        }
        
        logger.info(f"Querying database - URL: {url}, Collection: {collection_name}, Question: {question[:100]}...")
        
        response = requests.post(url, json=data, timeout=30)
        
        # Log HTTP status code
        logger.info(f"Database query response status code: {response.status_code}")
        
        # Check HTTP status code
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
            logger.error(f"Database query failed with HTTP error: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Try to parse JSON response
        try:
            result = response.json()
            logger.debug(f"Database query response JSON: {json.dumps(result, ensure_ascii=False)[:500]}")
            
            # Check if response has success field
            if "success" not in result:
                error_msg = f"Response missing 'success' field. Response keys: {list(result.keys())}"
                logger.error(f"Database query response format error: {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Log success status
            if result.get("success"):
                logger.info(f"Database query succeeded for collection: {collection_name}")
            else:
                error_detail = result.get("error", "Unknown error")
                logger.warning(f"Database query returned success=False - Error: {error_detail}")
            
            return result
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {str(e)}, Response text: {response.text[:500]}"
            logger.error(f"Database query JSON parsing error: {error_msg}")
            return {"success": False, "error": error_msg}
            
    except requests.exceptions.Timeout:
        error_msg = "Request timeout (30s)"
        logger.error(f"Database query timeout: {error_msg}")
        return {"success": False, "error": error_msg}
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(f"Database query connection error: {error_msg}")
        logger.error(f"API_BASE_URL: {API_BASE_URL} - Please check if API server is running")
        return {"success": False, "error": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"Request exception: {str(e)}"
        logger.error(f"Database query request error: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(f"Database query unexpected error: {error_msg}")
        return {"success": False, "error": error_msg}

def load_email_data():
    """Load emails"""
    try:
        emails_file = PREVIOUS_EMAILS_FILE
        if emails_file.exists():
            with open(emails_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []
    except Exception as e:
        st.error(f"Failed to load emails: {str(e)}")
        return []


def display_email_detail(email):
    """Display email details"""
    st.subheader("📧 Email Details")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"**Subject:** {email.get('subject', 'No Subject')}")
        st.write(f"**From:** {email.get('from', 'Unknown')}")
        st.write(f"**Date:** {email.get('date', 'Unknown')}")
        st.write(f"**Email ID:** {email.get('id', 'Unknown')}")
    
    with col2:
        if st.button("Back to List"):
            st.session_state.show_email_detail = False
            st.session_state.selected_email = None
            st.rerun()
    
    st.markdown("---")
    st.write("**Email Content:**")
    st.text_area("", email.get('body', 'No Content'), height=400, disabled=True)

def display_sidebar_email_list():
    """Display email list in sidebar"""
    emails = load_email_data()
    
    if not emails:
        st.warning("No emails found")
        return
    
    st.info(f"Total {len(emails)} emails")
    
    # Search functionality
    search_term = st.text_input("🔍 Search Emails", placeholder="Enter keywords...", key="sidebar_search")
    
    # Filter emails
    filtered_emails = emails
    if search_term:
        filtered_emails = [
            email for email in emails 
            if search_term.lower() in email.get("subject", "").lower() 
            or search_term.lower() in email.get("from", "").lower()
            or search_term.lower() in email.get("snippet", "").lower()
        ]
    
    if filtered_emails:
        # st.write(f"Found {len(filtered_emails)} emails")
        
        # Display all emails (no pagination)
        for i, email in enumerate(filtered_emails):
            subject = email.get('subject', 'No Subject')
            from_email = email.get('from', 'Unknown')
            date = email.get('date', 'Unknown')
            
            # Use subject as expander title
            with st.expander(f"📧 {subject}"):
                st.write(f"**Subject:** {subject}")
                st.write(f"**From:** {from_email}")
                st.write(f"**Date:** {date}")
                
                # Display email preview
                snippet = email.get('snippet', 'No Content')
                if len(snippet) > 100:
                    snippet = snippet[:100] + "..."
                st.write(f"**Preview:** {snippet}")
                
                # View details button
                if st.button(f"View Details", key=f"sidebar_view_{i}"):
                    st.session_state.selected_email = email
                    st.session_state.show_email_detail = True
                    st.rerun()
    else:
        st.warning("No matching emails found")

def display_chat_message(message: str, is_user: bool = False):
    """Display chat message"""
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
    """Add message to chat history"""
    st.session_state.chat_history.append({
        "content": content,
        "is_user": role == "user",
        "timestamp": datetime.now()
    })


def fetch_gmail_emails():
    """Execute Gmail email fetching"""
    try:
        # Check if credentials.json exists
        if not CREDENTIALS_FILE.exists():
            return False, "Cannot find credentials.json file, please set up Google OAuth2 credentials first"
        
        # Execute gmail_fetcher.py using UI mode
        result = subprocess.run([sys.executable, "gmail_fetcher.py", "--ui-mode"], 
                              capture_output=True, text=True, timeout=300,
                              encoding='utf-8', errors='replace')
        
        # Log messages to log file based on return code and log level
        if result.stderr:
            # Parse log level from stderr and log accordingly
            stderr_lines = result.stderr.strip().split('\n')
            for line in stderr_lines:
                if not line.strip():
                    continue
                # Check if line contains log level indicators
                if ' - ERROR - ' in line:
                    logger.error(f"Gmail fetcher: {line}")
                elif ' - WARNING - ' in line or ' - WARN - ' in line:
                    logger.warning(f"Gmail fetcher: {line}")
                elif ' - INFO - ' in line:
                    logger.info(f"Gmail fetcher: {line}")
                elif ' - DEBUG - ' in line:
                    logger.debug(f"Gmail fetcher: {line}")
                else:
                    # If return code is 0, treat as info; otherwise as error
                    if result.returncode == 0:
                        logger.info(f"Gmail fetcher: {line}")
                    else:
                        logger.error(f"Gmail fetcher: {line}")
        
        if result.stdout and result.returncode != 0:
            logger.error(f"Gmail fetcher stdout: {result.stdout}")
        
        if result.returncode == 0:
            # Check if gmail_emails.json was generated
            if GMAIL_EMAILS_FILE.exists():
                return True, "Email fetching success!"
            else:
                # Analyze why no file was generated
                reason = "Fetching completed but gmail_emails.json file was not generated\n"
                if result.stdout:
                    reason += f"Standard output: {result.stdout}\n"
                if result.stderr:
                    reason += f"Error message: {result.stderr}\n"
                
                return False, reason
        else:
            error_msg = f"Fetching failed (return code: {result.returncode})\n"
            if result.stderr:
                error_msg += f"Error output: {result.stderr}\n"
            if result.stdout:
                error_msg += f"Standard output: {result.stdout}"
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, "Fetching timeout, please try again later"
    except Exception as e:
        return False, f"Error occurred during fetching: {str(e)}"

def convert_emails_to_txt():
    """Convert fetched emails to txt format"""
    try:
        # Execute gmail_to_txt_converter.py
        result = subprocess.run([sys.executable, "gmail_to_txt_converter.py"], 
                              capture_output=True, text=True, timeout=60,
                              encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            return True, "Successfully converted emails to .txt files!"
        else:
            return False, f"txt conversion failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "txt conversion timeout, please try again later"
    except Exception as e:
        return False, f"Error occurred during txt conversion: {str(e)}"

def convert_emails_to_chunks():
    """Convert fetched emails to chunks format"""
    try:
        # Execute gmail_to_chunks_converter.py
        result = subprocess.run([sys.executable, "gmail_to_chunks_converter.py"], 
                              capture_output=True, text=True, timeout=60,
                              encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            return True, "Successfully converted emails to chunks!"
        else:
            return False, f"Conversion failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "Conversion timeout, please try again later"
    except Exception as e:
        return False, f"Error occurred during conversion: {str(e)}"

def create_db(json_path: str, collection_name: str):
    """Create vector database"""
    try:
        url = f"{API_BASE_URL}/create_db"
        data = {
            "json_path": json_path,
            "collection_name": collection_name
        }
        response = requests.post(url, json=data, timeout=300)
        return True, f"Successfully created database!"
    except Exception as e:
        return False, f"Failed to create database: {str(e)}"

def call_vllm_api_streaming(user_prompt: str, endpoint: str, model_name: str = "Qwen2.5-72B-Instruct-AWQ"):
    """Call vLLM API for Q&A with streaming support"""
    try:
        # Prepare the prompt with email context
        system_prompt = """You are a helpful assistant specialized in answering questions based on provided email content.
        Please only use the email content to answer user questions.
        If you cannot find the answer in the email content, please clearly state so."""
        
        # Prepare the request payload with streaming enabled
        payload = {
            "model": model_name,
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
            yield f"❌ vLLM API call error: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        yield f"❌ vLLM endpoint connection error: {str(e)}"
    except Exception as e:
        yield f"❌ Response processing error: {str(e)}"

def call_vllm_api_non_streaming(user_prompt: str, endpoint: str, model_name: str = "Qwen2.5-72B-Instruct-AWQ"):
    """Call vLLM API for Q&A without streaming support"""
    try:
        # Prepare the prompt with email context
        system_prompt = """You are a helpful assistant specialized in answering questions based on provided email content.
        Please only use the email content to answer user questions.
        If you cannot find the answer in the email content, please clearly state so."""
        
        # Prepare the request payload without streaming
        payload = {
            "model": model_name,
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
                return "❌ Unable to get response content"
        else:
            return f"❌ vLLM API call error: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ vLLM endpoint connection error: {str(e)}"
    except Exception as e:
        return f"❌ Response processing error: {str(e)}"

def detect_new_emails():
    """Detect new emails"""
    try:
        # Check if previous email records exist
        previous_emails_file = PREVIOUS_EMAILS_FILE
        current_emails_file = GMAIL_EMAILS_FILE
        
        if not current_emails_file.exists():
            return [], "No current email file found"
        
        # Read current emails
        with open(current_emails_file, 'r', encoding='utf-8') as f:
            current_emails = json.load(f)
        
        # If no previous records, all emails are new
        if not previous_emails_file.exists():
            return current_emails, f"Detected {len(current_emails)} new emails"
        
        # Read previous email records
        with open(previous_emails_file, 'r', encoding='utf-8') as f:
            previous_emails = json.load(f)
        
        # Create previous email ID set
        previous_ids = {email.get('id', '') for email in previous_emails}
        
        # Find new emails
        new_emails = []
        for email in current_emails:
            if email.get('id', '') not in previous_ids:
                new_emails.append(email)
        
        return new_emails, f"Detected {len(new_emails)} new emails"
        
    except Exception as e:
        return [], f"Error occurred while detecting new emails: {str(e)}"

def update_previous_emails(successfully_processed_emails):
    """Add successfully processed emails to previous_emails.json"""
    try:
        previous_emails_file = PREVIOUS_EMAILS_FILE
        
        # Read existing previous_emails
        existing_emails = []
        if previous_emails_file.exists():
            with open(previous_emails_file, 'r', encoding='utf-8') as f:
                existing_emails = json.load(f)
        
        # Create existing email ID set
        existing_ids = {email.get('id', '') for email in existing_emails}
        
        # Only add successfully processed emails that are not in existing records
        new_processed_emails = []
        for email in successfully_processed_emails:
            if email.get('id', '') not in existing_ids:
                new_processed_emails.append(email)
        
        # Merge existing emails and newly processed emails
        updated_emails = existing_emails + new_processed_emails
        
        # Save updated records
        with open(previous_emails_file, 'w', encoding='utf-8') as f:
            json.dump(updated_emails, f, ensure_ascii=False, indent=2)
        
        return len(new_processed_emails)
        
    except Exception as e:
        print(f"Error occurred while updating previous_emails: {str(e)}")
        return 0

def process_new_email_automatically(email, vllm_endpoint, model_name="Qwen2.5-72B-Instruct-AWQ"):
    """Automatically process new emails: query database and call vLLM API for summarization"""
    email_id = email.get('id', 'unknown')
    email_subject = email.get('subject', 'No Subject')
    
    try:
        # Step 1: Query database
        user_question = f"Summarize {email_subject} content"
        logger.debug(f"Processing email - ID: {email_id}, Subject: {email_subject}")
        logger.debug(f"Query question: {user_question}")
        
        result = query_database(user_question, "gmail_inbox")
        
        # Log detailed result information
        logger.debug(f"Query result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        logger.debug(f"Query result success: {result.get('success')}")
        logger.debug(f"Query result error: {result.get('error', 'No error field')}")
        
        if not result.get("success"):
            error_detail = result.get('error', 'Unknown error')
            logger.error(f"Database query failed for email {email_id} - Error: {error_detail}")
            logger.error(f"Full result: {json.dumps(result, ensure_ascii=False)[:1000]}")
            return False, f"Database query failed: {error_detail}"
        
        # Step 2: Get chat messages
        chat_messages = result.get("chat_messages", [])
        logger.debug(f"Retrieved {len(chat_messages)} chat messages")
        
        if not chat_messages:
            logger.warning(f"No chat messages retrieved for email {email_id}")
            return False, "No chat messages retrieved"
        
        # Find user message
        user_message = None
        for msg in chat_messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                logger.debug(f"Found user message, length: {len(user_message)}")
                break
        
        if not user_message:
            logger.warning(f"No user message found in chat_messages for email {email_id}")
            logger.debug(f"Chat messages structure: {json.dumps(chat_messages, ensure_ascii=False)[:500]}")
            return False, "No user message found"
        
        # Step 3: Call vLLM API for summarization (non-streaming)
        logger.debug(f"Calling vLLM API for email {email_id}")
        summary = call_vllm_api_non_streaming(user_message, vllm_endpoint, model_name)
        
        if summary.startswith("❌"):
            logger.error(f"vLLM API call failed for email {email_id}: {summary}")
            return False, f"vLLM API call failed: {summary}"
        
        logger.info(f"Email {email_id} processed successfully, summary length: {len(summary)}")
        return True, summary
        
    except Exception as e:
        logger.exception(f"Exception occurred while processing email {email_id}: {str(e)}")
        return False, f"Error occurred during automatic email processing: {str(e)}"

def main():
    # Title
    st.title("📧 Gmail Chat Room")
    st.markdown("---")
    
    # Sidebar - Configuration and Status
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Status Check
        if check_api_health():
            st.success("✅ API Service Available")
        else:
            st.error("❌ API Service Offline")
            st.stop()
        
        # Model Selection
        st.subheader("🤖 Model Configuration")
        # vLLM API endpoint configuration
        # st.subheader("🔗 vLLM API Configuration")
        default_endpoint = "http://localhost:13141/v1/chat/completions"
        vllm_endpoint = st.text_input(
            "vLLM API Endpoint:",
            value=default_endpoint,
            help="Enter the complete vLLM API endpoint URL",
            key="vllm_endpoint"
        )
        default_model = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
        selected_model = st.text_input(
            "Model Name:",
            value=default_model,
            help="Enter the model name to use",
            key="model_name"
        )
        
        # Credential Upload Section
        st.subheader("🔐 Google OAuth2 Credentials")
        
        # File Upload
        uploaded_file = st.file_uploader(
            "Upload credentials.json file",
            type=['json'],
            help="Please upload the OAuth2 credential file downloaded from Google Cloud Console",
            key="credential_upload"
        )
        
        # Process uploaded file
        if uploaded_file is not None:
            try:
                # Read uploaded file content
                file_content = uploaded_file.read()
                
                # Validate credential file
                is_valid, validation_message = validate_credential_file(file_content)
                
                if is_valid:
                    # Save file locally next to executable
                    with open(CREDENTIALS_FILE, "wb") as f:
                        f.write(file_content)
                    
                    st.success("✅ File upload successful!")
                    # st.success(f"✅ {validation_message}")
                    # st.rerun()  # Rerun to update status
                else:
                    st.error(f"❌ {validation_message}")
                    
            except Exception as e:
                st.error(f"❌ Error occurred while uploading file: {str(e)}")
        
        # Check credentials.json
        if CREDENTIALS_FILE.exists():
            st.success("✅ Google OAuth2 credentials uploaded")
            
            # Fetch Button
            if st.button("🔄 Fetch Emails", use_container_width=True):
                # Initialize variables at the beginning to avoid UnboundLocalError
                success = False
                message = ""
                txt_success = False
                txt_message = ""
                chunks_success = False
                chunks_message = ""
                db_success = False
                db_message = ""
                
                try:
                    logger.info("=" * 80)
                    logger.info("Starting email fetching process")
                    logger.info("=" * 80)
                    
                    # Create progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Step 1: Fetch Gmail emails
                    logger.info("Step 1/5: Starting Gmail email fetching...")
                    status_text.text("Step 1/5: Fetching emails...")
                    progress_bar.progress(15)
                    
                    try:
                        success, message = fetch_gmail_emails()
                        
                        if success:
                            progress_bar.progress(25)
                            status_text.text("Step 1/5: Gmail fetching completed")
                            logger.info(f"Step 1/5: Gmail fetching completed successfully - {message}")
                            st.success(message)
                            
                            # Step 2: Convert to txt file
                            logger.info("Step 2/5: Starting txt file conversion...")
                            status_text.text("Step 2/5: Converting to txt file...")
                            progress_bar.progress(40)
                            
                            try:
                                txt_success, txt_message = convert_emails_to_txt()
                                
                                if txt_success:
                                    progress_bar.progress(55)
                                    status_text.text("Step 2/5: txt file conversion completed")
                                    logger.info(f"Step 2/5: txt file conversion completed successfully - {txt_message}")
                                    st.success(txt_message)
                                    
                                    # Step 3: Convert to chunks
                                    logger.info("Step 3/5: Starting chunks format conversion...")
                                    status_text.text("Step 3/5: Converting to chunks format...")
                                    progress_bar.progress(70)
                                    
                                    try:
                                        chunks_success, chunks_message = convert_emails_to_chunks()
                                        
                                        if chunks_success:
                                            status_text.text("Step 3/5: chunks format conversion completed")
                                            logger.info(f"Step 3/5: chunks format conversion completed successfully - {chunks_message}")
                                            st.success(chunks_message)
                                        else:
                                            status_text.text("Step 3/5: chunks format conversion failed")
                                            logger.error(f"Step 3/5: chunks format conversion failed - {chunks_message}")
                                            st.error(chunks_message)
                                            
                                        # Step 4: Create database
                                        logger.info("Step 4/5: Starting database creation...")
                                        status_text.text("Step 4/5: Creating database...")
                                        
                                        try:
                                            db_success, db_message = create_db(json_path="test_data/gmail_chunks.json", collection_name='gmail_inbox')
                                            
                                            if db_success:
                                                status_text.text("Step 4/5: Database creation completed")
                                                logger.info(f"Step 4/5: Database creation completed successfully - {db_message}")
                                                st.success(db_message)
                                            else:
                                                status_text.text("Step 4/5: Database creation failed")
                                                logger.error(f"Step 4/5: Database creation failed - {db_message}")
                                                st.error(db_message)
                                                
                                        except Exception as e:
                                            db_success = False
                                            db_message = f"Internal error during database creation: {str(e)}"
                                            logger.exception(f"Step 4/5: Exception occurred during database creation: {str(e)}")
                                            status_text.text("Step 4/5: Database creation failed")
                                            st.error(db_message)

                                        # Step 5: Detect new emails and process automatically
                                        if chunks_success and db_success:
                                            logger.info("Step 5/5: Starting new email detection and processing...")
                                            status_text.text("Step 5/5: Detecting new emails and processing automatically...")
                                            progress_bar.progress(90)
                                            
                                            try:
                                                # Detect new emails
                                                new_emails, detect_message = detect_new_emails()
                                                logger.info(f"Step 5/5: Email detection completed - {detect_message}")
                                                
                                                if new_emails:
                                                    st.info(f"🔍 {detect_message}")
                                                    logger.info(f"Step 5/5: Found {len(new_emails)} new emails to process")
                                                    
                                                    # Automatically process each new email
                                                    processed_count = 0
                                                    successfully_processed_emails = []  # Collect successfully processed emails
                                                    
                                                    for i, new_email in enumerate(new_emails):
                                                        email_id = new_email.get('id', 'unknown')
                                                        email_subject = new_email.get('subject', 'No Subject')
                                                        
                                                        try:
                                                            logger.info(f"Step 5/5: Processing email {i+1}/{len(new_emails)} - ID: {email_id}, Subject: {email_subject}")
                                                            st.write(f"📧 Processing new email {i+1}/{len(new_emails)}: {email_subject}")
                                                            
                                                            # Automatically process email
                                                            success, result_message = process_new_email_automatically(new_email, vllm_endpoint, selected_model)
                                                            
                                                            if success:
                                                                processed_count += 1
                                                                successfully_processed_emails.append(new_email)  # Add to successfully processed list
                                                                logger.info(f"Step 5/5: Email {i+1} processed successfully - ID: {email_id}, Subject: {email_subject}")
                                                                st.success(f"✅ Email {i+1} - {email_subject} processed successfully")
                                                                # Can add summary result display here, but not showing results as per requirements
                                                            else:
                                                                logger.warning(f"Step 5/5: Email {i+1} processing failed - ID: {email_id}, Subject: {email_subject}, Error: {result_message}")
                                                                st.warning(f"⚠️ Email {i+1} processing failed: {result_message}")
                                                                
                                                        except Exception as e:
                                                            logger.exception(f"Step 5/5: Exception occurred while processing email {i+1} - ID: {email_id}, Subject: {email_subject}, Error: {str(e)}")
                                                            st.error(f"❌ Error occurred while processing email {i+1}: {str(e)}")
                                                    
                                                    # Only successfully processed emails are added to previous_emails.json
                                                    if successfully_processed_emails:
                                                        try:
                                                            updated_count = update_previous_emails(successfully_processed_emails)
                                                            logger.info(f"Step 5/5: Updated previous_emails.json with {updated_count} successfully processed emails")
                                                            st.success(f"🎉 Successfully processed {processed_count} new emails, processing records updated")
                                                        except Exception as e:
                                                            logger.exception(f"Step 5/5: Exception occurred while updating previous_emails.json: {str(e)}")
                                                            st.error(f"Failed to update processing records: {str(e)}")
                                                    else:
                                                        logger.info("Step 5/5: No emails processed successfully, processing records not updated")
                                                        st.info("ℹ️ No emails processed successfully, processing records not updated")
                                                        
                                            except Exception as e:
                                                logger.exception(f"Step 5/5: Exception occurred during email detection and processing: {str(e)}")
                                                st.error(f"Error during email detection and processing: {str(e)}")
                                        else:
                                            logger.warning("Step 5/5: Skipped - chunks conversion or database creation failed")
                                    
                                    except Exception as e:
                                        chunks_success = False
                                        chunks_message = f"Internal error during chunks conversion: {str(e)}"
                                        logger.exception(f"Step 3/5: Exception occurred during chunks conversion: {str(e)}")
                                        status_text.text("Step 3/5: chunks format conversion failed")
                                        st.error(chunks_message)
                                
                                else:
                                    progress_bar.empty()
                                    status_text.empty()
                                    logger.error(f"Step 2/5: txt file conversion failed - {txt_message}")
                                    st.error(f"txt conversion failed: {txt_message}")
                                    
                            except Exception as e:
                                logger.exception(f"Step 2/5: Exception occurred during txt file conversion: {str(e)}")
                                progress_bar.empty()
                                status_text.empty()
                                st.error(f"Internal error during txt conversion: {str(e)}")
                        else:
                            progress_bar.empty()
                            status_text.empty()
                            logger.error(f"Step 1/5: Gmail fetching failed - {message}")
                            st.error(f"Gmail fetching failed: {message}")
                            
                    except Exception as e:
                        logger.exception(f"Step 1/5: Exception occurred during Gmail fetching: {str(e)}")
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"Internal error during Gmail fetching: {str(e)}")
                    
                    # Final status - only check if Step 1 succeeded
                    if success:
                        # Final status check
                        if chunks_success:
                            progress_bar.progress(100)
                            status_text.text("Completed: All steps completed")
                            logger.info("=" * 80)
                            logger.info("Email fetching process completed successfully")
                            logger.info("=" * 80)
                            st.success(chunks_message)
                            st.info("Email data updated, page will refresh automatically")
                            
                            # Clear progress bar
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Auto refresh
                            time.sleep(2)
                            st.rerun()
                        elif not chunks_success and txt_success:
                            progress_bar.empty()
                            status_text.empty()
                            logger.error("Email fetching process failed at chunks conversion step")
                            st.error(f"chunks conversion failed: {chunks_message}")
                        elif not txt_success:
                            progress_bar.empty()
                            status_text.empty()
                            logger.error("Email fetching process failed at txt conversion step")
                            st.error(f"txt conversion failed: {txt_message}")
                        else:
                            # This should not be reached, but handle it just in case
                            progress_bar.empty()
                            status_text.empty()
                            logger.error("Email fetching process failed at an unknown step")
                        
                except Exception as e:
                    logger.exception(f"Unexpected exception in email fetching process: {str(e)}")
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"Unexpected error occurred: {str(e)}")
        else:
            st.error("❌ credentials.json file not found")
            st.info("Please upload Google OAuth2 credential file")

        # Email List
        st.subheader("📧 Email List")
        display_sidebar_email_list()


    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "show_email_detail" not in st.session_state:
        st.session_state.show_email_detail = False
    if "selected_email" not in st.session_state:
        st.session_state.selected_email = None
    
    # Check if email details should be displayed
    if st.session_state.show_email_detail and st.session_state.selected_email:
        display_email_detail(st.session_state.selected_email)
    else:
        # Normal chat interface
        st.markdown("---")
        
        # Display chat history
        if st.session_state.chat_history:
            st.subheader("💬 Chat with Your Emails")
            
            # Create chat container
            chat_container = st.container()
            
            with chat_container:
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                
                # Display chat history (from top to bottom in order)
                for message in st.session_state.chat_history:
                    # Ensure message has correct format
                    is_user = message.get("is_user", False)
                    content = message.get("content", "")
                    display_chat_message(content, is_user)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Chat input area
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        user_question = st.text_input("Ask a question about your gmail:", placeholder="")
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button("Send", use_container_width=True):
                if user_question:
                    # Add user question to chat history
                    add_to_chat_history("user", user_question)
                    
                    # Query database
                    with st.spinner("🎨 Analyzing your emails..."):
                        result = query_database(user_question, 'gmail_inbox')
                    
                    # Get answer from video content
                    full_answer = ""  # Initialize full_answer
                    if result.get("success"):
                        chat_messages = result.get("chat_messages", [])
                        if chat_messages:
                            user_message = None
                            for msg in chat_messages:
                                if msg.get("role") == "user":
                                    user_message = msg.get("content", "")
                                    break
                            
                            # Generate answer (using streaming output)
                            if user_message:
                                # Create a container to display streaming answer
                                streaming_container = st.empty()
                                full_answer = ""
                                
                                # Display generating prompt
                                streaming_container.markdown("""
                                <div class="chat-message assistant">
                                    <div class="avatar">🤖</div>
                                    <div>🤔 Thinking...</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Use streaming API to generate answer
                                try:
                                    for chunk in call_vllm_api_streaming(user_message, vllm_endpoint, selected_model):
                                        if chunk:
                                            full_answer += chunk
                                            # Real-time display update, add typewriter effect
                                            streaming_container.markdown(f"""
                                            <div class="chat-message assistant">
                                                <div class="avatar">🤖</div>
                                                <div>{full_answer}<span class="typing-cursor">|</span></div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            # Add small delay to simulate typing effect
                                            time.sleep(0.05)
                                    
                                    # Final display of complete answer (remove cursor)
                                    streaming_container.markdown(f"""
                                    <div class="chat-message assistant">
                                        <div class="avatar">🤖</div>
                                        <div>{full_answer}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                except Exception as e:
                                    full_answer = f"❌ Error occurred while generating answer: {str(e)}"
                                    streaming_container.markdown(f"""
                                    <div class="chat-message assistant">
                                        <div class="avatar">🤖</div>
                                        <div>{full_answer}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                full_answer = "Sorry, I cannot find relevant information from your emails."
                                st.markdown(f"""
                                <div class="chat-message assistant">
                                    <div class="avatar">🤖</div>
                                    <div>{full_answer}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            full_answer = "Sorry, I cannot find relevant information from your emails."
                            st.markdown(f"""
                            <div class="chat-message assistant">
                                <div class="avatar">🤖</div>
                                <div>{full_answer}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        error_msg = result.get("error", "Email query failed")
                        st.error(f"❌ {error_msg}")
                        
                        # Add error message to history
                        st.session_state.chat_history.append({
                            "content": error_msg,
                            "is_user": False,
                            "timestamp": datetime.now()
                        })
                    
                    if result.get("success"):
                        # After streaming output is complete, add to chat history
                        st.session_state.chat_history.append({
                            "content": full_answer,
                            "is_user": False,
                            "timestamp": datetime.now()
                        })
                    
                    # No need to re-render, chat history is already displayed at the top of the page
                    
                    # Display detailed information
                    with st.expander("🔍 Query Details"):
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
