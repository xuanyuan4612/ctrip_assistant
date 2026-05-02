"""Initial migration: create travel booking tables.

Revision ID: 001_init_travel_tables
Revises: None
Create Date: 2026-04-28 12:00:00.000000

This migration creates all tables required for the travel booking assistant,
using explicit raw SQL for maximum control and readability.

Tables created
--------------
* ``t_flight`` - Flight schedules and status
* ``t_ticket`` - Ticket / booking records
* ``t_ticket_flight`` - Junction: which tickets cover which flights
* ``t_hotel`` - Hotel reservations
* ``t_car_rental`` - Car rental bookings
* ``t_trip_recommendation`` - AI-generated trip recommendations
* ``t_boarding_pass`` - Boarding pass details
* ``t_city`` - City reference data (multi-language, IATA codes)
* ``t_usermodel`` - ALTER … ADD COLUMN ``passenger_id``
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_init_travel_tables"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHARSET = "DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
_ENGINE = "ENGINE=InnoDB"


def _create(table_name: str, columns: list[str], indexes: list[str] | None = None) -> str:
    """Build a ``CREATE TABLE`` statement string."""
    parts = [
        f"CREATE TABLE {table_name} (",
        ",\n".join("    " + c for c in columns),
    ]
    if indexes:
        parts[-1] += ","
        parts.append(",\n".join("    " + ix for ix in indexes))
    parts.append(f") {_ENGINE} {_CHARSET};")
    return "\n".join(parts)


def _drop(table_name: str) -> str:
    return f"DROP TABLE IF EXISTS {table_name};"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ---- t_flight ----------------------------------------------------------
    op.execute(_create("t_flight", [
        "flight_id          INTEGER       NOT NULL AUTO_INCREMENT",
        "flight_no          VARCHAR(20)   NOT NULL",
        "departure_airport  VARCHAR(100)  NOT NULL",
        "arrival_airport    VARCHAR(100)  NOT NULL",
        "scheduled_departure DATETIME      NOT NULL",
        "scheduled_arrival  DATETIME      NOT NULL",
        "actual_departure   DATETIME      NULL",
        "actual_arrival     DATETIME      NULL",
        "status             VARCHAR(20)   NOT NULL DEFAULT 'scheduled'",
        "create_time        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (flight_id)",
    ], indexes=[
        "INDEX idx_flight_departure (departure_airport)",
        "INDEX idx_flight_arrival   (arrival_airport)",
    ]))

    # ---- t_ticket ----------------------------------------------------------
    op.execute(_create("t_ticket", [
        "ticket_no       VARCHAR(20)   NOT NULL",
        "book_ref        VARCHAR(20)   NOT NULL",
        "passenger_id    VARCHAR(50)   NULL",
        "passenger_name  VARCHAR(100)  NOT NULL",
        "create_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (ticket_no)",
    ], indexes=[
        "INDEX idx_ticket_passenger (passenger_id)",
    ]))

    # ---- t_ticket_flight (junction) ----------------------------------------
    op.execute(_create("t_ticket_flight", [
        "ticket_no      VARCHAR(20)    NOT NULL",
        "flight_id      INTEGER        NOT NULL",
        "fare_conditions VARCHAR(20)   NOT NULL DEFAULT 'ECONOMY'",
        "amount         DECIMAL(10, 2) NOT NULL DEFAULT 0.00",
        "create_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (ticket_no, flight_id)",
        "CONSTRAINT fk_ticket_flight__ticket  FOREIGN KEY (ticket_no) REFERENCES t_ticket(ticket_no) ON DELETE CASCADE",
        "CONSTRAINT fk_ticket_flight__flight  FOREIGN KEY (flight_id) REFERENCES t_flight(flight_id) ON DELETE CASCADE",
    ], indexes=[
        "INDEX idx_ticket_flight__ticket  (ticket_no)",
        "INDEX idx_ticket_flight__flight  (flight_id)",
    ]))

    # ---- t_hotel -----------------------------------------------------------
    op.execute(_create("t_hotel", [
        "id             INTEGER        NOT NULL AUTO_INCREMENT",
        "name           VARCHAR(200)   NOT NULL",
        "location       VARCHAR(200)   NOT NULL",
        "price_tier     VARCHAR(20)    NOT NULL DEFAULT 'MID'",
        "checkin_date   DATE           NULL",
        "checkout_date  DATE           NULL",
        "booked         TINYINT(1)     NOT NULL DEFAULT 0",
        "create_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (id)",
    ], indexes=[
        "INDEX idx_hotel_location (location)",
    ]))

    # ---- t_car_rental ------------------------------------------------------
    op.execute(_create("t_car_rental", [
        "id             INTEGER        NOT NULL AUTO_INCREMENT",
        "name           VARCHAR(200)   NOT NULL",
        "location       VARCHAR(200)   NOT NULL",
        "price_tier     VARCHAR(20)    NOT NULL DEFAULT 'MID'",
        "start_date     DATE           NULL",
        "end_date       DATE           NULL",
        "booked         TINYINT(1)     NOT NULL DEFAULT 0",
        "create_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (id)",
    ], indexes=[
        "INDEX idx_car_rental_location (location)",
    ]))

    # ---- t_trip_recommendation ---------------------------------------------
    op.execute(_create("t_trip_recommendation", [
        "id             INTEGER        NOT NULL AUTO_INCREMENT",
        "name           VARCHAR(200)   NOT NULL",
        "location       VARCHAR(200)   NOT NULL",
        "keywords       TEXT           NULL",
        "details        TEXT           NULL",
        "booked         TINYINT(1)     NOT NULL DEFAULT 0",
        "thread_id      VARCHAR(50)    NULL",
        "create_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (id)",
    ], indexes=[
        "INDEX idx_recommendation_location  (location)",
        "INDEX idx_recommendation_thread    (thread_id)",
    ]))

    # ---- t_boarding_pass ---------------------------------------------------
    op.execute(_create("t_boarding_pass", [
        "id              INTEGER       NOT NULL AUTO_INCREMENT",
        "ticket_no       VARCHAR(20)   NOT NULL",
        "flight_id       INTEGER       NOT NULL",
        "boarding_no     VARCHAR(20)   NOT NULL",
        "seat_no         VARCHAR(10)   NOT NULL",
        "create_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (id)",
        "CONSTRAINT fk_boarding_pass__ticket FOREIGN KEY (ticket_no) REFERENCES t_ticket(ticket_no) ON DELETE CASCADE",
        "CONSTRAINT fk_boarding_pass__flight FOREIGN KEY (flight_id) REFERENCES t_flight(flight_id) ON DELETE CASCADE",
    ], indexes=[
        "INDEX idx_boarding_pass__ticket (ticket_no)",
        "INDEX idx_boarding_pass__flight (flight_id)",
    ]))

    # ---- t_city ------------------------------------------------------------
    op.execute(_create("t_city", [
        "id              INTEGER        NOT NULL AUTO_INCREMENT",
        "name_zh         VARCHAR(100)   NOT NULL",
        "name_en         VARCHAR(100)   NOT NULL",
        "name_aliases    JSON           NULL",
        "iata_code       VARCHAR(10)    NOT NULL",
        "country         VARCHAR(100)   NOT NULL",
        "timezone        VARCHAR(50)    NOT NULL DEFAULT 'Asia/Shanghai'",
        "is_active       TINYINT(1)     NOT NULL DEFAULT 1",
        "create_time     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "update_time     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "PRIMARY KEY (id)",
    ], indexes=[
        "UNIQUE INDEX idx_city_iata (iata_code)",
    ]))

    # ---- t_usermodel - add passenger_id ------------------------------------
    op.execute(
        "ALTER TABLE t_usermodel "
        "ADD COLUMN passenger_id VARCHAR(50) NULL "
        "COMMENT '\\u5173\\u8054\\u65c5\\u5ba2ID' "
        "AFTER real_name;"
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.execute("ALTER TABLE t_usermodel DROP COLUMN passenger_id;")
    op.execute(_drop("t_boarding_pass"))
    op.execute(_drop("t_trip_recommendation"))
    op.execute(_drop("t_car_rental"))
    op.execute(_drop("t_hotel"))
    op.execute(_drop("t_ticket_flight"))
    op.execute(_drop("t_ticket"))
    op.execute(_drop("t_flight"))
    op.execute(_drop("t_city"))