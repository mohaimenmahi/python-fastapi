from dataclasses import dataclass, field

import pytest

from app.services.item_service import ItemNotFoundError, ItemService


@dataclass
class FakeItem:
    id: int
    name: str
    description: str | None
    owner_id: int


class FakeItemRepository:
    def __init__(self):
        self._items: dict[int, FakeItem] = {}
        self._next_id = 1

    async def list(self) -> list[FakeItem]:
        return list(self._items.values())

    async def get_by_id(self, item_id: int) -> FakeItem | None:
        return self._items.get(item_id)

    async def create(self, **kwargs) -> FakeItem:
        item = FakeItem(id=self._next_id, **kwargs)
        self._items[item.id] = item
        self._next_id += 1
        return item

    async def update(self, instance: FakeItem, **kwargs) -> FakeItem:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        return instance

    async def delete(self, instance: FakeItem) -> None:
        del self._items[instance.id]


async def test_create_and_list():
    service = ItemService(FakeItemRepository())

    created = await service.create_item("Widget", "desc", owner_id=1)

    assert await service.list_items() == [created]


async def test_update_missing_item_raises():
    service = ItemService(FakeItemRepository())

    with pytest.raises(ItemNotFoundError):
        await service.update_item(999, "New name", None)


async def test_delete_missing_item_raises():
    service = ItemService(FakeItemRepository())

    with pytest.raises(ItemNotFoundError):
        await service.delete_item(999)


async def test_update_and_delete_existing_item():
    service = ItemService(FakeItemRepository())
    created = await service.create_item("Widget", "desc", owner_id=1)

    updated = await service.update_item(created.id, "Widget v2", None)
    assert updated.name == "Widget v2"
    assert updated.description == "desc"  # None means "leave unchanged"

    await service.delete_item(created.id)
    assert await service.get_item(created.id) is None
