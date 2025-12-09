# -*- coding: utf-8 -*-
"""
Gmail Chat Application Setup & Start Script
"""

import os
import re
import socket
import subprocess
import sys
import time
import webbrowser
import atexit
import tempfile
import traceback

# 在模块级检查是否是子进程（通过环境变量）
# 如果设置了 STREAMLIT_CHILD_PROCESS 环境变量，说明这是子进程，应该只执行特定任务
if os.environ.get('STREAMLIT_CHILD_PROCESS') == '1':
    # 这是 Streamlit 子进程，不应该执行主程序逻辑
    # 让 Streamlit 启动脚本处理
    pass
elif __name__ != "__main__":
    # 如果不是主模块，可能是被 multiprocessing 导入的子进程
    # 检查是否是 multiprocessing 子进程
    try:
        import multiprocessing
        # 在 spawn 模式下，子进程启动时会重新导入模块
        # 检查进程名称，如果不是 MainProcess，说明是子进程
        if hasattr(multiprocessing, 'current_process'):
            current_process = multiprocessing.current_process()
            if hasattr(current_process, 'name') and current_process.name != 'MainProcess':
                # 这是 multiprocessing 子进程，立即退出，不执行任何代码
                # 注意：这里不能导入太多东西，只能执行必要的检查然后退出
                sys.exit(0)
    except Exception:
        # 如果无法检查（可能是正常的模块导入），继续执行
        # 但这种情况不应该发生，因为 multiprocessing 应该已经初始化
        pass

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        # Python 3.7+ 支持 reconfigure
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        # 设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except (AttributeError, ValueError):
        # 如果 reconfigure 不可用，尝试其他方法
        pass

# 确保虚拟环境在 Python 路径中
def ensure_venv_in_path():
    """确保虚拟环境在 Python 路径中（仅在开发环境中）"""
    # 打包后的 exe 不需要虚拟环境，因为所有依赖都已打包
    if getattr(sys, 'frozen', False):
        return False
    
    project_root = get_project_root()
    venv_path = os.path.join(project_root, '.venv')
    if os.path.exists(venv_path):
        if sys.platform == 'win32':
            site_packages = os.path.join(venv_path, 'Lib', 'site-packages')
        else:
            site_packages = os.path.join(venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
        
        if os.path.exists(site_packages) and site_packages not in sys.path:
            sys.path.insert(0, site_packages)
            return True
    return False

def check_python():
    """检查 Python（仅在开发环境中）"""
    # 打包后的 exe 不需要检查 Python，因为已经打包了 Python 运行时
    if getattr(sys, 'frozen', False):
        return
    
    try:
        subprocess.check_call(['python', '--version'], stdout=subprocess.PIPE)
        print("[SUCCESS] Python found:")
    except subprocess.CalledProcessError:
        print("[ERROR] Python is not installed or not in PATH. Please install Python 3.8+ first.")
        sys.exit(1)

def check_uv():
    """检查 uv（仅在开发环境中）"""
    # 打包后的 exe 不需要检查 uv，因为所有依赖都已打包
    if getattr(sys, 'frozen', False):
        return
    
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
    """检查并创建虚拟环境（仅在开发环境中）"""
    # 打包后的 exe 不需要虚拟环境，因为所有依赖都已打包
    if getattr(sys, 'frozen', False):
        print("[INFO] Running as packaged exe, skipping virtual environment setup")
        return
    
    # 获取项目根目录
    project_root = get_project_root()
    venv_path = os.path.join(project_root, '.venv')
    venv_exists = os.path.exists(venv_path)
    
    if not venv_exists:
        print("[INFO] Virtual environment not found in project root. Creating virtual environment using uv...")
        try:
            # Create virtual environment first
            subprocess.check_call(['uv', 'venv', '--python', '3.12.11', venv_path])
            print("[SUCCESS] Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to create virtual environment: {e}")
            print("[INFO] Trying alternative method...")
            # Fallback to standard venv
            subprocess.check_call([sys.executable, '-m', 'venv', venv_path])
            print("[SUCCESS] Virtual environment created using standard venv")
    
    # 优先使用 requirements_all.txt，如果不存在则使用 requirements.txt
    req_file = os.path.join(project_root, 'requirements_all.txt') if os.path.exists(os.path.join(project_root, 'requirements_all.txt')) else os.path.join(project_root, 'requirements.txt')
    if os.path.exists(req_file):
        if venv_exists:
            print(f"[INFO] Virtual environment found. Installing/updating dependencies from {req_file}...")
        else:
            print(f"[INFO] Installing main requirements from {req_file}...")
        
        try:
            # Use uv pip install with the virtual environment
            subprocess.check_call(['uv', 'pip', 'install', '-r', req_file])
            print("[SUCCESS] All dependencies installed using uv")
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] uv pip install failed: {e}")
            print("[INFO] Trying alternative method with pip...")
            # Fallback to standard pip
            try:
                if sys.platform == 'win32':
                    pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
                else:
                    pip_path = os.path.join(venv_path, 'bin', 'pip')
                subprocess.check_call([pip_path, 'install', '-r', req_file])
                print("[SUCCESS] All dependencies installed using pip")
            except Exception as e2:
                print(f"[ERROR] pip install also failed: {e2}")
    else:
        if not venv_exists:
            print("[WARNING] No requirements file found (requirements_all.txt or requirements.txt)")
        else:
            print("[INFO] Virtual environment found, but no requirements file to install")
    
    # 安装 agent_builder_client 的依赖到项目根目录的 .venv
    # 注意：agent_builder_client 只是一个 Python 包，不需要单独的虚拟环境
    # 所有依赖都安装到项目根目录的 .venv 中
    agent_client_dir = os.path.join(project_root, 'agent_builder_client')
    agent_client_req = os.path.join(agent_client_dir, 'requirements.txt')
    
    if os.path.exists(agent_client_req):
        print("[INFO] Installing agent_builder_client dependencies to project .venv...")
        try:
            # 使用项目根目录的 .venv 安装 agent_builder_client 的依赖
            subprocess.check_call(['uv', 'pip', 'install', '-r', agent_client_req])
            print("[SUCCESS] agent_builder_client dependencies installed using uv")
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] uv pip install failed: {e}")
            print("[INFO] Trying alternative method with pip...")
            # Fallback to standard pip
            try:
                if sys.platform == 'win32':
                    pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
                else:
                    pip_path = os.path.join(venv_path, 'bin', 'pip')
                subprocess.check_call([pip_path, 'install', '-r', agent_client_req])
                print("[SUCCESS] agent_builder_client dependencies installed using pip")
            except Exception as e2:
                print(f"[WARNING] pip install also failed: {e2}")
    elif os.path.exists(agent_client_dir):
        print(f"[INFO] agent_builder_client directory found, but requirements.txt not found (optional)")

def check_required_files():
    """检查必需的文件是否存在"""
    # 获取项目根目录（在打包后可能是 PyInstaller 临时目录或 exe 所在目录）
    if getattr(sys, 'frozen', False):
        # 打包后，文件可能在 PyInstaller 的临时目录或 exe 所在目录
        # PyInstaller 会将数据文件解压到 sys._MEIPASS（临时目录）或 exe 所在目录
        if hasattr(sys, '_MEIPASS'):
            # 数据文件在临时解压目录
            project_root = sys._MEIPASS
        else:
            # 数据文件在 exe 所在目录
            project_root = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发环境，使用当前工作目录（应该已经是项目根目录）
        project_root = os.getcwd()
    
    # 定义相对路径（相对于项目根目录）
    required_files = [
        "api.py",  # api.py 在根目录
        "streamlit_chat_ui.py",
        os.path.join("agent_builder_client", "config.py")
    ]
    
    missing_files = []
    found_files = []
    
    for rel_path in required_files:
        # 检查相对于项目根目录的路径
        abs_path = os.path.join(project_root, rel_path)
        if os.path.exists(abs_path):
            found_files.append(abs_path)
            print(f"[OK] Found: {rel_path} -> {abs_path}")
        else:
            # 也尝试当前工作目录（作为后备）
            current_dir_path = os.path.join(os.getcwd(), rel_path)
            if os.path.exists(current_dir_path):
                found_files.append(current_dir_path)
                print(f"[OK] Found (current dir): {rel_path} -> {current_dir_path}")
            else:
                missing_files.append(rel_path)
                print(f"[ERROR] Missing required file: {rel_path}")
                print(f"       Tried: {abs_path}")
                print(f"       Tried: {current_dir_path}")
    
    if missing_files:
        print(f"\n[ERROR] Total {len(missing_files)} required file(s) missing")
        # 显示调试信息
        current_dir = os.getcwd()
        print(f"[DEBUG] Current working directory: {current_dir}")
        print(f"[DEBUG] Project root directory: {project_root}")
        print(f"[DEBUG] __file__: {__file__ if '__file__' in globals() else 'N/A'}")
        if getattr(sys, 'frozen', False):
            print(f"[DEBUG] Running as frozen exe")
            if hasattr(sys, '_MEIPASS'):
                print(f"[DEBUG] PyInstaller temp directory: {sys._MEIPASS}")
        
        # 列出项目根目录的内容
        print(f"[DEBUG] Contents of project root ({project_root}):")
        try:
            items = sorted(os.listdir(project_root))
            for item in items[:20]:  # 只显示前20个
                item_path = os.path.join(project_root, item)
                item_type = "DIR" if os.path.isdir(item_path) else "FILE"
                print(f"  [{item_type}] {item}")
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more items")
        except Exception as e:
            print(f"  [ERROR] Cannot list directory: {e}")
        
        # 检查 agent_builder_client 目录
        agent_dir = os.path.join(project_root, "agent_builder_client")
        if os.path.exists(agent_dir):
            print(f"[DEBUG] Contents of agent_builder_client:")
            try:
                for item in sorted(os.listdir(agent_dir))[:10]:
                    item_path = os.path.join(agent_dir, item)
                    item_type = "DIR" if os.path.isdir(item_path) else "FILE"
                    print(f"  [{item_type}] {item}")
            except Exception as e:
                print(f"  [ERROR] Cannot list directory: {e}")
        
        sys.exit(1)
    
    print(f"[SUCCESS] All {len(found_files)} required files found")

def check_embedding_model():
    """检查 embedding 模型是否存在（相对于项目根目录）"""
    project_root = get_project_root()
    model_path = os.path.join(project_root, "multilingual-e5-large")
    if not os.path.exists(model_path):
        print("[WARNING] multilingual-e5-large model directory not found")
        print(f"[WARNING] Expected path: {model_path}")
        print("[WARNING] Please download the model first:")
        print("[WARNING] git clone https://huggingface.co/intfloat/multilingual-e5-large")
        print("[WARNING] You can continue without it, but the API may not work properly")
    else:
        print(f"[SUCCESS] Embedding model found at: {model_path}")

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

def find_port_process(port):
    """查找占用指定端口的进程（Windows）"""
    try:
        import subprocess
        # 使用 netstat 查找占用端口的进程
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    return pid
        return None
    except:
        return None

# 模块级别的函数，用于 multiprocessing（Windows 需要）
def _run_streamlit_worker(streamlit_path):
    """在后台进程中运行 Streamlit（模块级别函数，用于 multiprocessing）"""
    try:
        import streamlit.web.cli as stcli
        # 修改 sys.argv 以传递正确的参数
        original_argv = sys.argv[:]
        sys.argv = [
            'streamlit', 'run', streamlit_path,
            '--server.headless', 'true',
            '--global.developmentMode', 'false'
        ]
        try:
            stcli.main()
        finally:
            sys.argv = original_argv
    except Exception as e:
        print(f"[ERROR] Failed to start Streamlit service: {e}")

def run_streamlit_process_worker(streamlit_path, temp_script_path, log_file_path, env):
    """在獨立進程中執行 Streamlit 啟動腳本"""
    try:
        # 設置環境變量
        if env:
            for key, value in env.items():
                if value is not None:
                    os.environ[key] = str(value)
        
        # 確保能找到打包的模組
        if hasattr(sys, '_MEIPASS'):
            if sys._MEIPASS not in sys.path:
                sys.path.insert(0, sys._MEIPASS)
        
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        with open(log_file_path, 'a', encoding='utf-8', errors='ignore') as log_file:
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            try:
                sys.stdout = log_file
                sys.stderr = log_file
                
                print(f"[STREAMLIT_CHILD] Starting Streamlit...")
                print(f"[STREAMLIT_CHILD] streamlit_path: {streamlit_path}")
                print(f"[STREAMLIT_CHILD] temp_script_path: {temp_script_path}")
                
                with open(temp_script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                
                exec(compile(script_content, temp_script_path, 'exec'), {
                    '__file__': temp_script_path,
                    '__name__': '__main__',
                    '__package__': None,
                })
            finally:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
    except Exception as e:
        try:
            with open(log_file_path, 'a', encoding='utf-8', errors='ignore') as log_file:
                log_file.write(f"[STREAMLIT_CHILD] ERROR: {e}\n")
                traceback.print_exc(file=log_file)
        except Exception:
            pass

# 全局变量：跟踪已启动的服务进程
_started_processes = {}
_started_threads = {}

def _process_is_alive(process):
    if process is None:
        return False
    if hasattr(process, 'is_alive'):
        return process.is_alive()
    if hasattr(process, 'poll'):
        return process.poll() is None
    return False

def _process_exit_code(process):
    if process is None:
        return None
    if hasattr(process, 'exitcode'):
        return process.exitcode
    if hasattr(process, 'returncode'):
        return process.returncode
    return None

def check_process_status(process_name, process):
    """检查进程状态并返回详细信息"""
    if process is None:
        return f"{process_name}: Process is None"
    
    if _process_is_alive(process):
        return f"{process_name}: Running (PID: {getattr(process, 'pid', 'N/A')})"
    else:
        return_code = _process_exit_code(process)
        return f"{process_name}: Exited with code {return_code} (PID: {getattr(process, 'pid', 'N/A')})"

def cleanup_processes():
    """清理已启动的进程（在程序退出时调用）"""
    global _started_processes
    for name, proc in _started_processes.items():
        if proc:
            # 检查是否是 multiprocessing.Process（使用 is_alive()）还是 subprocess.Popen（使用 poll()）
            if hasattr(proc, 'is_alive'):
                if proc.is_alive():  # multiprocessing.Process
                    try:
                        proc.terminate()
                        proc.join(timeout=2)
                    except:
                        try:
                            proc.kill()
                            proc.join(timeout=1)
                        except:
                            pass
            elif hasattr(proc, 'poll'):
                if proc.poll() is None:  # subprocess.Popen
                    try:
                        proc.terminate()
                        proc.wait(timeout=2)
                    except:
                        try:
                            proc.kill()
                        except:
                            pass

# 注册退出时的清理函数
atexit.register(cleanup_processes)

def start_services():
    # 延迟导入配置，确保在虚拟环境中运行
    # 如果导入失败，提示用户使用 uv run 运行脚本
    try:
        from agent_builder_client.config import settings
    except ImportError as e:
        print(f"[ERROR] 无法导入配置模块: {e}")
        print("[INFO] 请使用 'uv run build_exe.py' 来运行此脚本，以确保使用虚拟环境")
        print("[INFO] 或者确保虚拟环境已激活，并且所有依赖都已安装")
        sys.exit(1)
    
    # 检查是否在打包后的 exe 中运行
    is_frozen = getattr(sys, 'frozen', False)
    
    # 检查服务是否已经在运行（通过端口检查）
    global _started_processes, _started_threads
    
    print("[INFO] Starting FastAPI service in background...")
    # 根据是否打包选择不同的启动方式
    if is_frozen:
        # 打包后，使用 threading 来启动服务，避免使用 sys.executable（它指向 exe 本身）
        import threading
        
        def run_api():
            """在后台线程中运行 API"""
            try:
                # 导入 api 模块并调用 run_server 函数，避免重复执行
                # api.run_server() 内部已经有锁保护，防止重复启动
                import api
                # 使用 api.run_server() 函数来启动，这样可以精确控制启动过程
                # 避免 uvicorn.run() 可能导致的重复导入问题
                api.run_server()
            except Exception as e:
                print(f"[ERROR] Failed to start FastAPI service: {e}")
                import traceback
                traceback.print_exc()
        
        # 检查是否已经有API线程在运行
        if 'api' not in _started_threads or not _started_threads['api'].is_alive():
            api_thread = threading.Thread(target=run_api, daemon=True, name='API-Thread')
            api_thread.start()
            _started_threads['api'] = api_thread
            print("[SUCCESS] FastAPI service started in background thread")
        else:
            print("[WARNING] FastAPI service thread already running, skipping startup")
    else:
        # 开发环境，使用 uv run
        # 检查是否已经有API进程在运行
        if 'api' not in _started_processes or not _process_is_alive(_started_processes['api']):
            if settings.LOGGING_ENABLED:
                _started_processes['api'] = subprocess.Popen(['uv', 'run', '--python', '3.12.11', 'api.py'], stdout=open(settings.LOGGING_FILE_PATH, 'a', encoding='utf-8'), stderr=subprocess.STDOUT)
                print(f"[SUCCESS] FastAPI service started in background (logs: {settings.LOGGING_FILE_PATH})")
            else:
                devnull = open(os.devnull, 'w')
                _started_processes['api'] = subprocess.Popen(['uv', 'run', '--python', '3.12.11', 'api.py'], stdout=devnull, stderr=devnull)
                print("[SUCCESS] FastAPI service started in background (logging disabled)")
        else:
            print("[WARNING] FastAPI service process already running, skipping startup")

    time.sleep(10)  # Wait for the API to start

    print("[INFO] Starting Streamlit UI in background...")
    # 根据是否打包选择不同的启动方式
    if is_frozen:
        # 打包后，使用 subprocess 启动 Streamlit（NOT threading）
        # Streamlit 需要在主线程中运行以设置信号处理器，所以必须使用 subprocess
        # 在打包后的 exe 中，文件在临时解压目录（sys._MEIPASS）中
        # 使用与 check_required_files() 相同的逻辑来查找文件
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 临时解压目录
            streamlit_path = os.path.join(sys._MEIPASS, 'streamlit_chat_ui.py')
        else:
            # 数据文件在 exe 所在目录
            streamlit_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'streamlit_chat_ui.py')
        
        # 验证文件是否存在，如果不存在则尝试其他路径
        if not os.path.exists(streamlit_path):
            print(f"[WARNING] Streamlit file not found at primary location: {streamlit_path}")
            # 尝试其他可能的路径（与 check_required_files 逻辑一致）
            possible_paths = [
                os.path.join(os.getcwd(), 'streamlit_chat_ui.py'),  # 当前工作目录
                os.path.join(get_project_root(), 'streamlit_chat_ui.py'),  # exe 所在目录
            ]
            if hasattr(sys, '_MEIPASS'):
                possible_paths.insert(0, os.path.join(sys._MEIPASS, 'streamlit_chat_ui.py'))
            
            found = False
            for path in possible_paths:
                if os.path.exists(path):
                    streamlit_path = path
                    print(f"[INFO] Found Streamlit file at: {streamlit_path}")
                    found = True
                    break
            
            if not found:
                print(f"[ERROR] Could not find streamlit_chat_ui.py in any expected location")
                print(f"[DEBUG] sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
                print(f"[DEBUG] Current working directory: {os.getcwd()}")
                print(f"[DEBUG] Project root: {get_project_root()}")
                print(f"[DEBUG] sys.executable: {sys.executable}")
                return None
        else:
            print(f"[DEBUG] Using Streamlit file at: {streamlit_path}")
        
        # 使用 subprocess 启动 Streamlit，避免 threading 的信号处理器问题
        # Streamlit 需要在主线程中运行以设置信号处理器，所以使用 subprocess 在独立进程中运行
        try:
            # 在打包后的 exe 中，使用 sys.executable 来启动 Streamlit
            # 创建一个启动脚本来运行 Streamlit
            import tempfile
            import shutil
            
            # 创建临时启动脚本
            # 使用 repr() 确保路径字符串正确转义
            streamlit_path_escaped = repr(streamlit_path)
            # 使用纯英文注释避免 Windows cp950 编码问题
            # 设置环境变量标记这是子进程，防止重复启动
            child_marker = f"STREAMLIT_CHILD_{os.getpid()}"
            startup_script = f"""# -*- coding: utf-8 -*-
# Streamlit startup script
# This script is executed by the exe to start Streamlit in a child process

import sys
import os

# Print debug information
print("[STREAMLIT_STARTUP] Starting Streamlit startup script...")
print(f"[STREAMLIT_STARTUP] Python executable: {{sys.executable}}")
print(f"[STREAMLIT_STARTUP] Python version: {{sys.version}}")
print(f"[STREAMLIT_STARTUP] sys.argv: {{sys.argv}}")
print(f"[STREAMLIT_STARTUP] Current directory: {{os.getcwd()}}")
print(f"[STREAMLIT_STARTUP] sys._MEIPASS: {{getattr(sys, '_MEIPASS', 'N/A')}}")

# Set environment variable to mark this as child process
os.environ['STREAMLIT_CHILD_PROCESS'] = '1'
os.environ['STREAMLIT_CHILD_MARKER'] = '{child_marker}'

# Ensure we can find packaged modules
if hasattr(sys, '_MEIPASS'):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)
    print(f"[STREAMLIT_STARTUP] Added sys._MEIPASS to path: {{sys._MEIPASS}}")
print(f"[STREAMLIT_STARTUP] sys.path (first 3): {{sys.path[:3]}}")

# Patch importlib.metadata before importing streamlit
print("[STREAMLIT_STARTUP] Patching importlib.metadata...")
import importlib.metadata
original_version = importlib.metadata.version

def patched_version(package_name):
    try:
        return original_version(package_name)
    except importlib.metadata.PackageNotFoundError:
        if package_name == 'streamlit':
            return "1.39.0"
        raise

importlib.metadata.version = patched_version

# Import and run streamlit
print("[STREAMLIT_STARTUP] Importing streamlit...")
try:
    import streamlit.web.cli as stcli
    print("[STREAMLIT_STARTUP] Streamlit imported successfully")
except Exception as e:
    print(f"[STREAMLIT_STARTUP] ERROR: Failed to import streamlit: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

streamlit_path = {streamlit_path_escaped}
print(f"[STREAMLIT_STARTUP] Streamlit file path: {{streamlit_path}}")

# Verify file exists
if not os.path.exists(streamlit_path):
    print(f"[STREAMLIT_STARTUP] ERROR: Streamlit file not found: {{streamlit_path}}")
    print(f"[STREAMLIT_STARTUP] sys._MEIPASS: {{getattr(sys, '_MEIPASS', 'N/A')}}")
    print(f"[STREAMLIT_STARTUP] Current directory: {{os.getcwd()}}")
    print(f"[STREAMLIT_STARTUP] Listing sys._MEIPASS contents:")
    if hasattr(sys, '_MEIPASS'):
        try:
            for item in os.listdir(sys._MEIPASS)[:20]:
                print(f"  {{item}}")
        except Exception as e:
            print(f"  Error listing directory: {{e}}")
    sys.exit(1)

print(f"[STREAMLIT_STARTUP] Streamlit file found, starting Streamlit...")

# Set sys.argv for streamlit
sys.argv = [
    'streamlit', 'run', streamlit_path,
    '--server.headless', 'true',
    '--global.developmentMode', 'false'
]
print(f"[STREAMLIT_STARTUP] sys.argv set to: {{sys.argv}}")

# Run streamlit (this will block)
try:
    print("[STREAMLIT_STARTUP] Calling stcli.main()...")
    stcli.main()
except SystemExit as e:
    print(f"[STREAMLIT_STARTUP] Streamlit exited with code: {{e.code if hasattr(e, 'code') else 0}}")
    sys.exit(e.code if hasattr(e, 'code') else 0)
except Exception as e:
    print(f"[STREAMLIT_STARTUP] ERROR: Failed to start Streamlit: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
            
            # 将启动脚本写入临时文件（使用 UTF-8 编码避免 Windows cp950 编码问题）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(startup_script)
                temp_script = f.name
            
            try:
                # 检查是否已经有Streamlit进程在运行
                if 'streamlit' in _started_processes and _process_is_alive(_started_processes['streamlit']):
                    print("[WARNING] Streamlit process already running, skipping startup")
                    # 清理临时脚本
                    try:
                        os.unlink(temp_script)
                    except:
                        pass
                else:
                    # 使用 subprocess 启动 Streamlit（在独立进程中运行）
                    # 使用 sys.executable 来运行临时脚本
                    # 设置环境变量，标记这是子进程
                    env = os.environ.copy()
                    env['STREAMLIT_CHILD_PROCESS'] = '1'
                    env['STREAMLIT_CHILD_MARKER'] = child_marker
                    # 设置 PYTHONPATH 确保能找到打包的模块
                    if hasattr(sys, '_MEIPASS'):
                        if 'PYTHONPATH' in env:
                            env['PYTHONPATH'] = sys._MEIPASS + os.pathsep + env['PYTHONPATH']
                        else:
                            env['PYTHONPATH'] = sys._MEIPASS
                    
                    # 強制啟用日志，即使配置中關閉了（用于調試）
                    # 創建日志文件路径
                    log_file_path = settings.LOGGING_STREAMLIT_FILE_PATH if settings.LOGGING_ENABLED else os.path.join(get_project_root(), 'streamlit_debug.log')
                    log_dir = os.path.dirname(log_file_path)
                    if log_dir and not os.path.exists(log_dir):
                        os.makedirs(log_dir, exist_ok=True)
                    # 確保日志文件存在
                    open(log_file_path, 'a', encoding='utf-8').close()
                    print(f"[DEBUG] Streamlit log file: {log_file_path}")
                    
                    # 打印启动信息
                    print(f"[DEBUG] Starting Streamlit using multiprocessing...")
                    print(f"[DEBUG] Environment variables:")
                    print(f"  STREAMLIT_CHILD_PROCESS: {env.get('STREAMLIT_CHILD_PROCESS')}")
                    print(f"  PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
                    print(f"  Working directory: {os.path.dirname(streamlit_path) if os.path.dirname(streamlit_path) else os.getcwd()}")
                    
                    import multiprocessing
                    streamlit_process = multiprocessing.Process(
                        target=run_streamlit_process_worker,
                        args=(streamlit_path, temp_script, log_file_path, env),
                        name='StreamlitProcess'
                    )
                    streamlit_process.start()
                    print(f"[DEBUG] Streamlit process started, PID: {streamlit_process.pid}")
                    print(f"[DEBUG] Streamlit script: {temp_script}")
                    print(f"[DEBUG] Streamlit file: {streamlit_path}")
                    print(f"[DEBUG] Log file: {log_file_path}")
                    
                    _started_processes['streamlit'] = streamlit_process
                    print("[SUCCESS] Streamlit UI started in background process")
                    
                    # 等待一下，检查进程是否真的启动了
                    time.sleep(2)
                    
                    # 检查进程状态（multiprocessing.Process 使用 is_alive()）
                    if not _process_is_alive(streamlit_process):
                        # 进程已经退出
                        return_code = _process_exit_code(streamlit_process)
                        print(f"[ERROR] Streamlit process exited immediately with code: {return_code}")
                        if os.path.exists(log_file_path):
                            print(f"[INFO] Check log file for details: {log_file_path}")
                            try:
                                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    log_content = f.read()
                                    if log_content:
                                        print("[INFO] Last 50 lines of log:")
                                        lines = log_content.split('\n')
                                        for line in lines[-50:]:
                                            if line.strip():
                                                print(f"  {line}")
                            except Exception as e:
                                print(f"[WARNING] Could not read log file: {e}")
                        else:
                            print("[WARNING] Logging is disabled, cannot check error details")
                            print("[INFO] Try enabling logging in config.yaml to see error details")
                        return None
                    else:
                        print(f"[DEBUG] Streamlit process is running, PID: {streamlit_process.pid}")
            except Exception as e:
                print(f"[ERROR] Failed to start Streamlit process: {e}")
                import traceback
                traceback.print_exc()
                # 清理临时文件
                try:
                    os.unlink(temp_script)
                except:
                    pass
        except Exception as e:
            print(f"[ERROR] Failed to setup Streamlit: {e}")
            import traceback
            traceback.print_exc()
    else:
        # 开发环境，使用 uv run
        # 检查是否已经有Streamlit进程在运行
        if 'streamlit' not in _started_processes or not _process_is_alive(_started_processes['streamlit']):
            if settings.LOGGING_ENABLED:
                _started_processes['streamlit'] = subprocess.Popen(['uv', 'run', '--python', '3.12.11', 'streamlit', 'run', 'streamlit_chat_ui.py', '--server.headless', 'true'], stdout=open(settings.LOGGING_STREAMLIT_FILE_PATH, 'a', encoding='utf-8'), stderr=subprocess.STDOUT)
                print(f"[SUCCESS] Streamlit UI started in background (logs: {settings.LOGGING_STREAMLIT_FILE_PATH})")
            else:
                devnull = open(os.devnull, 'w')
                _started_processes['streamlit'] = subprocess.Popen(['uv', 'run', '--python', '3.12.11', 'streamlit', 'run', 'streamlit_chat_ui.py', '--server.headless', 'true'], stdout=devnull, stderr=devnull)
                print("[SUCCESS] Streamlit UI started in background (logging disabled)")
        else:
            print("[WARNING] Streamlit process already running, skipping startup")

    # 等待 Streamlit 启动
    print("[INFO] Waiting for Streamlit to start...")
    time.sleep(5)  # 给 Streamlit 一些时间启动
    
    # 检查 Streamlit 进程是否还在运行
    if is_frozen and 'streamlit' in _started_processes:
        streamlit_process = _started_processes['streamlit']
        if not streamlit_process.is_alive():
            # 进程已退出
            return_code = streamlit_process.exitcode
            print(f"[ERROR] Streamlit process exited with code: {return_code}")
            if settings.LOGGING_ENABLED and os.path.exists(settings.LOGGING_STREAMLIT_FILE_PATH):
                print(f"[INFO] Check log file for details: {settings.LOGGING_STREAMLIT_FILE_PATH}")
                try:
                    with open(settings.LOGGING_STREAMLIT_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()
                        if log_content:
                            print("[INFO] Last 50 lines of log:")
                            lines = log_content.split('\n')
                            for line in lines[-50:]:
                                if line.strip():
                                    print(f"  {line}")
                except Exception as e:
                    print(f"[WARNING] Could not read log file: {e}")
            return None
        else:
            print(f"[DEBUG] Streamlit process is still running, PID: {streamlit_process.pid}")
    
    print("[INFO] Detecting Streamlit port...")
    # 使用配置中的 log 文件路径
    log_file = settings.LOGGING_STREAMLIT_FILE_PATH if settings.LOGGING_ENABLED else 'streamlit.log'
    
    # 尝试多次检测端口
    max_attempts = 10
    streamlit_port = None
    for attempt in range(max_attempts):
        streamlit_port = get_streamlit_port(log_file=log_file)
        if streamlit_port and is_port_in_use(streamlit_port):
            print(f"[SUCCESS] Streamlit is running on port {streamlit_port}")
            break
        else:
            print(f"[INFO] Attempt {attempt + 1}/{max_attempts}: Port {streamlit_port if streamlit_port else 'unknown'} not ready yet...")
            time.sleep(2)
    
    if not streamlit_port or not is_port_in_use(streamlit_port):
        print("[ERROR] Could not detect Streamlit port or port is not in use")
        print("[INFO] Checking process status...")
        if is_frozen and 'streamlit' in _started_processes:
            streamlit_process = _started_processes['streamlit']
            if not streamlit_process.is_alive():
                print(f"[ERROR] Streamlit process has exited with code: {streamlit_process.exitcode}")
            else:
                print(f"[INFO] Streamlit process is still running (PID: {streamlit_process.pid})")
                print("[INFO] But port is not listening. This might indicate:")
                print("  1. Streamlit is still starting up (wait longer)")
                print("  2. Streamlit failed to bind to port")
                print("  3. Check firewall settings")
        
        return None
    
    streamlit_url = f'http://localhost:{streamlit_port}'
    print(f"[SUCCESS] Streamlit is running on port {streamlit_port}")
    print(f"[INFO] Opening browser at {streamlit_url}...")
    webbrowser.open(streamlit_url)
    
    return streamlit_port

def get_project_root():
    """Get the project root directory, handling both script and exe execution
    
    注意：在打包后的 exe 中，此函数返回 exe 所在目录（而不是临时解压目录）
    这样 embedding、log、venv 等路径都会相对于 exe 所在目录
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        # 使用 exe 所在目录作为项目根目录（而不是临时解压目录）
        # 这样 embedding、log、venv 等路径都会相对于 exe 所在目录
        exe_path = os.path.dirname(os.path.abspath(sys.executable))
        project_root = exe_path
    else:
        # Running as script
        # 获取 build_exe.py 所在的目录（项目根目录）
        script_file = os.path.abspath(__file__)
        project_root = os.path.dirname(script_file)
    
    # 规范化路径（处理大小写、路径分隔符等）
    project_root = os.path.normpath(os.path.abspath(project_root))
    
    # 验证项目根目录是否存在（包含必要的文件/目录）
    if not os.path.exists(project_root):
        # 如果获取的路径不存在，尝试使用当前工作目录
        current_dir = os.getcwd()
        current_dir = os.path.normpath(os.path.abspath(current_dir))
        print(f"[WARNING] Project root {project_root} does not exist, using current directory: {current_dir}")
        project_root = current_dir
    
    return project_root

def main():
    # 检查是否是子进程（通过环境变量）
    if os.environ.get('STREAMLIT_CHILD_PROCESS') == '1':
        # 这是 Streamlit 子进程，不应该执行主程序逻辑
        # 应该由 Streamlit 启动脚本处理
        return
    
    # Change to project root directory
    project_root = get_project_root()
    
    # 规范化路径（处理大小写和路径分隔符）
    project_root = os.path.normpath(os.path.abspath(project_root))
    
    print(f"[DEBUG] Switching to project root: {project_root}")
    
    # 切换到项目根目录
    try:
        os.chdir(project_root)
        print(f"[SUCCESS] Changed to directory: {os.getcwd()}")
    except Exception as e:
        print(f"[ERROR] Failed to change directory to {project_root}: {e}")
        print(f"[INFO] Current directory: {os.getcwd()}")
        # 尝试使用当前目录
        project_root = os.getcwd()
    
    print("==========================================")
    print("Gmail Chat Application Setup & Start")
    print("==========================================")

    # 打包后的 exe 不需要检查 Python、uv 和虚拟环境，因为所有依赖都已打包
    is_frozen = getattr(sys, 'frozen', False)
    if not is_frozen:
        # 仅在开发环境中检查这些
        check_python()
        check_uv()
        check_virtual_env()
    
    check_required_files()  # 现在使用当前工作目录检查文件
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
    
    # 显示进程状态
    print("\n[INFO] Process Status:")
    if 'api' in _started_threads:
        api_thread = _started_threads['api']
        status = "Running" if api_thread.is_alive() else "Stopped"
        print(f"    API Thread: {status}")
    if 'streamlit' in _started_processes:
        print(f"    {check_process_status('Streamlit', _started_processes['streamlit'])}")
    
    print("\nServices:")
    print("    FastAPI: http://localhost:8081")
    if streamlit_port:
        print(f"    Streamlit UI: http://localhost:{streamlit_port}")
    else:
        print("    Streamlit UI: Not available (check logs for details)")
    
    # 如果 Streamlit 没有启动，提供调试信息
    if not streamlit_port:
        print("\n[DEBUG] Troubleshooting:")
        print("    1. Check the log file for error messages")
        try:
            from agent_builder_client.config import settings
            log_file = settings.LOGGING_STREAMLIT_FILE_PATH if settings.LOGGING_ENABLED else os.path.join(get_project_root(), 'streamlit_debug.log')
        except:
            log_file = os.path.join(get_project_root(), 'streamlit_debug.log')
        print(f"    2. Log file location: {log_file}")
        print("    3. Check if port 8501 is available")
        print("    4. Try manually starting Streamlit to see error messages")
    
    print("\nPress Enter to exit...")
    try:
        input()  # 等待用户按 Enter
    except KeyboardInterrupt:
        print("\n\nExiting...")
    

def safe_print(*args, **kwargs):
    """安全的 print 函数，处理编码问题"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 如果编码失败，尝试使用 ASCII 编码
        try:
            message = ' '.join(str(arg).encode('ascii', 'replace').decode('ascii') for arg in args)
            print(message, **kwargs)
        except:
            # 最后的备选方案：使用 repr
            print(repr(args), **kwargs)

if __name__ == '__main__':
    # 检查是否是临时脚本在执行
    # 当使用 sys.executable temp_script 执行临时脚本时：
    # - sys.argv[0] 是 exe 路径
    # - sys.argv[1] 是临时脚本路径
    # - 环境变量 STREAMLIT_CHILD_PROCESS 会被设置
    # Python 会自动执行临时脚本的内容，但主程序逻辑也会执行
    # 我们需要检查：如果第二个参数是临时脚本，说明这是子进程，不应该执行主程序逻辑
    import sys
    is_temp_script = False
    if len(sys.argv) > 1:
        script_path = sys.argv[1]
        # 检查是否是临时脚本（包含 temp 或 tmp，且是 .py 文件）
        script_basename = os.path.basename(script_path).lower()
        if script_path.endswith('.py') and ('temp' in script_basename or 'tmp' in script_basename):
            is_temp_script = True
    
    # 如果是临时脚本在执行，立即退出，不执行主程序逻辑
    # Python 会自动执行临时脚本的内容，所以这里退出不会影响临时脚本的执行
    if is_temp_script:
        # 这是临时脚本在执行，不应该执行主程序逻辑
        # Python 会自动执行临时脚本的内容，所以这里退出不会影响临时脚本的执行
        sys.exit(0)
    
    # 也检查环境变量（双重保险）
    if os.environ.get('STREAMLIT_CHILD_PROCESS') == '1' and len(sys.argv) > 1:
        # 环境变量设置了，且第二个参数是脚本文件，说明这是子进程
        script_path = sys.argv[1]
        if script_path.endswith('.py'):
            sys.exit(0)
    
    # 防止 multiprocessing 子进程执行主程序
    # 在 Windows 上，multiprocessing 使用 spawn 方式，子进程会重新导入模块
    # 使用 freeze_support() 来正确处理 Windows 上的 multiprocessing
    import multiprocessing
    
    # Windows 上必须调用 freeze_support() 来正确处理 multiprocessing
    if sys.platform == 'win32':
        try:
            multiprocessing.freeze_support()
        except:
            pass
    
    # 再次检查是否是 multiprocessing 子进程（双重保险）
    try:
        current_process = multiprocessing.current_process()
        if current_process.name != 'MainProcess':
            # 这是子进程，不执行主程序
            sys.exit(0)
    except:
        pass
    
    # 设置 multiprocessing 启动方法（仅在 Windows 上需要）
    if sys.platform == 'win32':
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            # 如果已经设置过，忽略错误
            pass
    
    # 再次确保编码设置（在打包后可能需要在运行时设置）
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            os.environ['PYTHONIOENCODING'] = 'utf-8'
        except:
            pass
    
    # 打包后的 exe 不需要虚拟环境检查和警告
    is_frozen = getattr(sys, 'frozen', False)
    if not is_frozen:
        # 确保虚拟环境在 Python 路径中（仅开发环境）
        if ensure_venv_in_path():
            safe_print("[INFO] 已将虚拟环境添加到 Python 路径")
        
        # 检查是否在虚拟环境中运行（仅开发环境）
        in_venv = (
            hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )
        
        if not in_venv and os.path.exists('.venv'):
            safe_print("[WARNING] 检测到不在虚拟环境中运行")
            safe_print("[INFO] 建议使用 'uv run build_exe.py' 来运行此脚本，以确保使用虚拟环境")
            safe_print("[INFO] 已尝试将虚拟环境添加到路径，继续运行...")
            safe_print()
    
    main()
    
    
# uv run pyinstaller --onefile --noconsole --name=app build_exe.py