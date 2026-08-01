"""Initial Linda Protocol schema.

Revision ID: 001_initial
Revises: 
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.String(), primary_key=True), sa.Column("email", sa.String(), nullable=False, unique=True), sa.Column("display_name", sa.String(), nullable=False), sa.Column("role", sa.String(), nullable=False), sa.Column("org", sa.String(), nullable=False), sa.Column("password_hash", sa.String(), nullable=False), sa.Column("signing_key", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("source_snapshots", sa.Column("id", sa.String(), primary_key=True), sa.Column("adapter", sa.String(), nullable=False), sa.Column("endpoint_url", sa.String(), nullable=False), sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False), sa.Column("payload", sa.Text(), nullable=False), sa.Column("payload_sha256", sa.String(), nullable=False), sa.Column("schema_ok", sa.Integer(), nullable=False), sa.Column("freshness", sa.String(), nullable=False), sa.Column("meta", sa.Text(), nullable=False))
    op.create_table("decision_cases", sa.Column("id", sa.String(), primary_key=True), sa.Column("title", sa.String(), nullable=False), sa.Column("area", sa.Text(), nullable=False), sa.Column("hazard", sa.String(), nullable=False), sa.Column("state", sa.String(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("assessment", sa.Text(), nullable=False), sa.Column("tasks", sa.Text(), nullable=False), sa.Column("approvals", sa.Text(), nullable=False), sa.Column("evidence_ids", sa.Text(), nullable=False), sa.Column("revocation", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("case_events", sa.Column("id", sa.String(), primary_key=True), sa.Column("case_id", sa.String(), nullable=False), sa.Column("seq", sa.Integer(), nullable=False), sa.Column("at", sa.DateTime(timezone=True), nullable=False), sa.Column("actor", sa.String(), nullable=False), sa.Column("event_type", sa.String(), nullable=False), sa.Column("payload", sa.Text(), nullable=False), sa.Column("previous_hash", sa.String(), nullable=False), sa.Column("this_hash", sa.String(), nullable=False))
    op.create_table("export_artifacts", sa.Column("id", sa.String(), primary_key=True), sa.Column("case_id", sa.String(), nullable=False), sa.Column("kind", sa.String(), nullable=False), sa.Column("filename", sa.String(), nullable=False), sa.Column("sha256", sa.String(), nullable=False), sa.Column("media_type", sa.String(), nullable=False), sa.Column("manifest_sha256", sa.String()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("integration_keys", sa.Column("id", sa.String(), primary_key=True), sa.Column("label", sa.String(), nullable=False), sa.Column("key_hash", sa.String(), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_table("webhook_subscriptions", sa.Column("id", sa.String(), primary_key=True), sa.Column("url", sa.String(), nullable=False), sa.Column("events", sa.Text(), nullable=False), sa.Column("secret", sa.String(), nullable=False), sa.Column("active", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("webhook_deliveries", sa.Column("id", sa.String(), primary_key=True), sa.Column("subscription_id", sa.String(), nullable=False), sa.Column("case_id", sa.String(), nullable=False), sa.Column("event_name", sa.String(), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("status_code", sa.Integer()), sa.Column("state", sa.String(), nullable=False), sa.Column("error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_source_snapshots_adapter", "source_snapshots", ["adapter"], unique=False)
    op.create_index("ix_source_snapshots_payload_sha256", "source_snapshots", ["payload_sha256"], unique=False)
    op.create_index("ix_decision_cases_state", "decision_cases", ["state"], unique=False)
    op.create_index("ix_case_events_case_id", "case_events", ["case_id"], unique=False)
    op.create_index("ix_case_events_event_type", "case_events", ["event_type"], unique=False)
    op.create_index("ix_export_artifacts_case_id", "export_artifacts", ["case_id"], unique=False)
    op.create_index("ix_webhook_deliveries_subscription_id", "webhook_deliveries", ["subscription_id"], unique=False)
    op.create_index("ix_webhook_deliveries_case_id", "webhook_deliveries", ["case_id"], unique=False)


def downgrade():
    for table in ("webhook_deliveries", "webhook_subscriptions", "integration_keys", "export_artifacts", "case_events", "decision_cases", "source_snapshots", "users"):
        op.drop_table(table)
