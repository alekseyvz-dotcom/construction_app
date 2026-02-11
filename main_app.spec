# main_app.spec
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
spec_dir = os.getcwd()

# Сбор данных для библиотек
pandas_datas = collect_data_files('pandas')
psycopg2_datas = collect_data_files('psycopg2')
pyside6_datas = collect_data_files('PySide6')

a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        # Пакет app целиком
        ('app', 'app'),

        # Старые модули (пока не переписаны)
        ('meals_module.py', '.'),
        ('meals_employees.py', '.'),
        ('meals_reports.py', '.'),
        ('SpecialOrders.py', '.'),
        ('lodging_module.py', '.'),
        ('objects.py', '.'),
        ('timesheet_transformer.py', '.'),
        ('virtual_timesheet_grid.py', '.'),
        ('timesheet_compare.py', '.'),
        ('timesheet_module.py', '.'),
        ('employees.py', '.'),
        ('BudgetAnalyzer.py', '.'),
        ('employee_card.py', '.'),
        ('analytics_module.py', '.'),
        ('assets_logo.py', '.'),
    ] + pandas_datas + psycopg2_datas + pyside6_datas,
    hiddenimports=[
        # Новая структура
        'app',
        'app.core',
        'app.core.database',
        'app.core.auth',
        'app.core.permissions',
        'app.core.crypto',
        'app.core.settings_manager',
        'app.core.excel_import',
        'app.core.user_management',
        'app.core.logging_config',
        'app.main_window',
        'app.splash_screen',
        'app.login_page',
        'app.home_page',
        'app.menu_spec',
        'app.dialogs',
        'app.dialogs.settings_dialog',
        'app.dialogs.user_dialogs',
        'app.dialogs.permissions_dialog',
        'app.pages',
        'app.pages.users_page',
        'app.resources',
        'app.resources.styles',
        'app.resources.logo',

        # PySide6
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',

        # Старые модули
        'meals_module',
        'meals_employees',
        'meals_reports',
        'SpecialOrders',
        'lodging_module',
        'objects',
        'assets_logo',
        'timesheet_transformer',
        'timesheet_compare',
        'virtual_timesheet_grid',
        'employees',
        'BudgetAnalyzer',
        'timesheet_module',
        'employee_card',
        'analytics_module',

        # Библиотеки
        'psycopg2',
        'psycopg2.extras',
        'psycopg2.pool',
        'pandas',
        'openpyxl',
    ] + collect_submodules('pandas') + collect_submodules('PySide6'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Исключаем tkinter — больше не нужен
        'tkinter',
        '_tkinter',
        'PIL',  # Если не используется в других модулях
    ],
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
    name='ConstructionSuite_v2',
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
    icon='icon.ico',
)
