# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path


project_root = Path(globals().get("SPECPATH", ".")).resolve()

datas = [
    (str(project_root / "src" / "templates"), "src/templates"),
    (str(project_root / "src" / "static"), "src/static"),
]

a = Analysis(
    ["run.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AI-Cam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
