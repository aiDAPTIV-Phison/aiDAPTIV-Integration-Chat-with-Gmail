import os
import json
import requests
import time
from typing import Dict, List, Optional
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import chromadb
import datetime
from loguru import logger

# 添加配置導入
from config import settings

def get_rag_context_file_name(chroma, question, k=5):
    """
    根據問題從 chroma 檢索相關內容，並返回應該使用的文件名和推理的聊天消息列表
    
    Args:
        chroma: Chroma 向量數據庫實例
        question: 用戶問題
        k: 檢索的 top-k 數量
    
    Returns:
        dict: {
            'filename': str,  # 選中的文件名（不含路徑，只有檔名）
            'chat_messages': List[dict],  # 推理的聊天消息列表
            'error': str  # 錯誤信息，成功時為空字符串
        }
    """
    try:
        # 從 chroma 檢索 top-k 相關文檔
        results = chroma.similarity_search_with_score(question, k=k)
        
        if not results:
            return {
                'filename': None,
                'chat_messages': [],
                'error': 'no search results found'
            }
        # 統計每個 source 的出現次數和相似度總和
        source_stats = {}
        all_chunks = []
        
        for doc, score in results:
            source = doc.metadata.get('source', '')
            chunk_content = doc.page_content
            all_chunks.append(chunk_content)
            
            if source:
                if source not in source_stats:
                    source_stats[source] = {
                        'count': 0,
                        'similarity_sum': 0.0,
                        'scores': [],
                        'chunks': []
                    }
                
                source_stats[source]['count'] += 1
                source_stats[source]['similarity_sum'] += score
                source_stats[source]['scores'].append(score)
                source_stats[source]['chunks'].append(chunk_content)
        
        if not source_stats:
            return {
                'filename': None,
                'chat_messages': [],
                'error': 'no valid sources found'
            }
        
        max_count = max(stats['count'] for stats in source_stats.values())
        top_sources = [source for source, stats in source_stats.items() 
                      if stats['count'] == max_count]
        
        if len(top_sources) == 1:
            selected_source = top_sources[0]
        else:
            best_source = None
            best_similarity_sum = float('inf')
            
            for source in top_sources:
                similarity_sum = source_stats[source]['similarity_sum']
                if similarity_sum < best_similarity_sum:
                    best_similarity_sum = similarity_sum
                    best_source = source
            
            selected_source = best_source
        
        logger.info(f"選擇的 source: {selected_source}")
        print(f"選擇的 source: {selected_source}")
        logger.debug(f"統計結果: {source_stats}")
        
        # 返回對應的 merge file 名稱（去掉副檔名，加上 .txt）
        source_filename = os.path.splitext(selected_source)[0]
        merge_file_name = f"{source_filename}.txt"
        
        # 構建推理聊天消息列表
        # 從指定的 txt 檔案中讀取內容作為 chunk
        try:
            # 需要從API端點傳入 collection_name 來構建完整路徑
            # 這裡暫時使用空字符串，將在API端點中處理
            merged_content = ""
            logger.warning("需要從API端點傳入collection_name來讀取merged file內容")
        except Exception as file_error:
            logger.error(f"讀取 merged file 失敗: {str(file_error)}")
            # 如果讀取檔案失敗，回退到使用檢索到的片段
            merged_content = "\n\n".join(all_chunks)
        
        # 創建用於推理的聊天消息
        chat_messages = []
        
        # 如果 system prompt 不為空，則添加 system 消息
        if settings.SYSTEM_PROMPT and settings.SYSTEM_PROMPT.strip():
            chat_messages.append({
                "role": "system",
                "content": settings.SYSTEM_PROMPT
            })
        
        # 添加 user 消息
        chat_messages.append({
            "role": "user", 
            "content": settings.USER_PROMPT_TEMPLATE.format(chunk=merged_content, query=question)
        })
        
        logger.info(f"建議的 merge file 名稱: {merge_file_name}")
        logger.info(f"生成了 {len(chat_messages)} 條聊天消息")
        logger.debug(f"檢索到 {len(all_chunks)} 個文檔片段")
        
        return {
            'filename': merge_file_name,
            'chat_messages': chat_messages,
            'error': ''
        }
            
    except Exception as e:
        logger.error(f"get_rag_context_file_name 發生錯誤: {str(e)}")
        return {
            'filename': None,
            'chat_messages': [],
            'error': f'internal error: {str(e)}'
        }


def get_rag_context_with_file_content(chroma, question, collection_name, k=5):
    """
    根據問題從 chroma 檢索相關內容，並從對應的 merged file 中讀取完整內容來構建聊天消息
    
    Args:
        chroma: Chroma 向量數據庫實例
        question: 用戶問題
        collection_name: 集合名稱，用於構建檔案路徑
        k: 檢索的 top-k 數量
    
    Returns:
        dict: {
            'filename': str,  # 選中的文件名（不含路徑，只有檔名）
            'chat_messages': List[dict],  # 推理的聊天消息列表
            'error': str  # 錯誤信息，成功時為空字符串
        }
    """
    try:
        # 從 chroma 檢索 top-k 相關文檔
        results = chroma.similarity_search_with_score(question, k=k)
        
        if not results:
            return {
                'filename': None,
                'chat_messages': [],
                'error': 'no search results found'
            }
        
        # 統計每個 source 的出現次數和相似度總和
        source_stats = {}
        all_chunks = []
        
        for doc, score in results:
            source = doc.metadata.get('source', '')
            chunk_content = doc.page_content
            all_chunks.append(chunk_content)
            
            if source:
                if source not in source_stats:
                    source_stats[source] = {
                        'count': 0,
                        'similarity_sum': 0.0,
                        'scores': [],
                        'chunks': []
                    }
                
                source_stats[source]['count'] += 1
                source_stats[source]['similarity_sum'] += score
                source_stats[source]['scores'].append(score)
                source_stats[source]['chunks'].append(chunk_content)
                logger.info(f"source: {source}, similarity_sum: {source_stats[source]['similarity_sum']}, scores: {source_stats[source]['scores']}")
        
        # logger.info(f"source_stats: {source_stats}")
        if not source_stats:
            return {
                'filename': None,
                'chat_messages': [],
                'error': 'no valid sources found'
            }
        
        max_count = max(stats['count'] for stats in source_stats.values())
        top_sources = [source for source, stats in source_stats.items() 
                      if stats['count'] == max_count]
        
        if len(top_sources) == 1:
            selected_source = top_sources[0]
        else:
            best_source = None
            best_similarity_sum = float('inf')
            
            for source in top_sources:
                similarity_sum = source_stats[source]['similarity_sum']
                if similarity_sum < best_similarity_sum:
                    best_similarity_sum = similarity_sum
                    best_source = source
            
            selected_source = best_source
        
        logger.info(f"選擇的 source: {selected_source}")
        logger.debug(f"統計結果: {source_stats}")
        
        # 返回對應的 merge file 名稱（去掉副檔名，加上 .txt）
        # source_filename = os.path.splitext(selected_source)[0]
        source_filename = selected_source
        merge_file_name = f"{source_filename}.txt"
        
        # 構建完整的 merged file 路徑
        merged_file_path = os.path.join(
            'test_data', 
            'gmail_inbox', 
            merge_file_name
        )
        
        # 從指定的 txt 檔案中讀取內容作為 chunk
        merged_content = ""
        try:
            logger.info(f"嘗試讀取 merged file: {merged_file_path}")
            
            if os.path.exists(merged_file_path):
                with open(merged_file_path, 'r', encoding='utf-8') as f:
                    merged_content = f.read()
                logger.info(f"成功讀取 merged file{merged_file_path}，內容長度: {len(merged_content)} 字符")
            else:
                logger.warning(f"Merged file 不存在: {merged_file_path}")
                return {
                    'filename': None,
                    'chat_messages': [],
                    'error': 'merge file not found'
                }
                
        except Exception as file_error:
            logger.error(f"讀取 merged file 失敗: {str(file_error)}")
            return {
                'filename': None,
                'chat_messages': [],
                'error': 'merge file not found'
            }
        
        # 創建用於推理的聊天消息
        chat_messages = []
        
        # 如果 system prompt 不為空，則添加 system 消息
        if settings.SYSTEM_PROMPT and settings.SYSTEM_PROMPT.strip():
            chat_messages.append({
                "role": "system",
                "content": settings.SYSTEM_PROMPT
            })
        
        # 添加 user 消息
        chat_messages.append({
            "role": "user", 
            "content": settings.USER_PROMPT_TEMPLATE.format(chunk=merged_content, query=question)
        })
        
        logger.info(f"建議的 merge file 名稱: {merge_file_name}")
        logger.info(f"生成了 {len(chat_messages)} 條聊天消息")
        logger.info(f"檢索到 {len(all_chunks)} 個文檔片段")
        
        return {
            'filename': merge_file_name,
            'chat_messages': chat_messages,
            'error': ''
        }
            
    except Exception as e:
        logger.error(f"get_rag_context_with_file_content 發生錯誤: {str(e)}")
        return {
            'filename': None,
            'chat_messages': [],
            'error': f'internal error: {str(e)}'
        }
