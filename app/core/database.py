"""
Управление пулом соединений с PostgreSQL.
"""
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Синглтон-менеджер пула соединений с БД.
    
    Использование:
        db = DatabaseManager()
        db.initialize(database_url, sslmode)
        
        conn = db.get_connection()
        try:
            ...
        finally:
            db.put_connection(conn)
        
        # Или через контекстный менеджер:
        with db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """

    _instance: Optional["DatabaseManager"] = None
    _pool: Optional[pool.SimpleConnectionPool] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_initialized(self) -> bool:
        return self._pool is not None

    def initialize(
        self,
        database_url: str,
        sslmode: str = "require",
        min_conn: int = 1,
        max_conn: int = 10,
    ) -> None:
        """Создаёт пул соединений из DATABASE_URL."""
        if self._pool is not None:
            logger.warning("Пул соединений уже инициализирован, пропускаем.")
            return

        url = urlparse(database_url.strip())
        
        # sslmode из query string имеет приоритет
        qs_sslmode = parse_qs(url.query).get("sslmode", [None])[0]
        effective_sslmode = qs_sslmode or sslmode

        self._pool = pool.SimpleConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            host=url.hostname or "localhost",
            port=url.port or 5432,
            dbname=url.path.lstrip("/"),
            user=url.username,
            password=url.password,
            sslmode=effective_sslmode,
        )
        logger.info(
            "Пул соединений с БД создан: host=%s, db=%s, pool=[%d..%d]",
            url.hostname, url.path.lstrip("/"), min_conn, max_conn,
        )

    def get_connection(self):
        """Получить соединение из пула."""
        if not self._pool:
            raise RuntimeError("Пул соединений не инициализирован. Вызовите initialize().")
        return self._pool.getconn()

    def put_connection(self, conn) -> None:
        """Вернуть соединение в пул."""
        if self._pool and conn:
            self._pool.putconn(conn)

    def connection(self):
        """Контекстный менеджер для соединения."""
        return _ConnectionContext(self)

    def close(self) -> None:
        """Закрыть все соединения в пуле."""
        if self._pool:
            logger.info("Закрытие пула соединений с БД...")
            self._pool.closeall()
            self._pool = None
            logger.info("Пул соединений закрыт.")

    def execute_query(self, query: str, params=None, fetch: bool = True):
        """
        Утилита: выполнить запрос и вернуть результат.
        Для SELECT — возвращает список dict.
        Для INSERT/UPDATE/DELETE — выполняет commit.
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return [dict(row) for row in cur.fetchall()]
                else:
                    conn.commit()
                    return cur.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            self.put_connection(conn)


class _ConnectionContext:
    """Контекстный менеджер для автоматического возврата соединения."""

    def __init__(self, db: DatabaseManager):
        self._db = db
        self._conn = None

    def __enter__(self):
        self._conn = self._db.get_connection()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self._conn:
            self._conn.rollback()
        self._db.put_connection(self._conn)
        self._conn = None
        return False


# Глобальный экземпляр для удобства
db_manager = DatabaseManager()
