from app.repositories.item_repository import ItemRepository
from app.repositories.user_repository import UserRepository


async def test_create_list_update_delete(db_session):
    users = UserRepository(db_session)
    items = ItemRepository(db_session)
    owner = await users.create(email="d@example.com", hashed_password="hashed")

    created = await items.create(name="Widget", description="A widget", owner_id=owner.id)
    assert (await items.list()) == [created]

    updated = await items.update(created, name="Widget v2")
    assert updated.name == "Widget v2"

    await items.delete(updated)
    assert await items.get_by_id(created.id) is None
