"""Persist area definitions and resolved shared coverage without discarding subscriptions."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "d834b6f82260"
down_revision = "d027a1b2c3d4"
branch_labels = None
depends_on = None


def _hash(row: Mapping[str, Any]) -> str:
    """Freeze v1 legacy canonical identity independently of application releases."""
    values = [
        1,
        row["provider_id"],
        "campground",
        row["campground_id"],
        str(row["start_date"]),
        str(row["end_date"]),
        None,
        [],
    ]
    return hashlib.sha256(
        json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def upgrade() -> None:  # noqa: PLR0915
    """Preflight before mutation, then backfill every legacy row and association."""
    bind = op.get_bind()
    rows = list(
        bind.execute(
            sa.text(
                "SELECT s.id, s.user_id, t.provider_id, t.campground_id, t.start_date, t.end_date, c.name FROM user_scans s JOIN unique_targets t ON t.id=s.target_id LEFT JOIN campgrounds c ON c.id=t.campground_id AND c.provider_id=t.provider_id"
            )
        ).mappings()
    )
    identities = [(str(row["user_id"]), _hash(dict(row))) for row in rows]
    if len(set(identities)) != len(identities):
        raise RuntimeError(
            "Duplicate campground scan definitions; resolve duplicates before upgrading"
        )
    op.add_column(
        "notification_outbox",
        sa.Column(
            "payload_kind",
            sa.String(length=24),
            server_default="campground",
            nullable=False,
        ),
    )
    op.add_column(
        "notification_outbox", sa.Column("scan_revision", sa.Integer(), nullable=True)
    )
    op.add_column(
        "notification_outbox",
        sa.Column("payload_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "providers",
        sa.Column("catalog_revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("unique_targets", sa.Column("attempt_id", sa.UUID(), nullable=True))
    op.add_column(
        "unique_targets", sa.Column("attempt_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "unique_targets", sa.Column("attempt_finished_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "unique_targets",
        sa.Column("attempt_error_category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "user_scans",
        sa.Column(
            "destination_type",
            sa.String(length=24),
            server_default="campground",
            nullable=True,
        ),
    )
    op.add_column("user_scans", sa.Column("provider_id", sa.Integer(), nullable=True))
    op.add_column(
        "user_scans", sa.Column("campground_id", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "user_scans",
        sa.Column("recreation_area_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user_scans",
        sa.Column("destination_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_scans", sa.Column("coverage_mode", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "user_scans", sa.Column("selected_campgrounds", sa.JSON(), nullable=True)
    )
    op.add_column("user_scans", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("user_scans", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column(
        "user_scans", sa.Column("definition_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "user_scans",
        sa.Column(
            "definition_revision", sa.Integer(), server_default="1", nullable=True
        ),
    )
    op.add_column(
        "user_scans",
        sa.Column("coverage_revision", sa.Integer(), server_default="1", nullable=True),
    )
    op.add_column(
        "user_scans",
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=True),
    )
    op.add_column("user_scans", sa.Column("current_round_id", sa.UUID(), nullable=True))
    op.add_column(
        "user_scans", sa.Column("round_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "user_scans", sa.Column("round_deadline_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "user_scans", sa.Column("round_completed_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "user_scans", sa.Column("last_full_checked_at", sa.DateTime(), nullable=True)
    )

    for row in rows:
        bind.execute(
            sa.text(
                "UPDATE user_scans SET provider_id=:provider_id, campground_id=:campground_id, destination_name=:name, start_date=:start_date, end_date=:end_date, selected_campgrounds='[]', definition_hash=:hash WHERE id=:id"
            ),
            {
                **dict(row),
                "name": row["name"] or row["campground_id"],
                "hash": _hash(dict(row)),
            },
        )
    with op.batch_alter_table("user_scans") as batch:
        batch.alter_column("target_id", existing_type=sa.Uuid(), nullable=True)
        batch.alter_column("destination_type", nullable=False)
        batch.alter_column("provider_id", nullable=False)
        batch.alter_column("destination_name", nullable=False)
        batch.alter_column("selected_campgrounds", nullable=False)
        batch.alter_column("start_date", nullable=False)
        batch.alter_column("end_date", nullable=False)
        batch.alter_column("definition_hash", nullable=False)
        batch.alter_column("definition_revision", nullable=False)
        batch.alter_column("coverage_revision", nullable=False)
        batch.alter_column("row_version", nullable=False)
        batch.create_foreign_key(
            "fk_scan_provider", "providers", ["provider_id"], ["id"]
        )
        batch.create_unique_constraint(
            "uq_user_scan_definition", ["user_id", "definition_hash"]
        )
        batch.create_check_constraint("ck_scan_dates", "end_date > start_date")
        batch.create_check_constraint(
            "ck_scan_versions",
            "definition_revision > 0 AND coverage_revision > 0 AND row_version > 0",
        )
        batch.create_check_constraint(
            "ck_scan_destination",
            "(destination_type = 'campground' AND campground_id IS NOT NULL AND target_id IS NOT NULL AND recreation_area_id IS NULL AND coverage_mode IS NULL) OR (destination_type = 'recreation_area' AND recreation_area_id IS NOT NULL AND campground_id IS NULL AND target_id IS NULL AND coverage_mode IN ('all', 'selected'))",
        )
    op.create_table(
        "scan_targets",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column(
            "coverage_revision", sa.Integer(), server_default="1", nullable=False
        ),
        sa.Column("round_id", sa.Uuid(), nullable=True),
        sa.Column(
            "outcome", sa.String(length=16), server_default="pending", nullable=False
        ),
        sa.Column("attempt_id", sa.Uuid(), nullable=True),
        sa.Column("successful_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('pending', 'retrying', 'success', 'failed')",
            name="ck_scan_target_outcome",
        ),
        sa.CheckConstraint("coverage_revision > 0", name="ck_scan_target_revision"),
        sa.ForeignKeyConstraint(["scan_id"], ["user_scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["unique_targets.id"],
        ),
        sa.PrimaryKeyConstraint("scan_id", "target_id"),
    )
    op.create_index(
        "ix_scan_targets_round",
        "scan_targets",
        ["scan_id", "round_id", "outcome"],
        unique=False,
    )
    op.create_index(
        "ix_scan_targets_target", "scan_targets", ["target_id"], unique=False
    )
    bind.execute(
        sa.text(
            "INSERT INTO scan_targets (scan_id, target_id, coverage_revision, outcome) SELECT id, target_id, 1, 'pending' FROM user_scans"
        )
    )


def downgrade() -> None:
    """Refuse loss of area state and preserve campground-only legacy data."""
    bind = op.get_bind()
    if bind.scalar(
        sa.text(
            "SELECT count(*) FROM user_scans WHERE destination_type='recreation_area'"
        )
    ) or bind.scalar(
        sa.text("SELECT count(*) FROM notification_outbox WHERE payload_kind='area'")
    ):
        raise RuntimeError(
            "Area scans or delivery intents remain; restore a backup or remove them before downgrade"
        )
    op.drop_table("scan_targets")
    with op.batch_alter_table("user_scans") as batch:
        batch.drop_constraint("fk_scan_provider", type_="foreignkey")
        batch.drop_constraint("uq_user_scan_definition", type_="unique")
        batch.drop_constraint("ck_scan_dates", type_="check")
        batch.drop_constraint("ck_scan_versions", type_="check")
        batch.drop_constraint("ck_scan_destination", type_="check")
        batch.alter_column("target_id", existing_type=sa.Uuid(), nullable=False)
        batch.drop_column("last_full_checked_at")
        batch.drop_column("round_completed_at")
        batch.drop_column("round_deadline_at")
        batch.drop_column("round_started_at")
        batch.drop_column("current_round_id")
        batch.drop_column("row_version")
        batch.drop_column("coverage_revision")
        batch.drop_column("definition_revision")
        batch.drop_column("definition_hash")
        batch.drop_column("end_date")
        batch.drop_column("start_date")
        batch.drop_column("selected_campgrounds")
        batch.drop_column("coverage_mode")
        batch.drop_column("destination_name")
        batch.drop_column("recreation_area_id")
        batch.drop_column("campground_id")
        batch.drop_column("provider_id")
        batch.drop_column("destination_type")
    op.drop_column("unique_targets", "attempt_id")
    op.drop_column("unique_targets", "attempt_started_at")
    op.drop_column("unique_targets", "attempt_finished_at")
    op.drop_column("unique_targets", "attempt_error_category")
    op.drop_column("notification_outbox", "payload_kind")
    op.drop_column("notification_outbox", "scan_revision")
    op.drop_column("notification_outbox", "payload_version")
    op.drop_column("providers", "catalog_revision")
