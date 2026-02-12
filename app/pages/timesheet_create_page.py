import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QTimer
)
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QMessageBox, QTableView, QHeaderView, QAbstractItemView,
    QProgressDialog, QMenu
)

from app.core.settings_manager import settings
from app.modules.timesheet.utils import (
    month_days, month_name_ru, calc_row_totals, parse_hours_and_night, parse_overtime
)
from app.modules.timesheet.repository import (
    load_employees_from_db,
    load_objects_short_for_timesheet,
    load_timesheet_rows_from_db,
    upsert_timesheet_header,
    replace_timesheet_rows,
    find_duplicate_employees_for_timesheet,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Table model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TimesheetRow:
    fio: str
    tbn: str
    hours: List[Optional[str]]  # len=31
    totals: Dict[str, Any]


class TimesheetTableModel(QAbstractTableModel):
    """
    Колонки:
      0: ФИО
      1: Таб.№
      2..(2+dim-1): дни месяца
      далее 4 итога: Дней, Часы, Пер.день, Пер.ночь
    """
    COL_FIO = 0
    COL_TBN = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._year = datetime.now().year
        self._month = datetime.now().month
        self._dim = month_days(self._year, self._month)
        self._rows: List[TimesheetRow] = []

    # ---- context ----

    def set_period(self, year: int, month: int):
        year = int(year)
        month = int(month)
        dim = month_days(year, month)

        if year == self._year and month == self._month and dim == self._dim:
            return

        self.beginResetModel()
        self._year = year
        self._month = month
        self._dim = dim
        # пересчёт totals, т.к. dim мог измениться
        for r in self._rows:
            r.totals = calc_row_totals(r.hours, self._year, self._month)
        self.endResetModel()

    @property
    def year_month(self) -> Tuple[int, int]:
        return self._year, self._month

    @property
    def dim(self) -> int:
        return self._dim

    # ---- data ----

    def set_rows_from_dicts(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = []
        for rec in rows or []:
            hours = rec.get("hours") or [None] * 31
            hours = (hours + [None] * 31)[:31]
            totals = calc_row_totals(hours, self._year, self._month)
            self._rows.append(
                TimesheetRow(
                    fio=(rec.get("fio") or "").strip(),
                    tbn=(rec.get("tbn") or "").strip(),
                    hours=hours,
                    totals=totals,
                )
            )
        self.endResetModel()

    def to_dicts(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for r in self._rows:
            out.append({"fio": r.fio, "tbn": r.tbn, "hours": list(r.hours)})
        return out

    def add_row(self, fio: str, tbn: str):
        fio = (fio or "").strip()
        tbn = (tbn or "").strip()
        if not fio:
            return
        row = TimesheetRow(
            fio=fio,
            tbn=tbn,
            hours=[None] * 31,
            totals=calc_row_totals([None] * 31, self._year, self._month),
        )
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append(row)
        self.endInsertRows()

    def remove_rows_by_source_indices(self, indices: List[int]):
        # удаляем с конца, чтобы индексы не сдвигались
        for idx in sorted(set(indices), reverse=True):
            if not (0 <= idx < len(self._rows)):
                continue
            self.beginRemoveRows(QModelIndex(), idx, idx)
            del self._rows[idx]
            self.endRemoveRows()

    # ---- Qt overrides ----

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        # fio + tbn + days + 4 totals
        return 2 + self._dim + 4

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if section == self.COL_FIO:
                return "ФИО"
            if section == self.COL_TBN:
                return "Таб.№"

            # day columns
            day_start = 2
            day_end = 2 + self._dim - 1
            if day_start <= section <= day_end:
                return str(section - day_start + 1)

            # totals
            base = 2 + self._dim
            if section == base + 0:
                return "Дней"
            if section == base + 1:
                return "Часы"
            if section == base + 2:
                return "Пер.день"
            if section == base + 3:
                return "Пер.ночь"
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        col = index.column()
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

        # редактируем только дни
        if 2 <= col < 2 + self._dim:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        rec = self._rows[row]

        # zebra
        if role == Qt.ItemDataRole.BackgroundRole:
            if col >= 2 and col < 2 + self._dim:
                # выходные подсветим
                day_num = col - 2 + 1
                wd = datetime(self._year, self._month, day_num).weekday()
                if wd == 5:
                    return QColor("#fff8e1")  # sat
                if wd == 6:
                    return QColor("#ffebee")  # sun

            if row % 2 == 1:
                return QColor("#f6f8fa")
            return QColor("#ffffff")

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == self.COL_FIO:
                return rec.fio
            if col == self.COL_TBN:
                return rec.tbn

            # days
            if 2 <= col < 2 + self._dim:
                di = col - 2
                v = rec.hours[di]
                return "" if v is None else str(v)

            # totals
            base = 2 + self._dim
            if col == base + 0:
                v = rec.totals.get("days")
                return "" if v is None else str(v)
            if col == base + 1:
                v = rec.totals.get("hours")
                return "" if v is None else str(v)
            if col == base + 2:
                v = rec.totals.get("ot_day")
                return "" if v is None else str(v)
            if col == base + 3:
                v = rec.totals.get("ot_night")
                return "" if v is None else str(v)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (self.COL_FIO,):
                return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            return int(Qt.AlignmentFlag.AlignCenter)

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False

        row = index.row()
        col = index.column()
        if not (2 <= col < 2 + self._dim):
            return False

        rec = self._rows[row]
        di = col - 2

        s = (str(value or "").strip())
        rec.hours[di] = (s if s else None)
        rec.totals = calc_row_totals(rec.hours, self._year, self._month)

        # обновляем и ячейку, и итоги строки
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])

        base = 2 + self._dim
        tl = self.index(row, base)
        br = self.index(row, base + 3)
        self.dataChanged.emit(tl, br, [Qt.ItemDataRole.DisplayRole])

        return True


class TimesheetFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._needle = ""

    def set_filter_text(self, text: str):
        self._needle = (text or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._needle:
            return True
        model: TimesheetTableModel = self.sourceModel()  # type: ignore
        fio = (model._rows[source_row].fio or "").lower()
        tbn = (model._rows[source_row].tbn or "").lower()
        return self._needle in fio or self._needle in tbn


# ──────────────────────────────────────────────────────────────────────────────
#  Page widget
# ──────────────────────────────────────────────────────────────────────────────

class TimesheetCreatePage(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # чтобы иметь доступ к current_user

        self._employees: List[Tuple[str, str, str, str]] = []
        self._objects_full: List[Tuple[str, str, str]] = []  # (excel_id, addr, short)
        self._emp_by_fio: Dict[str, Tuple[str, str, str]] = {}  # fio -> (tbn, pos, dep)
        self._deps: List[str] = ["Все"]
        self._addr_to_ids: Dict[str, List[str]] = {}

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.timeout.connect(self._auto_save)

        self._build_ui()
        self._load_reference()
        self._init_defaults()
        self._reload_from_db()

    # ---- UI ----

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # верхние контролы
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        r = 0
        grid.addWidget(QLabel("Подразделение:"), r, 0, Qt.AlignmentFlag.AlignRight)
        self.cmb_department = QComboBox()
        grid.addWidget(self.cmb_department, r, 1, 1, 3)

        r += 1
        grid.addWidget(QLabel("Месяц:"), r, 0, Qt.AlignmentFlag.AlignRight)
        self.cmb_month = QComboBox()
        self.cmb_month.addItems([month_name_ru(i) for i in range(1, 13)])
        grid.addWidget(self.cmb_month, r, 1)

        grid.addWidget(QLabel("Год:"), r, 2, Qt.AlignmentFlag.AlignRight)
        self.cmb_year = QComboBox()
        years = [str(y) for y in range(datetime.now().year - 2, datetime.now().year + 3)]
        self.cmb_year.addItems(years)
        grid.addWidget(self.cmb_year, r, 3)

        r += 1
        grid.addWidget(QLabel("Адрес:"), r, 0, Qt.AlignmentFlag.AlignRight)
        self.cmb_address = QComboBox()
        self.cmb_address.setEditable(True)
        self.cmb_address.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        grid.addWidget(self.cmb_address, r, 1, 1, 2)

        grid.addWidget(QLabel("ID объекта:"), r, 3, Qt.AlignmentFlag.AlignRight)
        self.cmb_object_id = QComboBox()
        self.cmb_object_id.setEditable(False)
        grid.addWidget(self.cmb_object_id, r, 4)

        # строка добавления сотрудника
        r += 1
        grid.addWidget(QLabel("ФИО:"), r, 0, Qt.AlignmentFlag.AlignRight)
        self.cmb_fio = QComboBox()
        self.cmb_fio.setEditable(True)
        self.cmb_fio.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        grid.addWidget(self.cmb_fio, r, 1, 1, 2)

        grid.addWidget(QLabel("Таб.№:"), r, 3, Qt.AlignmentFlag.AlignRight)
        self.ed_tbn = QLineEdit()
        self.ed_tbn.setMaximumWidth(130)
        grid.addWidget(self.ed_tbn, r, 4)

        r += 1
        grid.addWidget(QLabel("Должность:"), r, 0, Qt.AlignmentFlag.AlignRight)
        self.ed_pos = QLineEdit()
        self.ed_pos.setReadOnly(True)
        grid.addWidget(self.ed_pos, r, 1, 1, 4)

        layout.addLayout(grid)

        # кнопки
        btns = QHBoxLayout()
        self.btn_add = QPushButton("Добавить в табель")
        self.btn_add.clicked.connect(self._on_add_row)
        btns.addWidget(self.btn_add)

        self.btn_add_dep = QPushButton("Добавить подразделение")
        self.btn_add_dep.setObjectName("SecondaryButton")
        self.btn_add_dep.clicked.connect(self._on_add_department_all)
        btns.addWidget(self.btn_add_dep)

        self.btn_delete = QPushButton("Удалить выбранные")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self._on_delete_selected)
        btns.addWidget(self.btn_delete)

        btns.addStretch()

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btns.addWidget(self.btn_save)

        layout.addLayout(btns)

        # фильтр
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Поиск:"))
        self.ed_filter = QLineEdit()
        self.ed_filter.setPlaceholderText("ФИО или таб.№...")
        self.ed_filter.textChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self.ed_filter, 1)

        btn_clear = QPushButton("Очистить")
        btn_clear.setObjectName("SecondaryButton")
        btn_clear.clicked.connect(lambda: self.ed_filter.setText(""))
        filter_bar.addWidget(btn_clear)
        layout.addLayout(filter_bar)

        # таблица
        self.model = TimesheetTableModel(self)
        self.proxy = TimesheetFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)

        layout.addWidget(self.table, 1)

        # итог внизу
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("Сумма: сотрудников 0 | дней 0 | часов 0 | в т.ч. ночных 0 | пер.день 0 | пер.ночь 0")
        bottom.addWidget(self.lbl_total)
        bottom.addStretch()
        self.lbl_autosave = QLabel("Последнее авто‑сохранение: нет")
        self.lbl_autosave.setStyleSheet("color: #555;")
        bottom.addWidget(self.lbl_autosave)
        layout.addLayout(bottom)

        # события
        self.cmb_department.currentTextChanged.connect(self._on_department_changed)
        self.cmb_address.currentTextChanged.connect(self._on_address_changed)
        self.cmb_object_id.currentTextChanged.connect(lambda _t: self._reload_from_db())
        self.cmb_month.currentIndexChanged.connect(self._on_period_changed)
        self.cmb_year.currentTextChanged.connect(self._on_period_changed)
        self.cmb_fio.currentTextChanged.connect(self._on_fio_changed)

        # если редактируем — перезапуск автосейва и пересчёт низа
        self.model.dataChanged.connect(lambda *_: self._on_any_change())

    # ---- reference ----

    def _load_reference(self):
        self._employees = load_employees_from_db()
        self._objects_full = load_objects_short_for_timesheet()

        # deps
        deps = sorted({(dep or "").strip() for (_fio, _tbn, _pos, dep) in self._employees if (dep or "").strip()})
        self._deps = ["Все"] + deps
        self.cmb_department.clear()
        self.cmb_department.addItems(self._deps)

        # employees
        self._emp_by_fio = {}
        fio_list = []
        for fio, tbn, pos, dep in self._employees:
            fio = fio or ""
            fio_list.append(fio)
            self._emp_by_fio[fio] = (tbn or "", pos or "", dep or "")
        fio_list = sorted(set(fio_list))
        self.cmb_fio.clear()
        self.cmb_fio.addItems(fio_list)

        # address -> ids
        self._addr_to_ids = {}
        addresses = []
        for oid, addr, _short in self._objects_full:
            if not addr:
                continue
            addresses.append(addr)
            self._addr_to_ids.setdefault(addr, [])
            if oid and oid not in self._addr_to_ids[addr]:
                self._addr_to_ids[addr].append(oid)

        self.cmb_address.clear()
        self.cmb_address.addItems(sorted(set(addresses)))

    def _init_defaults(self):
        # department from settings
        dep = settings.get("UI", "selected_department")
        if dep and dep in self._deps:
            self.cmb_department.setCurrentText(dep)

        # current date
        self.cmb_month.setCurrentIndex(datetime.now().month - 1)
        y = str(datetime.now().year)
        idx = self.cmb_year.findText(y)
        if idx >= 0:
            self.cmb_year.setCurrentIndex(idx)

        self._sync_object_ids()

    # ---- helpers ----

    def _current_user_id(self) -> Optional[int]:
        return (self.main_window.current_user or {}).get("id")

    def _current_role(self) -> str:
        return ((self.main_window.current_user or {}).get("role") or "specialist").lower()

    def _period(self) -> Tuple[int, int]:
        year = int(self.cmb_year.currentText())
        month = self.cmb_month.currentIndex() + 1
        return year, month

    def _sync_object_ids(self):
        addr = (self.cmb_address.currentText() or "").strip()
        ids = sorted(self._addr_to_ids.get(addr, []))
        cur = self.cmb_object_id.currentText()

        self.cmb_object_id.blockSignals(True)
        try:
            self.cmb_object_id.clear()
            self.cmb_object_id.addItem("")  # allow empty
            self.cmb_object_id.addItems(ids)
            if cur and cur in ids:
                self.cmb_object_id.setCurrentText(cur)
            elif len(ids) == 1:
                self.cmb_object_id.setCurrentText(ids[0])
            else:
                self.cmb_object_id.setCurrentText("")
        finally:
            self.cmb_object_id.blockSignals(False)

    def _allowed_fio_set(self) -> set[str]:
        dep = (self.cmb_department.currentText() or "Все").strip()
        if dep == "Все":
            return {fio for (fio, _tbn, _pos, _dep) in self._employees}
        return {fio for (fio, _tbn, _pos, d) in self._employees if (d or "").strip() == dep}

    # ---- events ----

    def _on_department_changed(self, dep: str):
        # сохранить выбор в settings
        try:
            settings.set("UI", "selected_department", dep)
            settings.save()
        except Exception:
            logger.exception("Не удалось сохранить selected_department")

        # ограничить список ФИО
        allowed = self._allowed_fio_set()
        all_fio = sorted({fio for (fio, _tbn, _pos, _dep) in self._employees})
        self.cmb_fio.blockSignals(True)
        try:
            self.cmb_fio.clear()
            self.cmb_fio.addItems(sorted(allowed) if dep != "Все" else all_fio)
        finally:
            self.cmb_fio.blockSignals(False)

        # если выбранное ФИО стало недоступным — очистим
        fio = (self.cmb_fio.currentText() or "").strip()
        if fio and fio not in allowed:
            self.cmb_fio.setCurrentText("")
            self.ed_tbn.setText("")
            self.ed_pos.setText("")

        self._reload_from_db()

    def _on_period_changed(self, *_):
        y, m = self._period()
        self.model.set_period(y, m)
        self._reload_from_db()

    def _on_address_changed(self, *_):
        self._sync_object_ids()
        self._reload_from_db()

    def _on_fio_changed(self, fio: str):
        fio = (fio or "").strip()
        tbn, pos, _dep = self._emp_by_fio.get(fio, ("", "", ""))
        self.ed_tbn.setText(tbn)
        self.ed_pos.setText(pos)

    def _on_filter_changed(self, text: str):
        self.proxy.set_filter_text(text)
        self._recalc_total_label()

    def _on_any_change(self):
        # автосейв
        self._auto_save_timer.start(8000)
        self._recalc_total_label()

    # ---- actions ----

    def _on_add_row(self):
        dep = (self.cmb_department.currentText() or "Все").strip()
        if dep == "Все":
            QMessageBox.warning(self, "Объектный табель", "Выберите конкретное подразделение (не 'Все').")
            return

        fio = (self.cmb_fio.currentText() or "").strip()
        tbn = (self.ed_tbn.text() or "").strip()

        if not fio:
            QMessageBox.warning(self, "Объектный табель", "Выберите ФИО.")
            return

        allowed = self._allowed_fio_set()
        if fio not in allowed:
            QMessageBox.warning(
                self,
                "Объектный табель",
                "Такого сотрудника нет в списке сотрудников текущего подразделения.\n"
                "Добавление в табель запрещено.",
            )
            return

        # предупреждение о дубле в текущем табеле
        existing = {(r["fio"].lower(), (r.get("tbn") or "").strip()) for r in self.model.to_dicts()}
        key = (fio.lower(), tbn.strip())
        if key in existing:
            ans = QMessageBox.question(
                self,
                "Дублирование",
                f"Сотрудник уже есть в табеле:\n{fio} (Таб.№ {tbn}).\nДобавить ещё одну строку?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        self.model.add_row(fio, tbn)
        self._recalc_total_label()

    def _on_add_department_all(self):
        dep = (self.cmb_department.currentText() or "Все").strip()
        if dep == "Все":
            QMessageBox.warning(self, "Объектный табель", "Выберите конкретное подразделение (не 'Все').")
            return

        candidates = [e for e in self._employees if (e[3] or "").strip() == dep]
        if not candidates:
            QMessageBox.information(self, "Объектный табель", f"В подразделении «{dep}» нет сотрудников.")
            return

        confirm = QMessageBox.question(
            self,
            "Добавить подразделение",
            f"Добавить в табель всех сотрудников подразделения «{dep}»?\n\n"
            f"Количество: {len(candidates)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # чтобы не зависеть от фильтра — работаем по source model
        existing = {(r["fio"].lower(), (r.get("tbn") or "").strip()) for r in self.model.to_dicts()}

        progress = QProgressDialog("Добавление сотрудников...", "Отмена", 0, len(candidates), self)
        progress.setWindowTitle("Добавление сотрудников")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        added = 0
        for i, (fio, tbn, _pos, _dep) in enumerate(candidates, start=1):
            if progress.wasCanceled():
                break
            progress.setValue(i)

            key = (fio.lower(), (tbn or "").strip())
            if key in existing:
                continue
            self.model.add_row(fio, tbn or "")
            existing.add(key)
            added += 1

        progress.setValue(len(candidates))
        self._recalc_total_label()
        self._auto_save_timer.start(8000)

        if added > 0:
            QMessageBox.information(self, "Объектный табель", f"Добавлено новых сотрудников: {added}")
        else:
            QMessageBox.information(self, "Объектный табель", "Все сотрудники из этого подразделения уже в списке.")

    def _selected_source_row_indices(self) -> List[int]:
        sel = self.table.selectionModel().selectedRows()
        src_indices = []
        for idx in sel:
            src = self.proxy.mapToSource(idx)
            if src.isValid():
                src_indices.append(src.row())
        return sorted(set(src_indices))

    def _on_delete_selected(self):
        rows = self._selected_source_row_indices()
        if not rows:
            QMessageBox.information(self, "Удалить", "Не выбрано ни одной строки.")
            return

        ans = QMessageBox.question(
            self,
            "Удалить",
            f"Удалить выбранные строки: {len(rows)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        self.model.remove_rows_by_source_indices(rows)
        self._recalc_total_label()
        self._auto_save_timer.start(8000)

    def _on_table_context_menu(self, pos):
        menu = QMenu(self)
        act_del = QAction("Удалить выбранные", self)
        act_del.triggered.connect(self._on_delete_selected)
        menu.addAction(act_del)
        menu.exec(self.table.mapToGlobal(pos))

    def _validate_before_save(self) -> Optional[Tuple[str, Optional[str], str, int, int, int]]:
        """
        Возвращает (addr, oid, dep, y, m, user_id) или None.
        """
        dep = (self.cmb_department.currentText() or "").strip()
        if dep == "Все":
            QMessageBox.warning(self, "Сохранение", "Для сохранения выберите конкретное подразделение (не 'Все').")
            return None

        user_id = self._current_user_id()
        if not user_id:
            QMessageBox.critical(self, "Сохранение", "Не удалось определить пользователя.")
            return None

        addr = (self.cmb_address.currentText() or "").strip()
        oid = (self.cmb_object_id.currentText() or "").strip() or None

        if not addr:
            QMessageBox.warning(self, "Сохранение", "Не задан адрес объекта. Выберите адрес из списка.")
            return None

        # если несколько ID на адрес, но oid не выбран — запрещаем
        ids = sorted(self._addr_to_ids.get(addr, []))
        if len(ids) > 1 and not oid:
            QMessageBox.warning(
                self,
                "Сохранение",
                "По выбранному адресу найдено несколько объектов.\n"
                "Сначала выберите корректный ID объекта.",
            )
            return None

        y, m = self._period()
        return addr, oid, dep, y, m, user_id

    def _on_save_clicked(self):
        self._save(show_messages=True, is_auto=False)

    def _auto_save(self):
        self._save(show_messages=False, is_auto=True)

    def _save(self, show_messages: bool, is_auto: bool):
        ctx = self._validate_before_save()
        if ctx is None:
            return
        addr, oid, dep, y, m, user_id = ctx

        # check duplicates across users
        employees_for_check = []
        for rec in self.model.to_dicts():
            fio = (rec.get("fio") or "").strip()
            tbn = (rec.get("tbn") or "").strip()
            if fio or tbn:
                employees_for_check.append((fio, tbn))

        try:
            duplicates = find_duplicate_employees_for_timesheet(
                object_id=oid,
                object_addr=addr,
                department=dep,
                year=y,
                month=m,
                user_id=user_id,
                employees=employees_for_check,
            )
        except Exception as e:
            logger.exception("Ошибка проверки дублей")
            if show_messages:
                QMessageBox.critical(self, "Сохранение", f"Ошибка при проверке дублей сотрудников:\n{e}")
            return

        if duplicates:
            if show_messages:
                lines = []
                for d in duplicates:
                    emp_fio = d.get("fio") or ""
                    emp_tbn = d.get("tbn") or ""
                    uname = d.get("full_name") or d.get("username") or f"id={d.get('user_id')}"
                    lines.append(f"- {emp_fio} (таб.№ {emp_tbn}) — уже есть у {uname}")
                QMessageBox.warning(
                    self,
                    "Дубли сотрудников",
                    "Найдены сотрудники, которые уже есть в табелях других пользователей "
                    "по этому объекту/подразделению/месяцу:\n\n"
                    + "\n".join(lines)
                    + "\n\nСохранение отменено.",
                )
            return

        # save to DB
        try:
            header_id = upsert_timesheet_header(oid, addr, dep, y, m, user_id)
            replace_timesheet_rows(header_id, self.model.to_dicts())
        except Exception as e:
            logger.exception("Ошибка сохранения табеля")
            if show_messages:
                QMessageBox.critical(self, "Сохранение", f"Ошибка сохранения в БД:\n{e}")
            return

        if show_messages:
            QMessageBox.information(self, "Сохранение", "Табель сохранён в БД.")
        if is_auto:
            self._update_autosave_label()

    def _update_autosave_label(self):
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.lbl_autosave.setText(f"Последнее авто‑сохранение: {now}")

    # ---- load from DB ----

    def _reload_from_db(self):
        dep = (self.cmb_department.currentText() or "").strip()
        if dep == "Все":
            self.model.set_rows_from_dicts([])
            self._recalc_total_label()
            return

        user_id = self._current_user_id()
        if not user_id:
            self.model.set_rows_from_dicts([])
            self._recalc_total_label()
            return

        addr = (self.cmb_address.currentText() or "").strip()
        oid = (self.cmb_object_id.currentText() or "").strip() or None
        y, m = self._period()

        self.model.set_period(y, m)

        try:
            rows = load_timesheet_rows_from_db(
                object_id=oid,
                object_addr=addr,
                department=dep,
                year=y,
                month=m,
                user_id=user_id,
            )
            self.model.set_rows_from_dicts(rows)
        except Exception as e:
            logger.exception("Ошибка загрузки табеля из БД")
            QMessageBox.critical(self, "Загрузка", f"Не удалось загрузить табель из БД:\n{e}")
            self.model.set_rows_from_dicts([])

        self._recalc_total_label()

    # ---- totals ----

    def _recalc_total_label(self):
        # считаем по ВСЕМ строкам (source model), а не по фильтру
        tot_h = 0.0
        tot_d = 0
        tot_night = 0.0
        tot_ot_day = 0.0
        tot_ot_night = 0.0

        y, m = self.model.year_month
        dim = self.model.dim

        rows = self.model.to_dicts()
        for rec in rows:
            hours_list = rec.get("hours") or []
            for i in range(min(dim, len(hours_list))):
                raw = hours_list[i]
                if not raw:
                    continue

                hv, night = parse_hours_and_night(raw)
                d_ot, n_ot = parse_overtime(raw)

                if isinstance(hv, (int, float)) and hv > 1e-12:
                    tot_h += float(hv)
                    tot_d += 1
                if isinstance(night, (int, float)):
                    tot_night += float(night)
                if isinstance(d_ot, (int, float)):
                    tot_ot_day += float(d_ot)
                if isinstance(n_ot, (int, float)):
                    tot_ot_night += float(n_ot)

        def fmt(x: float) -> str:
            return f"{x:.2f}".rstrip("0").rstrip(".")

        self.lbl_total.setText(
            f"Сумма: сотрудников {len(rows)} | дней {tot_d} | часов {fmt(tot_h)} | "
            f"в т.ч. ночных {fmt(tot_night)} | пер.день {fmt(tot_ot_day)} | пер.ночь {fmt(tot_ot_night)}"
        )
