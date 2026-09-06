"""Schéma initial : users, documents, document_analysis, pii_detections, human_reviews, audit_logs

Revision ID: 0001
Revises:
Create Date: 2026-09-06

Les enums sont stockés en VARCHAR (native_enum=False) pour rester
portables entre PostgreSQL et SQLite (tests).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    """Colonnes created_at / updated_at communes à toutes les tables."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=20), server_default="USER", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ---- documents ----
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="UPLOADED", nullable=False),
        sa.Column("error_reason", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_documents_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_owner_id"), "documents", ["owner_id"], unique=False)

    # ---- document_analysis ----
    op.create_table(
        "document_analysis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("lines", sa.JSON(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("sentiment", sa.String(length=10), nullable=True),
        sa.Column("sentiment_confidence", sa.Float(), nullable=True),
        sa.Column("emotions", sa.JSON(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("analysis_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_analysis_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_analysis")),
    )
    op.create_index(
        op.f("ix_document_analysis_document_id"), "document_analysis", ["document_id"], unique=True
    )

    # ---- pii_detections ----
    op.create_table(
        "pii_detections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("pii_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("start", sa.Integer(), nullable=True),
        sa.Column("end", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["document_analysis.id"],
            name=op.f("fk_pii_detections_analysis_id_document_analysis"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pii_detections")),
    )
    op.create_index(op.f("ix_pii_detections_analysis_id"), "pii_detections", ["analysis_id"], unique=False)

    # ---- human_reviews ----
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("corrected_text", sa.Text(), nullable=True),
        sa.Column("corrected_sentiment", sa.String(length=10), nullable=True),
        sa.Column("corrected_category", sa.String(length=100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name=op.f("fk_human_reviews_document_id_documents"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name=op.f("fk_human_reviews_reviewer_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_human_reviews")),
    )
    op.create_index(op.f("ix_human_reviews_document_id"), "human_reviews", ["document_id"], unique=False)

    # ---- audit_logs ----
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("event", sa.String(length=30), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name=op.f("fk_audit_logs_document_id_documents"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_document_id"), "audit_logs", ["document_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_document_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_human_reviews_document_id"), table_name="human_reviews")
    op.drop_table("human_reviews")

    op.drop_index(op.f("ix_pii_detections_analysis_id"), table_name="pii_detections")
    op.drop_table("pii_detections")

    op.drop_index(op.f("ix_document_analysis_document_id"), table_name="document_analysis")
    op.drop_table("document_analysis")

    op.drop_index(op.f("ix_documents_owner_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")