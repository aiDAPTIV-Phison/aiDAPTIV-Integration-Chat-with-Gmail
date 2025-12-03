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
API_BASE_URL = "http://localhost:8081"

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
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        return {"success": False, "error": f"Query failed: {str(e)}"}

def load_email_data():
    """Load emails"""
    try:
        # Try to load gmail_emails.json
        emails_file = "./aiDAPTIV_Files/Example/Files/previous_emails.json"
        if os.path.exists(emails_file):
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
        if not os.path.exists("./aiDAPTIV_Files/Example/Files/credentials.json"):
            return False, "Cannot find credentials.json file, please set up Google OAuth2 credentials first"
        
        # Execute gmail_fetcher.py using UI mode
        result = subprocess.run([sys.executable, "gmail_fetcher.py", "--ui-mode"], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Check if gmail_emails.json was generated
            if os.path.exists("gmail_emails.json"):
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
                              capture_output=True, text=True, timeout=60)
        
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
                              capture_output=True, text=True, timeout=60)
        
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
        previous_emails_file = "./aiDAPTIV_Files/Example/Files/previous_emails.json"
        current_emails_file = "./aiDAPTIV_Files/Example/Files/gmail_emails.json"
        
        if not os.path.exists(current_emails_file):
            return [], "No current email file found"
        
        # Read current emails
        with open(current_emails_file, 'r', encoding='utf-8') as f:
            current_emails = json.load(f)
        
        # If no previous records, all emails are new
        if not os.path.exists(previous_emails_file):
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
        previous_emails_file = "./aiDAPTIV_Files/Example/Files/previous_emails.json"
        
        # Read existing previous_emails
        existing_emails = []
        if os.path.exists(previous_emails_file):
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
    try:
        # Step 1: Query database
        user_question = f"Summarize {email.get('subject', 'No Subject')} content"
        result = query_database(user_question, "gmail_inbox")
        
        if not result.get("success"):
            return False, f"Database query failed: {result.get('error', 'Unknown error')}"
        
        # Step 2: Get chat messages
        chat_messages = result.get("chat_messages", [])
        if not chat_messages:
            return False, "No chat messages retrieved"
        
        # Find user message
        user_message = None
        for msg in chat_messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            return False, "No user message found"
        
        # Step 3: Call vLLM API for summarization (non-streaming)
        summary = call_vllm_api_non_streaming(user_message, vllm_endpoint, model_name)
        
        if summary.startswith("❌"):
            return False, f"vLLM API call failed: {summary}"
        
        return True, summary
        
    except Exception as e:
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
                    # Save file locally
                    with open("./aiDAPTIV_Files/Example/Files/credentials.json", "wb") as f:
                        f.write(file_content)
                    
                    st.success("✅ File upload successful!")
                    # st.success(f"✅ {validation_message}")
                    # st.rerun()  # Rerun to update status
                else:
                    st.error(f"❌ {validation_message}")
                    
            except Exception as e:
                st.error(f"❌ Error occurred while uploading file: {str(e)}")
        
        # Check credentials.json
        if os.path.exists("./aiDAPTIV_Files/Example/Files/credentials.json"):
            st.success("✅ Google OAuth2 credentials uploaded")
            
            # Fetch Button
            if st.button("🔄 Fetch Emails", use_container_width=True):
                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Fetch Gmail emails
                status_text.text("Step 1/5: Fetching emails...")
                progress_bar.progress(15)
                
                success, message = fetch_gmail_emails()
                
                if success:
                    progress_bar.progress(25)
                    status_text.text("Step 1/5: Gmail fetching completed")
                    st.success(message)
                    
                    # Step 2: Convert to txt file
                    status_text.text("Step 2/5: Converting to txt file...")
                    progress_bar.progress(40)
                    
                    txt_success, txt_message = convert_emails_to_txt()
                    
                    if txt_success:
                        progress_bar.progress(55)
                        status_text.text("Step 2/5: txt file conversion completed")
                        st.success(txt_message)
                        
                        # Step 3: Convert to chunks
                        status_text.text("Step 3/5: Converting to chunks format...")
                        progress_bar.progress(70)
                        
                        chunks_success, chunks_message = convert_emails_to_chunks()
                        if chunks_success:
                            status_text.text("Step 3/5: chunks format conversion completed")
                            st.success(chunks_message)
                        else:
                            status_text.text("Step 3/5: chunks format conversion failed")
                            st.error(chunks_message)
                            
                        # Step 4:
                        status_text.text("Step 4/5: Creating database...")
                        db_success, db_message = create_db(json_path="test_data/gmail_chunks.json", collection_name='gmail_inbox')
                        if db_success:
                            status_text.text("Step 4/5: Database creation completed")
                            st.success(db_message)
                        else:
                            status_text.text("Step 4/5: Database creation failed")
                            st.error(db_message)

                        # Step 5: Detect new emails and process automatically
                        if chunks_success and db_success:
                            status_text.text("Step 5/5: Detecting new emails and processing automatically...")
                            progress_bar.progress(90)
                            
                            # Detect new emails
                            new_emails, detect_message = detect_new_emails()
                            
                            if new_emails:
                                st.info(f"🔍 {detect_message}")
                                
                                # Automatically process each new email
                                processed_count = 0
                                successfully_processed_emails = []  # Collect successfully processed emails
                                
                                for i, new_email in enumerate(new_emails):
                                    try:
                                        st.write(f"📧 Processing new email {i+1}/{len(new_emails)}: {new_email.get('subject', 'No Subject')}")
                                        
                                        # Automatically process email
                                        success, result_message = process_new_email_automatically(new_email, vllm_endpoint, selected_model)
                                        
                                        if success:
                                            processed_count += 1
                                            successfully_processed_emails.append(new_email)  # Add to successfully processed list
                                            st.success(f"✅ Email {i+1} - {new_email.get('subject', 'No Subject')} processed successfully")
                                            # Can add summary result display here, but not showing results as per requirements
                                        else:
                                            st.warning(f"⚠️ Email {i+1} processing failed: {result_message}")
                                            
                                    except Exception as e:
                                        st.error(f"❌ Error occurred while processing email {i+1}: {str(e)}")
                                
                                # Only successfully processed emails are added to previous_emails.json
                                if successfully_processed_emails:
                                    updated_count = update_previous_emails(successfully_processed_emails)
                                    st.success(f"🎉 Successfully processed {processed_count} new emails, processing records updated")
                                else:
                                    st.info("ℹ️ No emails processed successfully, processing records not updated")
                            else:
                                st.info(f"ℹ️ {detect_message}")
                        
                        if chunks_success:
                            progress_bar.progress(100)
                            status_text.text("Completed: All steps completed")
                            st.success(chunks_message)
                            st.info("Email data updated, page will refresh automatically")
                            
                            # Clear progress bar
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Auto refresh
                            time.sleep(2)
                            st.rerun()
                        else:
                            progress_bar.empty()
                            status_text.empty()
                            st.error(f"chunks conversion failed: {chunks_message}")
                    else:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"txt conversion failed: {txt_message}")
                else:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"Fetching failed: {message}")
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
