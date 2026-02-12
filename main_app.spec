# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
spec_dir = os.getcwd()

# Данные библиотек
pandas_datas = collect_data_files("pandas")
psycopg2_datas = collect_data_files("psycopg2")
pyside6_datas = collect_data_files("PySide6")  # важно для Qt plugins

a = Analysis(
    ["main.py"],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        ("app", "app"),
    ] + pandas_datas + psycopg2_datas + pyside6_datas,
    hiddenimports=[
        # === Наша структура ===
        "app",
        "app.core",
        "app.core.database",
        "app.core.auth",
        "app.core.permissions",
        "app.core.crypto",
        "app.core.settings_manager",
        "app.core.excel_import",
        "app.core.user_management",
        "app.core.logging_config",

        "app.main_window",
        "app.splash_screen",
        "app.login_page",
        "app.home_page",
        "app.menu_spec",

        "app.dialogs",
        "app.dialogs.settings_dialog",
        "app.dialogs.user_dialogs",
        "app.dialogs.permissions_dialog",

        "app.pages",
        "app.pages.users_page",

        # === НОВОЕ: timesheet ===
        "app.modules",
        "app.modules.timesheet",
        "app.modules.timesheet.utils",
        "app.modules.timesheet.repository",
        "app.pages.timesheet_create_page",

        "app.resources",
        "app.resources.styles",
        "app.resources.logo",

        # === PySide6 ===
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",

        # === Библиотеки ===
        "psycopg2",
        "psycopg2.extras",
        "psycopg2.pool",
        "pandas",
        "openpyxl",
    ]
    + collect_submodules("pandas")
    + collect_submodules("PySide6"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    clean=True,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ConstructionSuite_v2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)
