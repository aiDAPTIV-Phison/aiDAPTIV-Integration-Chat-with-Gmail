import requests

url = 'http://localhost:8080/create_db'
data = {
    "json_path": "test_data/gmail_chunks.json",  
    "collection_name": "ptest9109"      
}

response = requests.post(url, json=data)
print(response.json())