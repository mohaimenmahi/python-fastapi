"""seed roles and permissions

Revision ID: 895ca4909c8a
Revises: cc0553d5ec03
Create Date: 2026-08-12 13:56:48.364180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '895ca4909c8a'
down_revision: Union[str, Sequence[str], None] = 'cc0553d5ec03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

roles_table = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String))
permissions_table = sa.table(
    "permissions", sa.column("id", sa.Integer), sa.column("name", sa.String)
)
role_permissions_table = sa.table(
    "role_permissions", sa.column("role_id", sa.Integer), sa.column("permission_id", sa.Integer)
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(roles_table.insert().values(name="user"))
    conn.execute(roles_table.insert().values(name="admin"))
    conn.execute(permissions_table.insert().values(name="items:write"))
    conn.execute(permissions_table.insert().values(name="items:delete"))

    admin_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.name == "admin")
    ).scalar_one()
    write_id = conn.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.name == "items:write")
    ).scalar_one()
    delete_id = conn.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.name == "items:delete")
    ).scalar_one()

    conn.execute(role_permissions_table.insert().values(role_id=admin_id, permission_id=write_id))
    conn.execute(role_permissions_table.insert().values(role_id=admin_id, permission_id=delete_id))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(role_permissions_table.delete())
    conn.execute(permissions_table.delete())
    conn.execute(roles_table.delete())
