from app.models.role import Role
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


async def test_assign_role_and_get_user_with_roles(db_session):
    db_session.add(Role(name="user"))
    await db_session.commit()

    users = UserRepository(db_session)
    roles = RoleRepository(db_session)

    user = await users.create(email="b@example.com", hashed_password="hashed")
    role = await roles.get_role_by_name("user")
    await roles.assign_role(user, role)

    fetched = await roles.get_user_with_roles(user.id)

    assert fetched is not None
    assert [r.name for r in fetched.roles] == ["user"]
