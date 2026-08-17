"""Seed system school and super admin user.

Revision ID: 0004
Revises: 0003
"""
import uuid
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    system_school_id = str(uuid.uuid4())
    admin_user_id = str(uuid.uuid4())

    op.execute(f"""
        INSERT INTO schools (id, name, code, county, level, settings, created_at, updated_at)
        VALUES (
            '{system_school_id}',
            'System Administration',
            'SYSADM',
            'Nairobi',
            'system',
            '{{}}',
            NOW(),
            NOW()
        )
        ON CONFLICT (code) DO NOTHING
    """)

    op.execute(f"""
        INSERT INTO users (id, school_id, email, full_name, role, password_hash, is_active, created_at, updated_at)
        VALUES (
            '{admin_user_id}',
            '{system_school_id}',
            'njungegideon73@gmail.com',
            'System Administrator',
            'super_admin',
            '$argon2id$v=19$m=65536,t=3,p=4$lNJaa42xljLGmFMKobRWig$QbHU2Cj3bxky+nUF1nqpava7mWu50oDwhml3O/ppnHM',
            true,
            NOW(),
            NOW()
        )
        ON CONFLICT (email) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email = 'njungegideon73@gmail.com'")
    op.execute("DELETE FROM schools WHERE code = 'SYSADM'")
