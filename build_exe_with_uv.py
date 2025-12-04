#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 uv 和 PyInstaller 打包应用成 exe
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_uv():
    """检查 uv 是否安装"""
    try:
        subprocess.check_call(['uv', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("[SUCCESS] uv 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] uv 未安装")
        print("[INFO] 正在安装 uv...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'uv'], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("[SUCCESS] uv 安装成功")
            return True
        except subprocess.CalledProcessError:
            print("[ERROR] uv 安装失败，请手动安装: pip install uv")
            return False

def setup_uv_environment():
    """使用 uv 创建虚拟环境并安装依赖"""
    print("\n" + "="*50)
    print("步骤 1/3: 使用 uv 创建环境")
    print("="*50)
    
    # 创建虚拟环境
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("[INFO] 创建虚拟环境（使用 Python 3.12.11）...")
        try:
            subprocess.check_call(['uv', 'venv', '--python', '3.12.11', '.venv'], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("[SUCCESS] 虚拟环境创建成功（Python 3.12.11）")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] 虚拟环境创建失败: {e}")
            return False
    else:
        print("[INFO] 虚拟环境已存在，跳过创建")
    
    # 安装依赖
    print("[INFO] 安装项目依赖...")
    try:
        # 优先使用 requirements.txt，避免 pyproject.toml 的包结构问题
        if os.path.exists('requirements.txt'):
            print("[INFO] 安装主项目依赖...")
            subprocess.check_call(['uv', 'pip', 'install', '-r', 'requirements.txt'])
            
            # 安装 agent_builder_client 的依赖
            agent_req = Path('agent_builder_client') / 'requirements.txt'
            if agent_req.exists():
                print("[INFO] 安装 agent_builder_client 依赖...")
                subprocess.check_call(['uv', 'pip', 'install', '-r', str(agent_req)])
            
            # 安装 PyInstaller（如果还没有）
            print("[INFO] 安装 PyInstaller...")
            subprocess.check_call(['uv', 'pip', 'install', 'pyinstaller>=6.0.0'])
            
        else:
            print("[ERROR] 未找到 requirements.txt")
            return False
        print("[SUCCESS] 依赖安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 依赖安装失败: {e}")
        return False

def get_venv_python():
    """获取虚拟环境中的 Python 路径"""
    if sys.platform == 'win32':
        return Path('.venv') / 'Scripts' / 'python.exe'
    else:
        return Path('.venv') / 'bin' / 'python'

def build_exe():
    """使用 PyInstaller 打包成 exe"""
    print("\n" + "="*50)
    print("步骤 2/3: 使用 PyInstaller 打包")
    print("="*50)
    
    venv_python = get_venv_python()
    if not venv_python.exists():
        print(f"[ERROR] 虚拟环境 Python 不存在: {venv_python}")
        return False
    
    # 验证 Python 版本
    try:
        version_output = subprocess.check_output([str(venv_python), '--version'], 
                                                stderr=subprocess.STDOUT, text=True)
        print(f"[INFO] 使用 Python 版本: {version_output.strip()}")
    except Exception as e:
        print(f"[WARNING] 无法获取 Python 版本: {e}")
    
    # PyInstaller 应该在依赖安装阶段已经安装了
    print("[INFO] PyInstaller 应该已经安装")
    
    # PyInstaller 命令
    build_dir = Path('build')
    dist_dir = Path('dist')
    spec_file = Path('build_exe.spec')
    
    # 清理之前的构建
    if build_dir.exists():
        print("[INFO] 清理旧的 build 目录...")
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        print("[INFO] 清理旧的 dist 目录...")
        shutil.rmtree(dist_dir)
    
    # 检查 spec 文件是否存在
    if not spec_file.exists():
        print(f"[ERROR] spec 文件不存在: {spec_file}")
        print("[INFO] 请确保 build_exe.spec 文件存在于项目根目录")
        return False
    
    # 执行打包
    print("[INFO] 开始打包...")
    print("[INFO] 这可能需要几分钟时间，请耐心等待...")
    
    try:
        cmd = [
            str(venv_python), '-m', 'PyInstaller',
            'build_exe.spec',
            '--clean',
            '--noconfirm'
        ]
        subprocess.check_call(cmd)
        print("[SUCCESS] 打包完成！")
        print(f"[INFO] exe 文件位置: {dist_dir / 'app.exe'}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 打包失败: {e}")
        return False

def main():
    """主函数"""
    print("="*50)
    print("使用 uv 打包应用成 exe")
    print("="*50)
    
    # 检查 uv
    if not check_uv():
        sys.exit(1)
    
    # 设置环境
    if not setup_uv_environment():
        sys.exit(1)
    
    # 打包
    if not build_exe():
        sys.exit(1)
    
    print("\n" + "="*50)
    print("步骤 3/3: 完成！")
    print("="*50)
    print("\n[SUCCESS] 所有步骤完成！")
    print("[INFO] exe 文件位于: dist/app.exe")
    print("\n注意事项:")
    print("1. 确保目标机器有必要的运行时库")
    print("2. 首次运行可能需要一些时间来初始化")
    print("3. 如果遇到问题，请检查 dist 目录中的日志文件")

if __name__ == '__main__':
    main()

