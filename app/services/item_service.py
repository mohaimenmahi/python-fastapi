class ItemNotFoundError(Exception):
    pass


class ItemService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def list_items(self):
        return await self.repository.list()

    async def get_item(self, item_id: int):
        return await self.repository.get_by_id(item_id)

    async def create_item(self, name: str, description: str | None, owner_id: int):
        return await self.repository.create(name=name, description=description, owner_id=owner_id)

    async def update_item(self, item_id: int, name: str | None, description: str | None):
        item = await self.repository.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError(f"Item {item_id} not found")
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        return await self.repository.update(item, **updates)

    async def delete_item(self, item_id: int) -> None:
        item = await self.repository.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError(f"Item {item_id} not found")
        await self.repository.delete(item)
