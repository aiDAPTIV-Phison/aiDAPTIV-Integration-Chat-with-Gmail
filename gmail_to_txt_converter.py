#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将Gmail邮件转换为txt格式并以主旨命名文件
"""

import json
import os
import re
from pathlib import Path

def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    # 移除或替换Windows文件名中的非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    filename = re.sub(illegal_chars, '_', filename)
    # 限制文件名长度
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip()

def convert_emails_to_txt():
    """将邮件转换为txt文件"""
    
    # 创建输出目录
    output_dir = Path("./agent_builder_client/test_data/gmail_inbox")
    
    # 如果目录存在，先清空内容
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取邮件数据
    with open("gmail_emails.json", "r", encoding="utf-8") as f:
        emails = json.load(f)
    
    # print(f"找到 {len(emails)} 封邮件")
    
    converted_count = 0
    
    for i, email in enumerate(emails):
        try:
            # 获取邮件信息
            subject = email.get("subject", f"无主旨_{i+1}")
            from_addr = email.get("from", "未知发件人")
            to_addr = email.get("to", "未知收件人")
            date = email.get("date", "未知日期")
            
            # 获取邮件正文
            body_text = ""
            if "body" in email:
                if "text" in email["body"]:
                    body_text = email["body"]["text"]
                elif "html" in email["body"]:
                    # 简单的HTML到文本转换
                    html_text = email["body"]["html"]
                    # 移除HTML标签
                    import re
                    body_text = re.sub(r'<[^>]+>', '', html_text)
                    # 解码HTML实体
                    import html
                    body_text = html.unescape(body_text)
            
            # 如果没有正文，使用摘要
            if not body_text.strip():
                body_text = email.get("snippet", "")
            
            # 创建文件内容
            content = f"""主旨: {subject}
发件人: {from_addr}
收件人: {to_addr}
日期: {date}

{body_text}
"""
            
            # 清理文件名
            safe_subject = sanitize_filename(subject)
            if not safe_subject:
                safe_subject = f"邮件_{i+1}"
            
            # 确保文件名唯一
            filename = f"{safe_subject}.txt"
            filepath = output_dir / filename
            
            # 如果文件已存在，添加序号
            counter = 1
            while filepath.exists():
                filename = f"{safe_subject}_{counter}.txt"
                filepath = output_dir / filename
                counter += 1
            
            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            converted_count += 1
            # print(f"已转换: {filename}")
            
        except Exception as e:
            # print(f"转换第 {i+1} 封邮件时出错: {e}")
            continue
    
    # print(f"\n转换完成！共转换了 {converted_count} 封邮件")
    # print(f"文件保存在: {output_dir.absolute()}")

if __name__ == "__main__":
    convert_emails_to_txt()
