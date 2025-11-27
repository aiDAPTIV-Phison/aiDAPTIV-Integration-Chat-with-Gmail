
import os
import re
import socket
import subprocess
import sys
import time
import webbrowser

def check_python():
    try:
        subprocess.check_call(['python', '--version'], stdout=subprocess.PIPE)
        print("[SUCCESS] Python found:")
    except subprocess.CalledProcessError:
        print("[ERROR] Python is not installed or not in PATH. Please install Python 3.8+ first.")
        sys.exit(1)

def check_uv():
    try:
        subprocess.check_call(['uv', '--version'], stdout=subprocess.PIPE)
        print("[SUCCESS] uv found:")
    except subprocess.CalledProcessError:
        print("[WARNING] uv is not installed. Installing uv...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'uv'])
            print("[SUCCESS] uv installed successfully")
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to install uv. Please install it manually with: pip install uv")
            sys.exit(1)

def check_virtual_env():
    # Check project root .venv
    if not os.path.exists('.venv'):
        print("[INFO] Virtual environment not found in project root. Installing dependencies using uv...")
        if os.path.exists('requirements.txt'):
            print("[INFO] Installing main requirements...")
            subprocess.check_call(['uv', 'pip', 'install', '-r', 'requirements.txt'])
            print("[SUCCESS] All dependencies installed using uv")
    else:
        print("[SUCCESS] Virtual environment found in project root, skipping dependency installation")
    
    # Check agent_builder_client .venv
    agent_client_venv = os.path.join('agent_builder_client', '.venv')
    if not os.path.exists(agent_client_venv):
        print("[INFO] Virtual environment not found in agent_builder_client. Installing dependencies using uv...")
        agent_client_req = os.path.join('agent_builder_client', 'requirements.txt')
        if os.path.exists(agent_client_req):
            print("[INFO] Installing agent_builder_client requirements...")
            os.chdir('agent_builder_client')
            subprocess.check_call(['uv', 'pip', 'install', '-r', 'requirements.txt'])
            os.chdir('..')
            print("[SUCCESS] agent_builder_client dependencies installed using uv")
    else:
        print("[SUCCESS] Virtual environment found in agent_builder_client, skipping dependency installation")

def check_required_files():
    required_files = [
        "agent_builder_client/api.py",
        "streamlit_chat_ui.py",
        "agent_builder_client/config.py"
    ]
    for file in required_files:
        if not os.path.exists(file):
            print(f"[ERROR] Missing required file: {file}")
            sys.exit(1)
    print("[SUCCESS] All required files found")

def check_embedding_model():
    if not os.path.exists("multilingual-e5-large"):
        print("[WARNING] multilingual-e5-large model directory not found")
        print("[WARNING] Please download the model first:")
        print("[WARNING] git clone https://huggingface.co/intfloat/multilingual-e5-large")
        print("[WARNING] You can continue without it, but the API may not work properly")
    else:
        print("[SUCCESS] Embedding model found")

def get_streamlit_port(log_file='streamlit.log', max_wait=30, default_port=8501):
    """Detect the actual port Streamlit is running on by reading the log file"""
    # Try to read from log file
    for i in range(max_wait):
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Look for port patterns in streamlit output
                    # Pattern: "Local URL: http://localhost:8501" or "Network URL: http://192.168.x.x:8501"
                    patterns = [
                        r'Local URL:\s*http://[^:]+:(\d+)',
                        r'Network URL:\s*http://[^:]+:(\d+)',
                        r'http://localhost:(\d+)',
                        r'http://127\.0\.0\.1:(\d+)',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            port = int(matches[-1])  # Get the last match (most recent)
                            # Verify port is actually in use
                            if is_port_in_use(port):
                                return port
            except Exception as e:
                pass
        
        time.sleep(1)
    
    # Fallback: try common streamlit ports
    for port in range(default_port, default_port + 5):
        if is_port_in_use(port):
            return port
    
    # Last resort: return default
    return default_port

def is_port_in_use(port, host='localhost'):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.5)
            result = s.connect_ex((host, port))
            return result == 0
        except:
            return False

def start_services():
    print("[INFO] Starting FastAPI service in background...")
    os.chdir('agent_builder_client')
    subprocess.Popen(['uv', 'run', 'api.py'], stdout=open('../api.log', 'w'), stderr=subprocess.STDOUT)
    os.chdir('..')
    print("[SUCCESS] FastAPI service started in background (logs: api.log)")

    time.sleep(10)  # Wait for the API to start

    print("[INFO] Starting Streamlit UI in background...")
    subprocess.Popen(['uv', 'run', 'streamlit', 'run', 'streamlit_chat_ui.py', '--server.headless', 'true'], stdout=open('streamlit.log', 'w'), stderr=subprocess.STDOUT)
    print("[SUCCESS] Streamlit UI started in background (logs: streamlit.log)")

    print("[INFO] Detecting Streamlit port...")
    streamlit_port = get_streamlit_port()
    streamlit_url = f'http://localhost:{streamlit_port}'
    print(f"[SUCCESS] Streamlit is running on port {streamlit_port}")
    print(f"[INFO] Opening browser at {streamlit_url}...")
    webbrowser.open(streamlit_url)
    
    return streamlit_port

def get_project_root():
    """Get the project root directory, handling both script and exe execution"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        exe_path = os.path.dirname(os.path.abspath(sys.executable))
        # Exe is in aiDAPTIV_Files\Installer\, so go up 2 levels to project root
        project_root = os.path.dirname(os.path.dirname(exe_path))
    else:
        # Running as script
        project_root = os.path.dirname(os.path.abspath(__file__))
    return project_root

def main():
    # Change to project root directory
    project_root = get_project_root()
    os.chdir(project_root)
    print("==========================================")
    print("Gmail Chat Application Setup & Start")
    print("==========================================")

    check_python()
    check_uv()
    check_virtual_env()
    check_required_files()
    check_embedding_model()
    
    print()
    print("==========================================")
    print("Starting Services...")
    print("==========================================")

    streamlit_port = start_services()

    print()
    print("==========================================")
    print("Setup Complete!")
    print("==========================================")
    print("Services are now running:")
    print("    FastAPI: http://localhost:8080")
    print(f"    Streamlit UI: http://localhost:{streamlit_port}")
    print("Press any key to exit...")
    

if __name__ == '__main__':
    main()
    
    
# uv run pyinstaller --onefile --noconsole --name=app build_exe.py