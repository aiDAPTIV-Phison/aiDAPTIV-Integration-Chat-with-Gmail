import requests
import json
import time

# API 基礎 URL
BASE_URL = "http://localhost:8080"

def test_health_check():
    """測試健康檢查"""
    print("=== 測試健康檢查 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"錯誤: {e}")
        return False

def test_api_info():
    """測試 API 信息"""
    print("\n=== 測試 API 信息 ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"錯誤: {e}")
        return False

def test_status():
    """測試狀態查詢"""
    print("\n=== 測試狀態查詢 ===")
    try:
        response = requests.get(f"{BASE_URL}/status")
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"錯誤: {e}")
        return False

def test_create_db():
    """測試創建數據庫"""
    print("\n=== 測試創建數據庫 ===")
    
    # 示例請求數據
    create_data = {
        "json_path": r".\test_data\chunks.json",
        "collection_name": "test_collection"
    }
    
    try:
        print(f"發送請求數據: {json.dumps(create_data, indent=2, ensure_ascii=False)}")
        response = requests.post(
            f"{BASE_URL}/create_db",
            json=create_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"錯誤: {e}")
        return False

    create_data = {
        "json_path": r".\test_data\chunks.json",
        "collection_name": "test_collection"
    }
    
    try:
        print(f"發送請求數據: {json.dumps(create_data, indent=2, ensure_ascii=False)}")
        response = requests.post(
            f"{BASE_URL}/create_db",
            json=create_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"錯誤: {e}")
        return False
    return response.status_code == 200


def test_query_group():
    """測試查詢文件組"""
    print("\n=== 測試查詢文件組 ===")
    
    # 示例請求數據
    query_data = {
        "question": "請介紹一下Qwen3-4B-Thinking模型的特點",
        "collection_name": "test_collection"
    }
    
    try:
        print(f"發送請求數據: {json.dumps(query_data, indent=2, ensure_ascii=False)}")
        response = requests.post(
            f"{BASE_URL}/query_group",
            json=query_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"狀態碼: {response.status_code}")
        response_data = response.json()
        print(f"響應: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # 如果成功，顯示詳細信息
        if response_data.get("success"):
            if response_data.get("filename"):
                print(f"📁 推薦的 merge file: {response_data['filename']}")
            
            if response_data.get("chat_messages"):
                print(f"💬 聊天消息數量: {len(response_data['chat_messages'])}")
                
                # 顯示聊天消息的詳細信息
                for i, msg in enumerate(response_data['chat_messages']):
                    role = msg.get('role', 'unknown')
                    content_preview = msg.get('content', '')[:100] + "..." if len(msg.get('content', '')) > 100 else msg.get('content', '')
                    print(f"  消息 {i+1} ({role}): {content_preview}")
                
                # 如果想看完整的user消息內容（包含RAG prompt）
                user_input = input("\n是否顯示完整的聊天消息內容？(y/n): ")
                if user_input.lower() == 'y':
                    for i, msg in enumerate(response_data['chat_messages']):
                        print(f"\n--- 消息 {i+1} ({msg.get('role')}) ---")
                        print(msg.get('content', ''))
                        print("-" * 50)
        else:
            error_msg = response_data.get("error", "未知錯誤")
            print(f"❌ 查詢失敗: {error_msg}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"錯誤: {e}")
        return False

def test_query_group_simple():
    """簡單的查詢測試（不顯示詳細內容）"""
    print("\n=== 簡單查詢測試 ===")
    
    test_questions = [
        "Qwen3-4B-Thinking模型有什麼特點？",
        "gpt-oss模型的特色功能是什麼？",
        "高能量可見光對眼睛有什麼影響？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n--- 測試問題 {i} ---")
        query_data = {
            "question": question,
            "collection_name": "test_collection"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/query_group",
                json=query_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ 問題: {question}")
                    print(f"📁 推薦文件: {data.get('filename', 'N/A')}")
                    print(f"💬 聊天消息數: {len(data.get('chat_messages', []))}")
                else:
                    error_msg = data.get('error', '未知錯誤')
                    print(f"❌ 查詢失敗: {error_msg}")
                    if error_msg == "merge file not found":
                        print("   ℹ️  這表示對應的merged file不存在於指定路徑")
                    elif error_msg == "no search results found":
                        print("   ℹ️  沒有找到相關的檢索結果")
                    elif error_msg == "no valid sources found":
                        print("   ℹ️  沒有找到有效的來源文檔")
            else:
                print(f"❌ HTTP錯誤: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 請求錯誤: {e}")

def test_merge_file_not_found():
    """測試merge file不存在的情況"""
    print("\n=== 測試 Merge File 不存在情況 ===")
    
    # 使用一個不存在的collection來測試
    query_data = {
        "question": "測試問題",
        "collection_name": "non_existent_collection"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/query_group",
            json=query_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"響應: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if not data.get("success") and data.get("error") == "merge file not found":
                print("✅ 正確返回 'merge file not found' 錯誤")
            else:
                print("❌ 未正確處理merge file不存在的情況")
        else:
            print(f"❌ HTTP錯誤: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 請求錯誤: {e}")

def monitor_create_status():
    """監控創建狀態"""
    print("\n=== 監控創建狀態 ===")
    for i in range(10):  # 最多檢查 10 次
        try:
            response = requests.get(f"{BASE_URL}/status")
            status = response.json()["status"]
            print(f"第 {i+1} 次檢查 - 狀態: {status}")
            
            if status == "success":
                print("✅ 創建成功！")
                break
            elif status == "fail":
                print("❌ 創建失敗！")
                break
            elif status == "running":
                print("⏳ 正在創建中...")
                time.sleep(2)  # 等待 2 秒後再檢查
            
        except Exception as e:
            print(f"檢查狀態時出錯: {e}")
            break

    
    
def main():
    """主測試函數"""
    print("🚀 開始測試 RAG API")
    print("確保 API 服務器正在運行於 http://localhost:8080")
    
    # 基礎測試
    if not test_health_check():
        print("❌ 健康檢查失敗，請確認 API 服務器是否啟動")
        return
    
    test_api_info()
    test_status()
    
    # 進階測試（需要實際的數據文件）
    print("\n" + "="*50)
    print("⚠️  以下測試需要實際的數據文件")

    user_input = input("是否繼續測試創建數據庫？(y/n): ")
    if user_input.lower() == 'y':
        # 測試創建數據庫
        #test_create_db()

        if True: #test_create_db():
            #監控創建狀態
            monitor_create_status()
            
            # 測試查詢
            time.sleep(1)
            print("\n" + "="*50)
            
            # 選擇測試模式
            test_mode = input("選擇測試模式 - (1)詳細測試 (2)簡單測試 (3)測試錯誤處理: ")
            if test_mode == "1":
                test_query_group()
            elif test_mode == "2":
                test_query_group_simple()
            else:
                test_merge_file_not_found()
    
    print("\n✅ 測試完成！")

if __name__ == "__main__":
    main() 