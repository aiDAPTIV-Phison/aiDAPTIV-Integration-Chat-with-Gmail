#!/usr/bin/env python3
"""
Gmail信件抓取工具
從Gmail帳戶抓取所有信件並儲存為JSON格式
"""

import os
import json
import base64
import pickle
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API 範圍
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# 可執行檔所在目錄（打包後）或目前檔案所在目錄（開發環境）
APP_BASE_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.resolve()
CREDENTIALS_DEFAULT_PATH = APP_BASE_DIR / "credentials.json"
GMAIL_EMAILS_DEFAULT_PATH = APP_BASE_DIR / "gmail_emails.json"
TOKEN_DEFAULT_PATH = APP_BASE_DIR / "token.pickle"
LOG_FILE = APP_BASE_DIR / "streamlit.log"

# 設定日誌 - 輸出到與執行檔同目錄的 streamlit.log
# 由於 gmail_fetcher.py 通過 subprocess 運行，是獨立進程，需要單獨配置日誌
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 檢查是否已經有文件處理器指向 streamlit.log
log_file_str = str(LOG_FILE.resolve())
has_file_handler = False
for handler in root_logger.handlers:
    if isinstance(handler, logging.FileHandler):
        try:
            # 比較絕對路徑
            handler_path = str(Path(handler.baseFilename).resolve())
            if handler_path == log_file_str:
                has_file_handler = True
                break
        except:
            pass

# 如果沒有文件處理器，添加一個
if not has_file_handler:
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)

# 確保有控制台處理器（用於 subprocess 輸出）
has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
                         for h in root_logger.handlers)
if not has_console_handler:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

class GmailFetcher:
    """Gmail信件抓取器"""
    
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        初始化Gmail抓取器
        
        Args:
            credentials_file: Google OAuth2 憑證檔案路徑
            token_file: 存取權杖檔案路徑
        """
        credentials_path = Path(credentials_file) if credentials_file else CREDENTIALS_DEFAULT_PATH
        token_path = Path(token_file) if token_file else TOKEN_DEFAULT_PATH
        self.credentials_file = credentials_path
        self.token_file = token_path
        self.service = None
        self.creds = None
        
    def authenticate(self) -> Tuple[bool, Optional[str]]:
        """
        進行Gmail API認證
        
        Returns:
            tuple[bool, Optional[str]]: (認證是否成功, 錯誤訊息)
        """
        try:
            # 載入已儲存的憑證
            if self.token_file.exists():
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # 如果沒有有效的憑證，則進行OAuth2流程
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                    except Exception as e:
                        error_msg = f"刷新憑證失敗: {str(e)}"
                        logger.error(error_msg)
                        return False, error_msg
                else:
                    if not self.credentials_file.exists():
                        error_msg = f"找不到憑證檔案: {self.credentials_file}\n請先下載Google OAuth2憑證檔案並命名為credentials.json"
                        logger.error(error_msg)
                        return False, error_msg
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES)
                        self.creds = flow.run_local_server(port=0)
                    except Exception as e:
                        error_msg = f"OAuth2認證流程失敗: {str(e)}"
                        logger.error(error_msg)
                        return False, error_msg
                
                # 儲存憑證供下次使用
                try:
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(self.creds, token)
                except Exception as e:
                    error_msg = f"儲存憑證失敗: {str(e)}"
                    logger.error(error_msg)
                    return False, error_msg
            
            # 建立Gmail API服務
            try:
                self.service = build('gmail', 'v1', credentials=self.creds)
                logger.info("Gmail API認證成功")
                return True, None
            except Exception as e:
                error_msg = f"建立Gmail API服務失敗: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            
        except Exception as e:
            error_msg = f"認證失敗: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_message_list(self, query: str = '', max_results: int = None) -> List[Dict[str, Any]]:
        """
        獲取信件列表
        
        Args:
            query: Gmail搜尋查詢字串 (例如: 'is:unread', 'from:example@gmail.com')
            max_results: 最大結果數量，None表示獲取所有信件
            
        Returns:
            List[Dict]: 信件列表
        """
        if not self.service:
            logger.error("請先進行認證")
            return []
        
        try:
            messages = []
            page_token = None
            
            while True:
                # 準備請求參數
                request_params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': 500  # 每次最多500封
                }
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                # 發送請求
                results = self.service.users().messages().list(**request_params).execute()
                message_list = results.get('messages', [])
                
                if not message_list:
                    break
                
                messages.extend(message_list)
                logger.info(f"已獲取 {len(messages)} 封信件")
                
                # 檢查是否還有更多頁面
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                
                # 如果設定了最大結果數量，檢查是否已達到
                if max_results and len(messages) >= max_results:
                    messages = messages[:max_results]
                    break
            
            logger.info(f"總共獲取 {len(messages)} 封信件")
            return messages
            
        except HttpError as error:
            logger.error(f"獲取信件列表失敗: {error}")
            return []
    
    def get_message_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取信件詳細內容
        
        Args:
            message_id: 信件ID
            
        Returns:
            Dict: 信件詳細內容
        """
        if not self.service:
            logger.error("請先進行認證")
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(message)
            
        except HttpError as error:
            logger.error(f"獲取信件詳細內容失敗 (ID: {message_id}): {error}")
            return None
    
    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析信件內容
        
        Args:
            message: Gmail API返回的原始信件資料
            
        Returns:
            Dict: 解析後的信件資料
        """
        headers = message.get('payload', {}).get('headers', [])
        
        # 提取信件標頭資訊
        parsed_message = {
            'id': message.get('id'),
            'threadId': message.get('threadId'),
            'labelIds': message.get('labelIds', []),
            'snippet': message.get('snippet', ''),
            'sizeEstimate': message.get('sizeEstimate', 0),
            'historyId': message.get('historyId'),
            'internalDate': message.get('internalDate'),
            'date': self._format_date(message.get('internalDate')),
        }
        
        # 提取標頭欄位
        header_fields = ['From', 'To', 'Subject', 'Date', 'Cc', 'Bcc', 'Reply-To']
        illegal_chars = r'[<>:"/\\|?*!~]'
        for header in headers:
            name = header.get('name', '')
            value = header.get('value', '')
            if name in header_fields:
                # 如果是 Subject，移除非法字符
                if name == 'Subject':
                    value = re.sub(illegal_chars, '_', value)
                parsed_message[name.lower().replace('-', '_')] = value
        
        # 提取信件內容
        parsed_message['body'] = self._extract_body(message.get('payload', {}))
        
        return parsed_message
    
    def _extract_body(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """
        提取信件內容
        
        Args:
            payload: 信件payload
            
        Returns:
            Dict: 包含純文字和HTML內容的字典
        """
        body = {'text': '', 'html': ''}
        
        # 檢查是否有parts（多部分信件）
        if 'parts' in payload:
            for part in payload['parts']:
                self._extract_part_body(part, body)
        else:
            # 單一部分信件
            self._extract_part_body(payload, body)
        
        return body
    
    def _extract_part_body(self, part: Dict[str, Any], body: Dict[str, str]):
        """
        提取信件部分的內容
        
        Args:
            part: 信件部分
            body: 內容字典
        """
        mime_type = part.get('mimeType', '')
        
        if mime_type == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                body['text'] = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        elif mime_type == 'text/html':
            data = part.get('body', {}).get('data', '')
            if data:
                body['html'] = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # 遞歸處理子部分
        if 'parts' in part:
            for subpart in part['parts']:
                self._extract_part_body(subpart, body)
    
    def _format_date(self, timestamp: Optional[str]) -> str:
        """
        格式化時間戳
        
        Args:
            timestamp: Unix時間戳（毫秒）
            
        Returns:
            str: 格式化的日期字串
        """
        if not timestamp:
            return ''
        
        try:
            # 轉換毫秒為秒
            dt = datetime.fromtimestamp(int(timestamp) / 1000)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return ''
    
    def fetch_all_emails(self, query: str = '', max_results: int = None, 
                        save_to_file: str = None) -> List[Dict[str, Any]]:
        """
        抓取所有信件
        
        Args:
            query: Gmail搜尋查詢字串
            max_results: 最大結果數量
            save_to_file: 儲存檔案的檔案名
            
        Returns:
            List[Dict]: 所有信件的詳細內容
        """
        logger.info("開始抓取Gmail信件...")
        
        # 獲取信件列表
        message_list = self.get_message_list(query, max_results)
        if not message_list:
            logger.warning("沒有找到任何信件")
            return []
        
        # 獲取每封信件的詳細內容
        all_emails = []
        total = len(message_list)
        
        for i, message_info in enumerate(message_list, 1):
            logger.info(f"正在處理信件 {i}/{total} (ID: {message_info['id']})")
            
            email_details = self.get_message_details(message_info['id'])
            if email_details:
                all_emails.append(email_details)
        
        logger.info(f"成功抓取 {len(all_emails)} 封信件")
        
        # 儲存到檔案
        if save_to_file:
            self.save_emails_to_file(all_emails, save_to_file)
        
        return all_emails
    
    def save_emails_to_file(self, emails: List[Dict[str, Any]], filename: str):
        """
        將信件儲存到JSON檔案
        
        Args:
            emails: 信件列表
            filename: 檔案名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(emails, f, ensure_ascii=False, indent=2)
            logger.info(f"信件已儲存到: {filename}")
        except Exception as e:
            logger.error(f"儲存檔案失敗: {str(e)}")


def main():
    """主程式"""
    
    print("Gmail信件抓取工具")
    print("=" * 50)
    
    # 建立Gmail抓取器
    fetcher = GmailFetcher()
    
    # 進行認證
    auth_success, error_msg = fetcher.authenticate()
    if not auth_success:
        error_output = f"認證失敗，程式結束"
        if error_msg:
            error_output += f"\n錯誤訊息: {error_msg}"
        print(error_output, file=sys.stderr)
        return
    
    # 檢查是否為非交互模式（從UI調用）
    if len(sys.argv) > 1 and sys.argv[1] == "--ui-mode":
        # UI模式：使用默認參數
        query = ""
        max_results = None
        print("UI模式：使用默認參數抓取所有信件")
    else:
        # 交互模式：詢問用戶參數
        query = input("請輸入Gmail搜尋查詢 (留空表示所有信件): ").strip()
        max_results_input = input("請輸入最大信件數量 (留空表示無限制): ").strip()
        max_results = int(max_results_input) if max_results_input.isdigit() else None
    
    # 生成檔案名
    # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = str(GMAIL_EMAILS_DEFAULT_PATH)  # f"gmail_emails_{timestamp}.json"
    
    # 抓取信件
    emails = fetcher.fetch_all_emails(
        query=query,
        max_results=max_results,
        save_to_file=filename
    )
    
    if emails:
        print(f"\n成功抓取 {len(emails)} 封信件")
        print(f"信件已儲存到: {filename}")
        
        # 顯示統計資訊
        print("\n統計資訊:")
        print(f"- 總信件數: {len(emails)}")
        
        # 統計發件人
        senders = {}
        for email in emails:
            sender = email.get('from', 'Unknown')
            senders[sender] = senders.get(sender, 0) + 1
        
        print(f"- 發件人數量: {len(senders)}")
        print("\n前10個發件人:")
        for sender, count in sorted(senders.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {sender}: {count} 封")
    else:
        print("沒有抓取到任何信件")


if __name__ == "__main__":
    main()
