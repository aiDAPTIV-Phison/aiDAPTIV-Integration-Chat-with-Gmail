#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail 郵件資料轉換成 chunks.json 格式的程式

這個程式會讀取 gmail_emails.json 檔案，將每封郵件轉換成 chunks.json 格式，
包含 page_content 和 metadata 欄位。
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


def clean_text(text: str) -> str:
    """清理文字內容，移除多餘的空白和特殊字符"""
    if not text:
        return ""
    
    # 移除 HTML 標籤
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除多餘的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除開頭和結尾的空白
    text = text.strip()
    
    return text


def extract_email_content(email: Dict[str, Any]) -> str:
    """從郵件中提取主要內容"""
    content_parts = []
    
    # 添加主題
    if email.get('subject'):
        content_parts.append(f"主題: {email['subject']}")
    
    # 添加寄件人
    if email.get('from'):
        content_parts.append(f"寄件人: {email['from']}")
    
    # 添加收件人
    if email.get('to'):
        content_parts.append(f"收件人: {email['to']}")
    
    # 添加日期
    if email.get('date'):
        content_parts.append(f"日期: {email['date']}")
    
    # 添加標籤
    if email.get('labelIds'):
        label_ids = email['labelIds']
        if isinstance(label_ids, list):
            labels_str = ", ".join(label_ids)
        else:
            labels_str = str(label_ids)
        content_parts.append(f"標籤: {labels_str}")
    
    # 添加郵件內容
    if email.get('body'):
        body = email['body']
        if isinstance(body, dict):
            # 優先使用 text 內容，如果沒有則使用 html
            if body.get('text'):
                email_content = clean_text(body['text'])
            elif body.get('html'):
                # 將 HTML 轉換為純文字
                if HTML2TEXT_AVAILABLE:
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    email_content = clean_text(h.handle(body['html']))
                else:
                    # 如果沒有 html2text，使用簡單的 HTML 標籤移除
                    email_content = clean_text(body['html'])
            else:
                email_content = ""
        else:
            email_content = clean_text(str(body))
        
        if email_content:
            content_parts.append(f"內容:\n{email_content}")
    
    return "\n\n".join(content_parts)


def create_chunk_metadata(email: Dict[str, Any], chunk_index: int) -> Dict[str, Any]:
    """創建 chunk 的 metadata"""
    return {
        "source": email.get('subject', 'unknown'),
        "source_file": email.get('subject', 'unknown'),
        "file_path": email.get('subject', 'unknown'),
        "file_type": ".txt",
        "loader": "gmail_email_loader",
        "processing_mode": "easy",
        "source_type": "gmail",
        "chunk_id": email.get('subject', 'unknown'),
        "chunk_index": 1
    }


def convert_gmail_to_chunks(gmail_file: str, output_file: str):
    """將 Gmail 郵件轉換成 chunks.json 格式"""
    
    print(f"正在讀取 Gmail 郵件檔案: {gmail_file}")
    
    try:
        with open(gmail_file, 'r', encoding='utf-8') as f:
            emails = json.load(f)
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 {gmail_file}")
        return
    except json.JSONDecodeError as e:
        print(f"錯誤: JSON 格式錯誤 - {e}")
        return
    
    print(f"成功讀取 {len(emails)} 封郵件")
    
    chunks = []
    
    for email_index, email in enumerate(emails):
        print(f"正在處理第 {email_index + 1} 封郵件...")
        
        # 提取郵件內容
        content = extract_email_content(email)
        
        if not content.strip():
            print(f"  警告: 第 {email_index + 1} 封郵件沒有內容，跳過")
            continue
        
        # 每封郵件就是一個完整的 chunk
        chunk_data = {
            "page_content": content,
            "metadata": create_chunk_metadata(email, 1)
        }
        chunks.append(chunk_data)
        
        print(f"  完成: 轉換為 1 個 chunk")
    
    # 寫入輸出檔案
    print(f"正在寫入輸出檔案: {output_file}")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print(f"轉換完成! 總共產生 {len(chunks)} 個 chunks")
        print(f"輸出檔案: {output_file}")
        
    except Exception as e:
        print(f"錯誤: 寫入檔案時發生錯誤 - {e}")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='將 Gmail 郵件轉換成 chunks.json 格式')
    parser.add_argument('--input', '-i', default='gmail_emails.json', 
                       help='輸入的 Gmail 郵件檔案 (預設: gmail_emails.json)')
    parser.add_argument('--output', '-o', default='./agent_builder_client/test_data/gmail_chunks.json', 
                       help='輸出的 chunks 檔案 (預設: gmail_chunks.json)')
    args = parser.parse_args()
    
    print("Gmail 郵件轉換成 chunks.json 格式")
    print("=" * 50)
    
    convert_gmail_to_chunks(args.input, args.output)


if __name__ == "__main__":
    main()
