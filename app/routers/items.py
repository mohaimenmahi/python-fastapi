from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, public, require_permission
from app.core.dependencies import get_item_service
from app.models.user import User
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.item_service import ItemNotFoundError, ItemService

router = APIRouter()


@router.get("", response_model=list[ItemRead])
@public
async def list_items(service: ItemService = Depends(get_item_service)):
    return await service.list_items()


@router.get("/{item_id}", response_model=ItemRead)
@public
async def get_item(item_id: int, service: ItemService = Depends(get_item_service)):
    item = await service.get_item(item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    user: User = Depends(get_current_user),
    service: ItemService = Depends(get_item_service),
):
    return await service.create_item(payload.name, payload.description, owner_id=user.id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    user: User = Depends(get_current_user),
    service: ItemService = Depends(get_item_service),
):
    try:
        return await service.update_item(item_id, payload.name, payload.description)
    except ItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    user: User = Depends(require_permission("items:delete")),
    service: ItemService = Depends(get_item_service),
) -> None:
    try:
        await service.delete_item(item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
