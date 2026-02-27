# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files
ROOTDIR = os.path.abspath(os.path.join(SPECPATH, '..'))

block_cipher = None

flet_desktop_data = collect_data_files('flet_desktop')

a = Analysis(
    [os.path.join(ROOTDIR, 'main.py')],
    pathex=[],
    datas=[(os.path.join(ROOTDIR, 'root.json'), '.')] + flet_desktop_data,
    hiddenimports=['flet_desktop'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'boto3', 'botocore', 's3transfer', 'jmespath',
        'pytest', 'pytest_cov', '_pytest', 'coverage', 'mypy', 'ruff',
        'tkinter', '_tkinter', 'unittest', 'doctest', 'pdb',
        'xmlrpc', 'ftplib', 'imaplib', 'smtplib', 'nntplib',
        'telnetlib', 'cgi', 'cgitb',
        'IPython', 'notebook', 'jupyter',
    ],
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
    name='video-dl.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'ucrtbase.dll', 'python312.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOTDIR, 'icon.ico'),
)
