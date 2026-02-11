"""
QSS-стили для PySide6 приложения.
"""

MAIN_STYLESHEET = """
/* === Общие стили === */
QMainWindow {
    background-color: #f5f5f5;
}

/* === Заголовок страницы === */
#PageTitle {
    font-size: 18px;
    font-weight: bold;
    color: #1a1a1a;
    padding: 8px 0;
}

#PageHint {
    font-size: 11px;
    color: #666666;
    padding: 4px 0;
}

/* === Боковая панель навигации === */
#Sidebar {
    background-color: #2c3e50;
    min-width: 220px;
    max-width: 220px;
}

#SidebarTitle {
    color: #ecf0f1;
    font-size: 14px;
    font-weight: bold;
    padding: 16px 12px 8px 12px;
}

#SidebarButton {
    background-color: transparent;
    color: #bdc3c7;
    border: none;
    text-align: left;
    padding: 10px 16px;
    font-size: 12px;
}

#SidebarButton:hover {
    background-color: #34495e;
    color: #ecf0f1;
}

#SidebarButton:checked,
#SidebarButton[active="true"] {
    background-color: #3498db;
    color: white;
    font-weight: bold;
}

#SidebarButton:disabled {
    color: #5d6d7e;
}

/* === Контентная область === */
#ContentArea {
    background-color: #f7f7f7;
    border: none;
}

/* === Кнопки === */
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #2471a3;
}

QPushButton:disabled {
    background-color: #bdc3c7;
    color: #7f8c8d;
}

QPushButton#DangerButton {
    background-color: #e74c3c;
}

QPushButton#DangerButton:hover {
    background-color: #c0392b;
}

QPushButton#SecondaryButton {
    background-color: #95a5a6;
}

QPushButton#SecondaryButton:hover {
    background-color: #7f8c8d;
}

/* === Поля ввода === */
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
    background-color: white;
    min-height: 28px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #3498db;
}

/* === Таблицы === */
QTableWidget, QTableView {
    border: 1px solid #dcdcdc;
    gridline-color: #ecf0f1;
    selection-background-color: #3498db;
    selection-color: white;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #ecf0f1;
    padding: 6px;
    border: 1px solid #d5d5d5;
    font-weight: bold;
    font-size: 11px;
}

/* === Вкладки === */
QTabWidget::pane {
    border: 1px solid #dcdcdc;
    background-color: white;
}

QTabBar::tab {
    background-color: #ecf0f1;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 2px solid #3498db;
}

/* === Подвал === */
#Footer {
    color: #999999;
    font-size: 9px;
    padding: 4px 12px;
}

/* === Экран входа === */
#LoginContainer {
    background-color: white;
    border-radius: 8px;
    padding: 32px;
}

/* === Splash screen === */
#SplashWindow {
    background-color: #f0f0f0;
    border: 1px solid #cccccc;
}
"""
