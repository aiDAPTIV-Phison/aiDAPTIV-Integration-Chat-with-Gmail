import json
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from loguru import logger

         
def create_db_from_json(json_path, 
                        chroma_path, 
                        embedding_model,
                        collection_name):
    """
    從 JSON 文件創建 Chroma 向量數據庫
    
    Args:
        json_path (str): JSON 文件路径
        chroma_path (str): Chroma 數據庫存儲路径 (固定資料庫目錄)
        embedding_model: 嵌入模型
        collection_name (str): 集合名稱
    
    Returns:
        Chroma: 創建的向量數據庫實例
    """
    try:
        # 確保 Chroma 資料庫目錄存在
        os.makedirs(chroma_path, exist_ok=True)
        logger.info(f"使用 Chroma 資料庫目錄: {chroma_path}")
        
        # 檢查並刪除已存在的同名集合（Windows 兼容）
        try:
            collection = Chroma(
                persist_directory=chroma_path,
                collection_name=collection_name
            )
            collection_ids = collection.get()['ids']
            if collection_ids:
                collection.delete(ids=collection_ids)
            logger.info(f"已清空集合: {collection_name}")
        except Exception as e:
            logger.error(f"清空集合時發生錯誤: {str(e)}")
            
        # 溫和地清理 Chroma 進程（避免強制殺死）
        try:
            import psutil
            import time
            
            # 查找可能的 Chroma 相關進程
            chroma_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and any(keyword in proc.info['name'].lower() for keyword in ['chroma', 'python']):
                        cmdline = proc.info['cmdline']
                        if cmdline and any('chroma' in str(arg).lower() for arg in cmdline):
                            chroma_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if chroma_processes:
                logger.info(f"發現 {len(chroma_processes)} 個 Chroma 相關進程，嘗試溫和終止...")
                
                for proc in chroma_processes:
                    try:
                        # 首先嘗試溫和終止
                        proc.terminate()
                        logger.info(f"已發送終止信號給進程 {proc.pid}")
                        
                        # 等待進程自然終止（最多等待 5 秒）
                        proc.wait(timeout=5)
                        logger.info(f"進程 {proc.pid} 已正常終止")
                        
                    except psutil.TimeoutExpired:
                        logger.warning(f"進程 {proc.pid} 未在 5 秒內終止，嘗試強制終止")
                        try:
                            proc.kill()
                            logger.info(f"已強制終止進程 {proc.pid}")
                        except psutil.NoSuchProcess:
                            logger.info(f"進程 {proc.pid} 已經終止")
                    except psutil.NoSuchProcess:
                        logger.info(f"進程 {proc.pid} 已經終止")
                        
        except Exception as cleanup_e:
            logger.warning(f"清理進程時出現問題: {str(cleanup_e)}")
        
        # 讀取 JSON 文件
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 創建 Document 對象
        documents = []
        
        # 處理 JSON 數據，直接使用 page_content 和 metadata 字段
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'page_content' in item:
                    # 創建 Document 對象
                    doc = Document(
                        page_content=item['page_content'],
                        metadata=item.get('metadata', {})
                    )
                    documents.append(doc)
                else:
                    logger.warning(f"跳過無效項目，缺少 page_content 字段: {item}")
        
        elif isinstance(data, dict) and 'page_content' in data:
            # 如果是單個包含 page_content 的字典對象
            doc = Document(
                page_content=data['page_content'],
                metadata=data.get('metadata', {})
            )
            documents.append(doc)
        
        else:
            raise ValueError("JSON 格式不正確，應包含 'page_content' 字段")
        
        # 使用 from_documents 創建 Chroma 向量數據庫
        logger.info(f"正在使用 from_documents 創建向量數據庫...")
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding_model,
            persist_directory=chroma_path,
            collection_name=collection_name
        )
        
        # 持久化數據庫
        vectorstore.persist()
        logger.info("數據庫已持久化")
        
        logger.success(f"成功創建向量數據庫:")
        logger.info(f"- JSON 文件: {json_path}")
        logger.info(f"- 數據庫路径: {chroma_path}")
        logger.info(f"- 集合名稱: {collection_name}")
        logger.info(f"- 文檔數量: {len(documents)}")
        
        return vectorstore
        
    except FileNotFoundError:
        logger.error(f"找不到 JSON 文件 {json_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"JSON 文件格式無效 {json_path}")
        return None
    except Exception as e:
        logger.error(f"創建數據庫時發生錯誤: {str(e)}")
        return None 