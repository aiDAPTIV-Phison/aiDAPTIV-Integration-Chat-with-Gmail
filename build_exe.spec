# -*- mode: python ; coding: utf-8 -*-

import os
import streamlit

block_cipher = None

streamlit_root = os.path.dirname(streamlit.__file__)
streamlit_runtime_dir = os.path.join(streamlit_root, "runtime")
streamlit_static_dir = os.path.join(streamlit_root, "static")

a = Analysis(
    ['build_exe.py'],
    pathex=[],  # PyInstaller 会自动将脚本所在目录添加到路径
    binaries=[],
    datas=[
        ('agent_builder_client', 'agent_builder_client'),
        ('config.yaml', '.'),  # 将 config.yaml 打包到根目录
        ('api.py', '.'),  # 将 api.py 打包到根目录
        ('streamlit_chat_ui.py', '.'),  # 将 streamlit_chat_ui.py 打包到根目录
        (streamlit_runtime_dir, os.path.join('streamlit', 'runtime')),
        (streamlit_static_dir, os.path.join('streamlit', 'static')),
    ],
    hiddenimports=[
        # api.py 现在在根目录，直接导入
        'api',
        # agent_builder_client 模块
        'agent_builder_client',
        'agent_builder_client.config',
        'agent_builder_client.services',
        'agent_builder_client.services.client_query',
        'agent_builder_client.services.create_db',
        # 第三方库
        'streamlit',
        'fastapi',
        'uvicorn',
        'chromadb',
        'langchain',
        'langchain_community',
        'langchain_chroma',
        'sentence_transformers',
        'torch',
        'transformers',
        'transformers.models',
        'transformers.models.metaclip_2',
        'transformers.models.metaclip_2.modeling_metaclip_2',
        'transformers.models.metaclip_2.configuration_metaclip_2',
        'google',
        'google.auth',
        'google.oauth2',
        'googleapiclient',
        'embedchain',
        'loguru',
        'pydantic',
        'requests',
        'openai',
        'yaml',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.uvloop_impl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用UPX压缩以加快打包速度
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

