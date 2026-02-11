"""
Диалог редактирования прав доступа пользователя.
"""
import logging
from typing import Dict, List, Set, Optional
from collections import defaultdict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QScrollArea, QCheckBox, QLabel, QLineEdit, QPushButton,
    QMessageBox, QGridLayout, QFrame,
)
from PySide6.QtCore import Qt

from app.core.user_management import (
    get_permissions_catalog,
    get_user_permissions,
    set_user_permissions,
)

logger = logging.getLogger(__name__)


class PermissionsDialog(QDialog):
    """Окно редактирования прав пользователя с вкладками по группам."""

    def __init__(
        self,
        user_id: int,
        username: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Права доступа — {username}")
        self.setMinimumSize(780, 540)
        self.resize(780, 540)

        self.user_id = user_id
        self.username = username

        # Загрузка данных
        try:
            self._catalog: List[Dict] = get_permissions_catalog()
            self._current: Set[str] = get_user_permissions(user_id)
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить права:\n{e}",
            )
            self.reject()
            return

        # code -> QCheckBox
        self._checkboxes: Dict[str, QCheckBox] = {}
        # code -> meta dict
        self._meta: Dict[str, Dict] = {}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── Верхняя панель: поиск + кнопки ──────────────────────
        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Название или код права...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        self.search_input.setMinimumWidth(250)
        top_bar.addWidget(self.search_input)

        top_bar.addStretch()

        btn_select_all = QPushButton("Выбрать всё (видимое)")
        btn_select_all.setObjectName("SecondaryButton")
        btn_select_all.clicked.connect(self._select_all_visible)
        top_bar.addWidget(btn_select_all)

        btn_clear_all = QPushButton("Снять всё (видимое)")
        btn_clear_all.setObjectName("SecondaryButton")
        btn_clear_all.clicked.connect(self._clear_all_visible)
        top_bar.addWidget(btn_clear_all)

        layout.addLayout(top_bar)

        # ── Вкладки по группам ──────────────────────────────────
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Группируем права
        groups: Dict[str, List[Dict]] = defaultdict(list)
        for perm in self._catalog:
            group = (perm.get("group_name") or "").strip() or "Другое"
            groups[group].append(perm)

        for group_name in sorted(groups.keys()):
            tab = self._create_group_tab(group_name, groups[group_name])
            self.tab_widget.addTab(tab, group_name)

        # ── Нижние кнопки ───────────────────────────────────────
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(btn_cancel)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._on_save)
        bottom_bar.addWidget(btn_save)

        layout.addLayout(bottom_bar)

    def _create_group_tab(
        self, group_name: str, permissions: List[Dict],
    ) -> QWidget:
        """Создаёт вкладку с прокручиваемым списком чекбоксов."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопки для вкладки
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(8, 8, 8, 4)
        btn_bar.addStretch()

        btn_sel = QPushButton("Выбрать всё")
        btn_sel.setObjectName("SecondaryButton")
        btn_sel.setMaximumWidth(120)
        btn_sel.clicked.connect(
            lambda checked=False, g=group_name: self._select_group(g)
        )
        btn_bar.addWidget(btn_sel)

        btn_clr = QPushButton("Снять всё")
        btn_clr.setObjectName("SecondaryButton")
        btn_clr.setMaximumWidth(120)
        btn_clr.clicked.connect(
            lambda checked=False, g=group_name: self._clear_group(g)
        )
        btn_bar.addWidget(btn_clr)

        tab_layout.addLayout(btn_bar)

        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(12, 8, 12, 8)

        for perm in permissions:
            code = perm["code"]
            title = perm.get("title") or code

            cb = QCheckBox(f"{title}  [{code}]")
            cb.setChecked(code in self._current)

            self._checkboxes[code] = cb
            self._meta[code] = perm
            content_layout.addWidget(cb)

        content_layout.addStretch()
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)

        return tab

    # ── Фильтрация ──────────────────────────────────────────────

    def _apply_filter(self):
        needle = self.search_input.text().strip().lower()

        for code, cb in self._checkboxes.items():
            meta = self._meta[code]
            haystack = (
                f"{meta.get('title', '')} {meta.get('code', '')} "
                f"{meta.get('group_name', '')}"
            ).lower()

            visible = (not needle) or (needle in haystack)
            cb.setVisible(visible)

    def _visible_codes(self) -> List[str]:
        return [
            code for code, cb in self._checkboxes.items()
            if cb.isVisible()
        ]

    # ── Групповые операции ──────────────────────────────────────

    def _select_all_visible(self):
        for code in self._visible_codes():
            self._checkboxes[code].setChecked(True)

    def _clear_all_visible(self):
        for code in self._visible_codes():
            self._checkboxes[code].setChecked(False)

    def _select_group(self, group_name: str):
        for code, meta in self._meta.items():
            group = (meta.get("group_name") or "").strip() or "Другое"
            if group == group_name:
                self._checkboxes[code].setChecked(True)

    def _clear_group(self, group_name: str):
        for code, meta in self._meta.items():
            group = (meta.get("group_name") or "").strip() or "Другое"
            if group == group_name:
                self._checkboxes[code].setChecked(False)

    # ── Сохранение ──────────────────────────────────────────────

    def _on_save(self):
        selected = [
            code for code, cb in self._checkboxes.items()
            if cb.isChecked()
        ]

        try:
            set_user_permissions(self.user_id, selected)
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить права:\n{e}",
            )
            return

        QMessageBox.information(
            self, "Права",
            f"Права пользователя '{self.username}' сохранены "
            f"({len(selected)} прав).",
        )
        self.accept()
