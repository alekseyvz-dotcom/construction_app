import calendar
import re
import difflib
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple


def month_days(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_name_ru(month: int) -> str:
    return [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ][month - 1]


def parse_hours_value(v: Any) -> Optional[float]:
    """
    Парсит строку часов:
      - '8' / '8,25'
      - '8:30'
      - '1/7' => сумма частей
      - отсекает часть в скобках (переработка)
    """
    s = str(v or "").strip()
    if not s:
        return None
    if "(" in s:
        s = s.split("(", 1)[0].strip()

    if "/" in s:
        total = 0.0
        for part in s.split("/"):
            n = parse_hours_value(part)
            if isinstance(n, (int, float)):
                total += float(n)
        return total if total > 0 else None

    if ":" in s:
        p = s.split(":")
        try:
            hh = float(p[0].replace(",", "."))
            mm = float((p[1] if len(p) > 1 else "0").replace(",", "."))
            return hh + mm / 60.0
        except Exception:
            return None

    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def parse_overtime(v: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Переработка хранится в скобках:
      - "8(2)" => (2, 0)
      - "8(1/1)" => (1, 1)
    """
    s = str(v or "").strip()
    if "(" not in s or ")" not in s:
        return None, None
    try:
        overtime_str = s[s.index("(") + 1:s.index(")")].strip()
        if "/" in overtime_str:
            parts = overtime_str.split("/")
            day_ot = float(parts[0].replace(",", ".")) if parts[0].strip() else 0.0
            night_ot = float(parts[1].replace(",", ".")) if len(parts) > 1 and parts[1].strip() else 0.0
            return day_ot, night_ot
        return float(overtime_str.replace(",", ".")), 0.0
    except Exception:
        return None, None


def parse_hours_and_night(v: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    Парсит отработанные часы вне скобок.
    Возвращает (total_hours, night_hours).

    Правила:
      - '8' / '8,25' / '8:30' -> (8, 0) / (8.25, 0) / (8.5, 0)
      - '8/2' -> (10, 2)  (ночные входят в total)
      - '8/2/1' -> (11, 3)
      - '8/2(1/1)' -> учитываем только '8/2' как (10, 2)
    """
    s = str(v or "").strip()
    if not s:
        return None, None

    if "(" in s:
        s = s.split("(", 1)[0].strip()
    if not s:
        return None, None

    def _to_hours(x: str) -> Optional[float]:
        x = (x or "").strip()
        if not x:
            return None
        if ":" in x:
            p = x.split(":")
            try:
                hh = float(p[0].replace(",", "."))
                mm = float((p[1] if len(p) > 1 else "0").replace(",", "."))
                return hh + mm / 60.0
            except Exception:
                return None
        try:
            return float(x.replace(",", "."))
        except Exception:
            return None

    if "/" in s:
        parts = [p.strip() for p in s.split("/") if p.strip()]
        if not parts:
            return None, None

        base = _to_hours(parts[0])
        if base is None:
            return None, None

        night_sum = 0.0
        for p in parts[1:]:
            v = _to_hours(p)
            if isinstance(v, (int, float)):
                night_sum += float(v)

        total = base + night_sum
        return (total if total > 0 else None, night_sum if night_sum > 0 else 0.0)

    total = parse_hours_value(s)
    if total is None:
        return None, None
    return total, 0.0


def calc_row_totals(hours_list: List[Optional[str]], year: int, month: int) -> Dict[str, Any]:
    """
    Итоги по строке табеля:
      - days: сколько дней с ненулевыми часами
      - hours: сумма часов (включая ночные)
      - ot_day / ot_night: переработка из скобок
    """
    dim = month_days(year, month)

    total_hours = 0.0
    total_days = 0
    total_ot_day = 0.0
    total_ot_night = 0.0

    if not hours_list:
        hours_list = [None] * 31
    if len(hours_list) < 31:
        hours_list = (hours_list + [None] * 31)[:31]
    else:
        hours_list = hours_list[:31]

    for i in range(dim):
        raw = hours_list[i]
        if not raw:
            continue

        hrs, _night = parse_hours_and_night(raw)
        d_ot, n_ot = parse_overtime(raw)

        if isinstance(hrs, (int, float)) and hrs > 1e-12:
            total_hours += float(hrs)
            total_days += 1
        if isinstance(d_ot, (int, float)):
            total_ot_day += float(d_ot)
        if isinstance(n_ot, (int, float)):
            total_ot_night += float(n_ot)

    return {
        "days": total_days,
        "hours": float(f"{total_hours:.2f}"),
        "ot_day": float(f"{total_ot_day:.2f}"),
        "ot_night": float(f"{total_ot_night:.2f}"),
    }


def safe_filename(s: str, maxlen: int = 60) -> str:
    s = re.sub(r'[<>:"/\\|?*\n\r\t]+', "_", str(s or "")).strip()
    return re.sub(r"_+", "_", s)[:maxlen]


def _norm_fio(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"[.\t\r\n]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def best_fio_match_with_score(skud_fio: str, candidates: List[str]) -> Tuple[Optional[str], float]:
    nf = _norm_fio(skud_fio)
    if not nf:
        return None, 0.0

    best_name = None
    best_score = 0.0
    for cand in candidates:
        nc = _norm_fio(cand)
        if not nc:
            continue
        score = difflib.SequenceMatcher(None, nf, nc).ratio()
        if score > best_score:
            best_score = score
            best_name = cand

    return best_name, float(best_score)


def round_hours_nearest(duration_minutes: int) -> int:
    """7:29 -> 7, 7:30 -> 8"""
    if duration_minutes <= 0:
        return 0
    return int((duration_minutes + 30) // 60)
