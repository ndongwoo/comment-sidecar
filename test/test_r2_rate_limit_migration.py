#!/usr/bin/env python3

import os
from pathlib import Path

from mysql.connector import connect

ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATION_FILE = ROOT_DIR / "sql" / "migrations" / "004_pseudonymize_rate_limit_ips.sql"
MYSQL_CONNECTION = {
    "host": "127.0.0.1",
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": "root",
    "passwd": "root",
}
TEST_DB = "comment_sidecar_r2_rate_limit_migration_test"


def test_rate_limit_migration_discards_raw_ips_and_adds_unique_hash_key():
    admin = connect(**MYSQL_CONNECTION)
    admin.autocommit = True
    admin_cursor = admin.cursor()
    try:
        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
        admin_cursor.execute(
            f"CREATE DATABASE `{TEST_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        db = connect(**MYSQL_CONNECTION, db=TEST_DB)
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE ip_addresses (
                    `ip` varchar(45) NOT NULL,
                    `creation_date` timestamp(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute("INSERT INTO ip_addresses (ip) VALUES ('203.0.113.42')")
            db.commit()
            migration_sql = MIGRATION_FILE.read_text(encoding="utf-8")
            for statement in [s.strip() for s in migration_sql.split(";") if s.strip()]:
                cursor.execute(statement)
            db.commit()
            cursor.execute("SHOW COLUMNS FROM ip_addresses LIKE 'ip_hash'")
            column = cursor.fetchone()
            assert column is not None
            assert column[1].lower() == "char(64)"
            cursor.execute("SELECT COUNT(*) FROM ip_addresses")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SHOW INDEX FROM ip_addresses WHERE Key_name = 'PRIMARY'")
            primary_rows = cursor.fetchall()
            assert [row[4] for row in primary_rows] == ["ip_hash"]
        finally:
            cursor.close()
            db.close()
    finally:
        admin_cursor.execute(f"DROP DATABASE IF EXISTS `{TEST_DB}`")
        admin_cursor.close()
        admin.close()
