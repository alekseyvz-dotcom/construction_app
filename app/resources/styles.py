"""
QSS-стили для PySide6 приложения.
"""

MAIN_STYLESHEET = """
/* ═══════════════════════════════════════════
   ОБЩИЕ
   ═══════════════════════════════════════════ */
QMainWindow {
    background-color: #f5f5f5;
}

/* ═══════════════════════════════════════════
   ВЕРХНЯЯ ПАНЕЛЬ НАВИГАЦИИ
   ═══════════════════════════════════════════ */
#NavBar {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #2c3e50, stop:1 #1a252f
    );
    min-height: 48px;
    max-height: 48px;
    border-bottom: 2px solid #3498db;
}

#NavAppTitle {
    color: #ecf0f1;
    font-size: 15px;
    font-weight: bold;
    padding: 0 16px 0 8px;
    font-family: "Segoe UI", Arial;
}

#NavButton {
    background: transparent;
    color: #bdc3c7;
    border: none;
    border-radius: 4px;
    padding: 8px 14px;
    font-size: 12px;
    font-family: "Segoe UI", Arial;
    font-weight: 500;
    margin: 4px 2px;
}

#NavButton:hover {
    background-color: rgba(52, 152, 219, 0.3);
    color: #ffffff;
}

#NavButton:pressed {
    background-color: rgba(52, 152, 219, 0.5);
}

#NavButton:checked,
#NavButton[active="true"] {
    background-color: #3498db;
    color: #ffffff;
    font-weight: bold;
}

#NavButton:disabled {
    color: #5d6d7e;
}

#NavHomeButton {
    background: transparent;
    color: #ecf0f1;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
    font-family: "Segoe UI", Arial;
    font-weight: bold;
    margin: 4px 2px;
}

#NavHomeButton:hover {
    background-color: rgba(46, 204, 113, 0.3);
    color: #ffffff;
}

#NavHomeButton:pressed {
    background-color: rgba(46, 204, 113, 0.5);
}

#NavSettingsButton {
    background: transparent;
    color: #95a5a6;
    border: none;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: "Segoe UI", Arial;
    margin: 4px 2px;
}

#NavSettingsButton:hover {
    background-color: rgba(149, 165, 166, 0.3);
    color: #ecf0f1;
}

#NavSettingsButton:disabled {
    color: #5d6d7e;
}

#NavSeparator {
    background-color: #3d5266;
    min-width: 1px;
    max-width: 1px;
    margin: 10px 4px;
}

#NavUserLabel {
    color: #7f8c8d;
    font-size: 11px;
    padding: 0 12px;
    font-family: "Segoe UI", Arial;
}

/* ═══════════════════════════════════════════
   ВЫПАДАЮЩИЕ МЕНЮ (от кнопок навбара)
   ═══════════════════════════════════════════ */
QMenu {
    background-color: #2c3e50;
    border: 1px solid #3d5266;
    border-radius: 6px;
    padding: 6px 0;
}

QMenu::item {
    background: transparent;
    color: #bdc3c7;
    padding: 8px 32px 8px 16px;
    font-size: 12px;
    font-family: "Segoe UI", Arial;
    border-radius: 0;
}

QMenu::item:selected {
    background-color: #3498db;
    color: #ffffff;
}

QMenu::item:disabled {
    color: #5d6d7e;
}

QMenu::separator {
    height: 1px;
    background: #3d5266;
    margin: 4px 8px;
}

QMenu::indicator {
    width: 18px;
    height: 18px;
    margin-left: 6px;
}

/* ═══════════════════════════════════════════
   ЗАГОЛОВОК СТРАНИЦЫ
   ═══════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════
   КОНТЕНТНАЯ ОБЛАСТЬ
   ═══════════════════════════════════════════ */
#ContentArea {
    background-color: #f7f7f7;
    border: none;
}

/* ═══════════════════════════════════════════
   КНОПКИ
   ═══════════════════════════════════════════ */
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    font-family: "Segoe UI", Arial;
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

/* ═══════════════════════════════════════════
   ПОЛЯ ВВОДА
   ═══════════════════════════════════════════ */
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
    background-color: white;
    min-height: 28px;
    font-family: "Segoe UI", Arial;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #3498db;
    border-width: 2px;
}

/* ═══════════════════════════════════════════
   ТАБЛИЦЫ
   ═══════════════════════════════════════════ */
QTableWidget, QTableView {
    border: 1px solid #dcdcdc;
    gridline-color: #ecf0f1;
    selection-background-color: #3498db;
    selection-color: white;
    font-size: 12px;
    alternate-background-color: #f9f9f9;
    font-family: "Segoe UI", Arial;
}

QHeaderView::section {
    background-color: #ecf0f1;
    padding: 6px;
    border: 1px solid #d5d5d5;
    font-weight: bold;
    font-size: 11px;
}

/* ═══════════════════════════════════════════
   ВКЛАДКИ
   ═══════════════════════════════════════════ */
QTabWidget::pane {
    border: 1px solid #dcdcdc;
    background-color: white;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #ecf0f1;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-family: "Segoe UI", Arial;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 2px solid #3498db;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #d5dbdb;
}

/* ═══════════════════════════════════════════
   ГРУППЫ (QGroupBox)
   ═══════════════════════════════════════════ */
QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-family: "Segoe UI", Arial;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #2c3e50;
}

/* ═══════════════════════════════════════════
   ПОДВАЛ
   ═══════════════════════════════════════════ */
#Footer {
    color: #999999;
    font-size: 9px;
    padding: 4px 12px;
    font-family: "Segoe UI", Arial;
}

/* ═══════════════════════════════════════════
   ЭКРАН ВХОДА
   ═══════════════════════════════════════════ */
#LoginContainer {
    background-color: white;
    border-radius: 8px;
    padding: 32px;
}

/* ═══════════════════════════════════════════
   ДИАЛОГОВЫЕ ОКНА
   ═══════════════════════════════════════════ */
QDialog {
    background-color: #f5f5f5;
}

/* ═══════════════════════════════════════════
   СКРОЛЛБАРЫ
   ═══════════════════════════════════════════ */
QScrollBar:vertical {
    border: none;
    background: #f0f0f0;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #bdc3c7;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #95a5a6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    border: none;
    background: #f0f0f0;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #bdc3c7;
    min-width: 30px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: #95a5a6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ═══════════════════════════════════════════
   ПРОГРЕСС-БАР
   ═══════════════════════════════════════════ */
QProgressBar {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    text-align: center;
    background-color: #ecf0f1;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #3498db, stop:1 #2ecc71
    );
    border-radius: 3px;
}

/* ═══════════════════════════════════════════
   ЧЕКБОКСЫ
   ═══════════════════════════════════════════ */
QCheckBox {
    spacing: 8px;
    font-family: "Segoe UI", Arial;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #bdc3c7;
    border-radius: 3px;
    background: white;
}

QCheckBox::indicator:checked {
    background-color: #3498db;
    border-color: #3498db;
}

QCheckBox::indicator:hover {
    border-color: #3498db;
}

/* ═══════════════════════════════════════════
   СТАТУСБАР
   ═══════════════════════════════════════════ */
QStatusBar {
    background-color: #ecf0f1;
    border-top: 1px solid #d5d5d5;
    font-size: 11px;
    color: #555;
    font-family: "Segoe UI", Arial;
}
"""
