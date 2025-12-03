import os
import multiprocessing
import threading
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger

# 修改导入路径，从 agent_builder_client 导入
from agent_builder_client.config import settings
from agent_builder_client.services.create_db import create_db_from_json
from agent_builder_client.services.client_query import get_rag_context_file_name, get_rag_context_with_file_content

# 日志配置标志，避免重复配置
_logger_configured = False

# 服务器启动标志和锁，防止重复启动
_server_started = False
_server_lock = threading.Lock()
_server_instance = None

def configure_logger():
    """配置日志（延迟初始化，避免重复配置）"""
    global _logger_configured
    if _logger_configured:
        return
    
    logger.remove()  # 移除默認處理器
    if settings.LOGGING_ENABLED:
        logger.add(
            settings.LOGGING_FILE_PATH,
            format=settings.LOGGING_FORMAT,
            level=settings.LOGGING_LEVEL,
            rotation=settings.LOGGING_ROTATION,
            retention=settings.LOGGING_RETENTION
        )
    _logger_configured = True

# 模块加载时配置日志（只执行一次）
configure_logger()

# FastAPI 應用程序實例
app = FastAPI(
    title="RAG API",
    description="檢索增強生成 (RAG) API 服務",
    version="1.0.0"
)

# 全局變量 - 緩存嵌入模型和 collection
current_embedding_model = None
current_model_path = None
current_collection = None
current_collection_key = None

# 初始化嵌入模型
def init_embedding_model():
    """初始化嵌入模型"""
    global current_embedding_model, current_model_path
    
    if current_embedding_model is None:
        try:
            logger.info(f"載入嵌入模型: {settings.EMBEDDING_MODEL_PATH}")
            current_embedding_model = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_PATH,
                model_kwargs={"device": settings.EMBEDDING_DEVICE},
                encode_kwargs={"normalize_embeddings": True}
            )
            current_model_path = settings.EMBEDDING_MODEL_PATH
            logger.info("✅ 嵌入模型載入完成")
        except Exception as e:
            logger.error(f"❌ 嵌入模型載入失敗: {e}")
            raise e

# 嵌入模型初始化标志，避免重复初始化
_embedding_initialized = False

def ensure_embedding_model():
    """確保嵌入模型已初始化（延遲初始化，避免重複執行）"""
    global _embedding_initialized, current_embedding_model
    
    # 如果已經初始化過，直接返回
    if _embedding_initialized and current_embedding_model is not None:
        return current_embedding_model
    
    # 檢查是否在子進程中（Windows multiprocessing spawn 模式）
    if hasattr(multiprocessing, 'current_process'):
        try:
            current_process = multiprocessing.current_process()
            if current_process.name != 'MainProcess':
                # 子進程中不初始化，返回 None
                return None
        except:
            pass
    
    # 在主進程中初始化
    try:
        init_embedding_model()
        _embedding_initialized = True
        return current_embedding_model
    except Exception as e:
        logger.error(f"模組初始化失敗: {e}")
        current_embedding_model = None
        return None

# 不在模組載入時自動初始化，改為延遲初始化
# 只在真正需要時（API 請求或手動啟動時）才初始化

# 創建狀態
create_status = "success"  # running, success, fail

# Pydantic 模型定義
class CreateDBRequest(BaseModel):
    json_path: str
    collection_name: str

class CreateDBResponse(BaseModel):
    success: bool
    message: str
    collection_name: Optional[str] = None
    document_count: Optional[int] = None

class QueryFileRequest(BaseModel):
    question: str
    collection_name: str

class QueryFileResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    question: Optional[str] = None
    chat_messages: Optional[List[Dict]] = None
    error: Optional[str] = None

class StatusResponse(BaseModel):
    status: str  # running, success, fail

# 輔助函數
def get_embedding_model():
    """獲取嵌入模型（如果未初始化則先初始化）"""
    if current_embedding_model is None:
        return ensure_embedding_model()
    return current_embedding_model

def get_collection(chroma_path: str, collection_name: str):
    """獲取或創建 Chroma collection（帶緩存）"""
    global current_collection, current_collection_key
    
    collection_key = f"{chroma_path}#{collection_name}"
    
    # 如果是相同的 collection，直接返回
    if current_collection is not None and current_collection_key == collection_key:
        logger.debug(f"使用緩存的 collection: {collection_name}")
        return current_collection
    
    # 創建新的 collection
    logger.info(f"載入新的 collection: {collection_name}")
    embedding_model = get_embedding_model()
    if embedding_model is None:
        raise HTTPException(status_code=500, detail="嵌入模型未載入，請重新啟動服務器")
    
    current_collection = Chroma(
        persist_directory=chroma_path,
        embedding_function=embedding_model,
        collection_name=collection_name
    )
    current_collection_key = collection_key
    
    return current_collection

def clear_collection_cache(collection_name: str = None):
    """清除 collection 緩存"""
    global current_collection, current_collection_key
    
    if collection_name:
        # 只清除特定 collection 的緩存
        if current_collection_key and collection_name in current_collection_key:
            logger.info(f"清除 collection 緩存: {collection_name}")
            current_collection = None
            current_collection_key = None
    else:
        # 清除所有 collection 緩存
        logger.info("清除所有 collection 緩存")
        current_collection = None
        current_collection_key = None


# API 端點
@app.get("/")
async def root():
    """根路徑，返回 API 信息"""
    return {
        "message": "RAG API 服務",
        "version": "1.0.0",
        "endpoints": {
            "create_db": "/create_db", 
            "query_group": "/query_group",
            "status": "/status",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "service": "RAG API"}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """獲取創建狀態"""
    return StatusResponse(status=create_status)

@app.post("/create_db", response_model=CreateDBResponse)
async def create_database(request: CreateDBRequest):
    """
    創建向量數據庫
    
    Args:
        request: CreateDBRequest 包含創建數據庫所需的參數
    
    Returns:
        CreateDBResponse: 創建結果
    """
    global create_status, current_vectorstore, current_vectorstore_key
    
    try:
        # 檢查是否正在創建
        if create_status == "running":
            raise HTTPException(status_code=409, detail="正在創建數據庫，請稍後再試")
        
        # 開始創建
        create_status = "running"
        
        # 驗證輸入路徑
        if not os.path.exists(request.json_path):
            raise HTTPException(status_code=400, detail=f"JSON 文件不存在: {request.json_path}")
        
        # 獲取嵌入模型
        embedding_model = get_embedding_model()
        if embedding_model is None:
            raise HTTPException(status_code=500, detail="嵌入模型未載入，請重新啟動服務器")
        
        # 創建數據庫
        vectorstore = create_db_from_json(
            json_path=request.json_path,
            chroma_path=settings.CHROMA_PATH,
            embedding_model=embedding_model,
            collection_name=request.collection_name
        )
        
        if vectorstore is None:
            raise HTTPException(status_code=500, detail="創建向量數據庫失敗")
        
        # 計算文檔數量
        try:
            collection = vectorstore._collection
            document_count = collection.count()
        except:
            document_count = None
        
        # 清除對應的 collection 緩存（因為創建了新的）
        clear_collection_cache(request.collection_name)
        
        # 完成創建
        create_status = "success"
        
        return CreateDBResponse(
            success=True,
            message="向量數據庫創建成功",
            collection_name=request.collection_name,
            document_count=document_count
        )
        
    except HTTPException:
        create_status = "fail"
        raise
    except Exception as e:
        create_status = "fail"
        raise HTTPException(status_code=500, detail=f"創建數據庫時發生錯誤: {str(e)}")

@app.post("/query_group", response_model=QueryFileResponse)
async def query_group_endpoint(request: QueryFileRequest):
    """
    查詢文件名端點
    
    Args:
        request: QueryFileRequest 包含查詢所需的參數
    
    Returns:
        QueryFileResponse: 查詢結果，包含建議的文件名、聊天消息和檢索內容
    """
    try:
        # 使用配置文件中的 chroma_path
        chroma_path = settings.CHROMA_PATH
        
        # 驗證輸入路徑
        if not os.path.exists(chroma_path):
            raise HTTPException(status_code=400, detail=f"Chroma 數據庫路徑不存在: {chroma_path}")
        
        # 獲取 collection（帶緩存）
        chroma = get_collection(chroma_path, request.collection_name)
        
        # 使用默認的 k 值
        k = settings.DEFAULT_TOP_K
        
        # 執行文件名查詢和聊天消息生成
        result = get_rag_context_with_file_content(
            chroma=chroma,
            question=request.question,
            collection_name=request.collection_name,
            k=k
        )
        
        if result.get('error'):
            # 如果有錯誤，返回錯誤信息
            return QueryFileResponse(
                success=False,
                filename=None,
                question=request.question,
                chat_messages=[],
                error=result['error']
            )
        else:
            # 成功情況
            return QueryFileResponse(
                success=True,
                filename=result['filename'],
                question=request.question,
                chat_messages=result['chat_messages'],
                error=""
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢文件時發生錯誤: {str(e)}")



def run_server():
    """啟動服務器的函數（可以被外部調用，避免重複執行）"""
    global _server_started, _server_instance
    
    import socket
    
    # 使用鎖確保線程安全，只允許一個執行緒啟動服務
    with _server_lock:
        if _server_started:
            logger.warning("⚠️ 服務器已經啟動，跳過重複啟動")
            return True
        # 標記正在啟動（若後續失敗會重設）
        _server_started = True
    
    try:
        # 確保嵌入模型已初始化
        embedding_model = ensure_embedding_model()
        if embedding_model is None:
            logger.error("❌ 嵌入模型未載入，請檢查配置")
            with _server_lock:
                _server_started = False
            return False
        else:
            logger.info("✅ 嵌入模型已準備就緒")
        
        logger.info("🚀 啟動 RAG API 服務器")
        logger.info(f"服務器地址: {settings.API_HOST}:{settings.API_PORT}")
        
        # 檢查端口是否可用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((settings.API_HOST, settings.API_PORT))
            sock.close()
        except OSError as e:
            if e.errno == 10048:  # Windows: 端口已被占用
                logger.error(f"❌ 端口 {settings.API_PORT} 已被占用，請關閉占用該端口的程序後重試")
                logger.error(f"   錯誤信息: {e}")
                with _server_lock:
                    _server_started = False
                return False
            else:
                with _server_lock:
                    _server_started = False
                raise
        
        # 使用 uvicorn.Server 和 Config 來精確控制啟動，避免重複導入
        try:
            config = uvicorn.Config(
                app=app,  # 直接傳遞 app 對象
                host=settings.API_HOST,
                port=settings.API_PORT,
                log_level="warning",  # 降低 uvicorn 日誌級別，使用我們的 loguru
                loop="asyncio"  # 明確指定事件循環
            )
            _server_instance = uvicorn.Server(config)
            _server_instance.run()  # 運行服務器（阻塞調用）
            return True
        except Exception as e:
            logger.error(f"❌ 服務器啟動失敗: {e}")
            return False
        finally:
            # 當伺服器結束或異常時，允許再次啟動
            with _server_lock:
                _server_started = False
                _server_instance = None
    except Exception:
        # 確保任何未捕捉的異常都能重置狀態
        with _server_lock:
            _server_started = False
            _server_instance = None
        raise

if __name__ == "__main__":
    import sys
    # 檢查是否在 multiprocessing 子進程中（Windows spawn 模式）
    # 如果是子進程，不執行主程序代碼
    try:
        if hasattr(multiprocessing, 'current_process'):
            current_process = multiprocessing.current_process()
            if hasattr(current_process, 'name') and current_process.name != 'MainProcess':
                # 這是 multiprocessing 子進程，不執行主程序
                sys.exit(0)
    except:
        pass
    
    success = run_server()
    if not success:
        sys.exit(1)

