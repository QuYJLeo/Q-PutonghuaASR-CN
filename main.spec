# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import site

from PyInstaller.utils.hooks import collect_submodules,collect_data_files
from build_pyd import BuildPyd

system = platform.system()
isWindows = system == "Windows"
isLinux = system == "Linux"

build_pyd_mult = BuildPyd('', ["."], [])
packages_mult =build_pyd_mult.exec_build_pyd()
build_pyd_mult.clean_c_html()

venv_path = [s for s in site.getsitepackages() if s.endswith("site-packages")][0]

hiddenimports = []
hiddenimports += packages_mult
hiddenimports += collect_submodules('eventlet')
hiddenimports += collect_submodules('dns')
hiddenimports += collect_submodules('socketio')
hiddenimports += collect_submodules('engineio')
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('VAD')
hiddenimports += collect_submodules('kaldi_native_fbank')
hiddenimports += collect_submodules('logging')
hiddenimports += collect_submodules('pyDes')
hiddenimports += collect_submodules('funasr')
hiddenimports += collect_submodules('flask')
hiddenimports += collect_submodules('gevent')
hiddenimports += collect_submodules('mutagen')
hiddenimports += collect_submodules('soundfile')
hiddenimports += collect_submodules('noisereduce')
hiddenimports += collect_submodules('funasr_onnx')
hiddenimports += collect_submodules('logger')
if isWindows:
    hiddenimports += collect_submodules('wmi')

datas=[]

datas+=[('config.yaml','.')]

datas+=[(os.path.join(venv_path,'funasr/version.txt'),'funasr')]
datas+=[(os.path.join(venv_path,'funasr/frontends/wav_frontend.py'),'funasr/frontends')]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[]+datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='asr-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    [('config1.yaml','config.yaml','data')],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='hs-asr-funasr-large-server',
)
build_pyd_mult.clean_pyd()
