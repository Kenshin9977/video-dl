# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files
ROOTDIR = os.path.abspath(os.path.join(SPECPATH, '..'))

_version = {}
exec(open(os.path.join(ROOTDIR, 'version.py')).read(), _version)
APP_VERSION = _version['__version__']

block_cipher = None

flet_data = collect_data_files('flet')
flet_desktop_data = collect_data_files('flet_desktop')

a = Analysis(
    [os.path.join(ROOTDIR, 'main.py')],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(ROOTDIR, 'root.json'), '.'),
        (os.path.join(ROOTDIR, 'icon.icns'), '.'),
        (os.path.join(ROOTDIR, 'assets'), 'assets'),
    ] + flet_data + flet_desktop_data,
    # yt-dlp imports these inside try/except ImportError and quietly does without
    # them, so a binary that failed to collect one still starts and only breaks
    # later, on audio tagging or AES. main.py --selftest enforces their presence.
    hiddenimports=[
        'flet_desktop',
        'Cryptodome.Cipher.AES',
        'brotli',
        'mutagen',
        'websockets',
    ],
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
    [],
    exclude_binaries=True,
    name='video-dl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOTDIR, 'icon.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='video-dl',
)

app = BUNDLE(
    coll,
    name='video-dl.app',
    icon=os.path.join(ROOTDIR, 'icon.icns'),
    bundle_identifier='com.kenshin.video-dl',
    info_plist={
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleName': 'video-dl',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,
    },
)
