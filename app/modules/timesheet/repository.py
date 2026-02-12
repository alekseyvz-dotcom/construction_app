import logging
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor, execute_values

from app.core.database import db_manager
from app.modules.timesheet.utils import parse_hours_and_night, parse_overtime

logger = logging.getLogger(__name__)


def find_object_db_id_by_excel_or_address(
    cur,
    excel_id: Optional[str],
    address: str,
) -> Optional[int]:
    if excel_id:
        cur.execute(
            "SELECT id FROM objects WHERE COALESCE(NULLIF(excel_id, ''), '') = %s",
            (excel_id,),
        )
        row = cur.fetchone()
        if row:
            return row[0]

    cur.execute("SELECT id FROM objects WHERE address = %s", (address,))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_timesheet_header(
    object_id: Optional[str],
    object_addr: str,
    department: str,
    year: int,
    month: int,
    user_id: int,
) -> int:
    with db_manager.connection() as conn:
        with conn, conn.cursor() as cur:
            object_db_id = find_object_db_id_by_excel_or_address(cur, object_id or None, object_addr)
            if object_db_id is None:
                raise RuntimeError(
                    f"В БД не найден объект (excel_id={object_id!r}, address={object_addr!r}). "
                    f"Сначала создайте объект в разделе «Объекты»."
                )

            cur.execute(
                """
                INSERT INTO timesheet_headers (object_id, object_addr, department, year, month, user_id, object_db_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (object_id, object_addr, department, year, month, user_id)
                DO UPDATE SET updated_at = now(), object_db_id = EXCLUDED.object_db_id
                RETURNING id;
                """,
                (object_id or None, object_addr, department or None, year, month, user_id, object_db_id),
            )
            header_id = cur.fetchone()[0]
        conn.commit()
    return header_id


def replace_timesheet_rows(header_id: int, rows: List[Dict[str, Any]]):
    with db_manager.connection() as conn:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM timesheet_rows WHERE header_id = %s", (header_id,))
            if not rows:
                conn.commit()
                return

            values = []
            for rec in rows:
                hours_list = rec.get("hours") or [None] * 31
                if len(hours_list) != 31:
                    hours_list = (hours_list + [None] * 31)[:31]

                total_hours = 0.0
                total_night_hours = 0.0
                total_days = 0
                total_ot_day = 0.0
                total_ot_night = 0.0

                for raw in hours_list:
                    if not raw:
                        continue
                    hrs, night = parse_hours_and_night(raw)
                    d_ot, n_ot = parse_overtime(raw)

                    if isinstance(hrs, (int, float)) and hrs > 1e-12:
                        total_hours += float(hrs)
                        total_days += 1
                    if isinstance(night, (int, float)):
                        total_night_hours += float(night)
                    if isinstance(d_ot, (int, float)):
                        total_ot_day += float(d_ot)
                    if isinstance(n_ot, (int, float)):
                        total_ot_night += float(n_ot)

                values.append(
                    (
                        header_id,
                        rec.get("fio") or "",
                        (rec.get("tbn") or "").strip() or None,
                        hours_list,
                        total_days or None,
                        total_hours or None,
                        total_night_hours or None,
                        total_ot_day or None,
                        total_ot_night or None,
                    )
                )

            execute_values(
                cur,
                """
                INSERT INTO timesheet_rows
                    (header_id, fio, tbn, hours_raw,
                     total_days, total_hours, night_hours, overtime_day, overtime_night)
                VALUES %s
                """,
                values,
            )
        conn.commit()


def load_timesheet_rows_from_db(
    object_id: Optional[str],
    object_addr: str,
    department: str,
    year: int,
    month: int,
    user_id: int,
) -> List[Dict[str, Any]]:
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT h.id
                FROM timesheet_headers h
                WHERE COALESCE(h.object_id, '') = COALESCE(%s, '')
                  AND h.object_addr = %s
                  AND COALESCE(h.department, '') = COALESCE(%s, '')
                  AND h.year = %s
                  AND h.month = %s
                  AND h.user_id = %s
                """,
                (object_id or None, object_addr, department or None, year, month, user_id),
            )
            row = cur.fetchone()
            if not row:
                return []
            header_id = row[0]

            cur.execute(
                """
                SELECT fio, tbn, hours_raw
                FROM timesheet_rows
                WHERE header_id = %s
                ORDER BY fio, tbn
                """,
                (header_id,),
            )

            result: List[Dict[str, Any]] = []
            for fio, tbn, hours_raw in cur.fetchall():
                hrs = list(hours_raw) if hours_raw is not None else [None] * 31
                hrs = (hrs + [None] * 31)[:31]
                result.append(
                    {"fio": fio or "", "tbn": tbn or "", "hours": [h for h in hrs]}
                )
            return result


def load_timesheet_rows_by_header_id(header_id: int) -> List[Dict[str, Any]]:
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT fio, tbn, hours_raw, total_days, total_hours, night_hours, overtime_day, overtime_night
                FROM timesheet_rows
                WHERE header_id = %s
                ORDER BY fio, tbn
                """,
                (header_id,),
            )

            result: List[Dict[str, Any]] = []
            for fio, tbn, hours_raw, total_days, total_hours, night_hours, ot_day, ot_night in cur.fetchall():
                hrs = list(hours_raw) if hours_raw else [None] * 31
                hrs = (hrs + [None] * 31)[:31]
                result.append(
                    {
                        "fio": fio or "",
                        "tbn": tbn or "",
                        "hours_raw": [h for h in hrs],
                        "total_days": total_days,
                        "total_hours": float(total_hours) if total_hours is not None else None,
                        "night_hours": float(night_hours) if night_hours is not None else None,
                        "overtime_day": float(ot_day) if ot_day is not None else None,
                        "overtime_night": float(ot_night) if ot_night is not None else None,
                    }
                )
            return result


def load_user_timesheet_headers(
    user_id: int,
    year: Optional[int],
    month: Optional[int],
    department: Optional[str],
    object_addr_substr: Optional[str],
) -> List[Dict[str, Any]]:
    where = ["user_id = %s"]
    params: List[Any] = [user_id]

    if year is not None:
        where.append("year = %s")
        params.append(year)
    if month is not None:
        where.append("month = %s")
        params.append(month)
    if department:
        where.append("COALESCE(department, '') = %s")
        params.append(department)
    if object_addr_substr:
        where.append("object_addr ILIKE %s")
        params.append(f"%{object_addr_substr}%")

    where_sql = " AND ".join(where)

    with db_manager.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, object_id, object_addr, department, year, month, created_at, updated_at
                FROM timesheet_headers
                WHERE {where_sql}
                ORDER BY year DESC, month DESC, object_addr, COALESCE(department, '')
                """,
                params,
            )
            return [dict(r) for r in cur.fetchall()]


def load_all_timesheet_headers(
    year: Optional[int],
    month: Optional[int],
    department: Optional[str],
    object_addr_substr: Optional[str],
    object_id_substr: Optional[str],
) -> List[Dict[str, Any]]:
    where = ["1=1"]
    params: List[Any] = []

    if year is not None:
        where.append("h.year = %s")
        params.append(year)
    if month is not None:
        where.append("h.month = %s")
        params.append(month)
    if department:
        where.append("COALESCE(h.department, '') = %s")
        params.append(department)
    if object_addr_substr:
        where.append("h.object_addr ILIKE %s")
        params.append(f"%{object_addr_substr}%")
    if object_id_substr:
        where.append("COALESCE(h.object_id, '') ILIKE %s")
        params.append(f"%{object_id_substr}%")

    where_sql = " AND ".join(where)

    with db_manager.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT h.id, h.object_id, h.object_addr, h.department, h.year, h.month, h.user_id,
                       u.username, u.full_name, h.created_at, h.updated_at
                FROM timesheet_headers h
                JOIN app_users u ON u.id = h.user_id
                WHERE {where_sql}
                ORDER BY h.year DESC, h.month DESC, h.object_addr, COALESCE(h.department, ''), u.full_name
                """,
                params,
            )
            return [dict(r) for r in cur.fetchall()]


def load_employees_from_db() -> List[Tuple[str, str, str, str]]:
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.fio, e.tbn, e.position, d.name AS dep
                FROM employees e
                LEFT JOIN departments d ON d.id = e.department_id
                WHERE COALESCE(e.is_fired, FALSE) = FALSE
                ORDER BY e.fio
                """
            )
            return [(r[0] or "", r[1] or "", r[2] or "", r[3] or "") for r in cur.fetchall()]


def load_objects_short_for_timesheet() -> List[Tuple[str, str, str]]:
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(NULLIF(excel_id, ''), '') AS code,
                    address,
                    COALESCE(short_name, '') AS short_name
                FROM objects
                ORDER BY address, code
                """
            )
            return [(r[0] or "", r[1] or "", r[2] or "") for r in cur.fetchall()]


def find_duplicate_employees_for_timesheet(
    object_id: Optional[str],
    object_addr: str,
    department: str,
    year: int,
    month: int,
    user_id: int,
    employees: List[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    if not employees:
        return []

    fio_tbn_pairs = [
        (fio.strip(), (tbn or "").strip())
        for fio, tbn in employees
        if (fio or "").strip() or (tbn or "").strip()
    ]
    if not fio_tbn_pairs:
        return []

    with_tbn = [(fio, tbn) for fio, tbn in fio_tbn_pairs if tbn]
    without_tbn = [fio for fio, tbn in fio_tbn_pairs if not tbn]

    base_where = """
        COALESCE(h.object_id, '') = COALESCE(%s, '')
        AND h.object_addr = %s
        AND COALESCE(h.department, '') = COALESCE(%s, '')
        AND h.year = %s
        AND h.month = %s
        AND h.user_id <> %s
    """
    base_params = [object_id or None, object_addr, department or None, year, month, user_id]

    results: List[Dict[str, Any]] = []

    with db_manager.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if with_tbn:
                cur.execute(
                    f"""
                    SELECT h.id AS header_id,
                           h.user_id,
                           u.username,
                           u.full_name,
                           r.fio,
                           r.tbn
                    FROM timesheet_headers h
                    JOIN app_users u      ON u.id = h.user_id
                    JOIN timesheet_rows r ON r.header_id = h.id
                    WHERE {base_where}
                      AND (r.fio, COALESCE(r.tbn, '')) IN %s
                    """,
                    base_params + [tuple(with_tbn)],
                )
                results.extend(cur.fetchall())

            if without_tbn:
                cur.execute(
                    f"""
                    SELECT h.id AS header_id,
                           h.user_id,
                           u.username,
                           u.full_name,
                           r.fio,
                           r.tbn
                    FROM timesheet_headers h
                    JOIN app_users u      ON u.id = h.user_id
                    JOIN timesheet_rows r ON r.header_id = h.id
                    WHERE {base_where}
                      AND r.fio = ANY(%s)
                    """,
                    base_params + [without_tbn],
                )
                results.extend(cur.fetchall())

    return [dict(r) for r in results]
