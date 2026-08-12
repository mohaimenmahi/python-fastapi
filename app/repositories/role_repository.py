from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role
from app.models.user import User


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_role_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_permission_by_name(self, name: str) -> Permission | None:
        result = await self.session.execute(select(Permission).where(Permission.name == name))
        return result.scalar_one_or_none()

    async def assign_role(self, user: User, role: Role) -> None:
        await self.session.refresh(user, attribute_names=["roles"])
        user.roles.append(role)
        await self.session.commit()

    async def get_user_with_roles(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()
