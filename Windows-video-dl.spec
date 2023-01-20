# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[
        ('dependencies/avcodec-59.dll', '.'),
        ('dependencies/avdevice-59.dll', '.'),
        ('dependencies/avfilter-8.dll', '.'),
        ('dependencies/avformat-59.dll', '.'),
        ('dependencies/avutil-57.dll', '.'),
        ('dependencies/postproc-56.dll', '.'),
        ('dependencies/swresample-4.dll', '.'),
        ('dependencies/swscale-6.dll', '.')
    ],
    datas=[
        ('dependencies/ffmpeg.exe', '.'),
        ('dependencies/ffprobe.exe', '.')
    ],
    hiddenimports=[],
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
    name='video-dl.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
