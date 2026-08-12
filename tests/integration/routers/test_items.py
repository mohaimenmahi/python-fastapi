async def test_public_list_and_get_do_not_require_auth(client, authenticated_client):
    create_response = await authenticated_client.post(
        "/items", json={"name": "Widget", "description": "A widget"}
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    list_response = await client.get("/items")
    assert list_response.status_code == 200
    assert any(item["id"] == item_id for item in list_response.json())

    get_response = await client.get(f"/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Widget"


async def test_get_missing_item_returns_404(client):
    response = await client.get("/items/999999")

    assert response.status_code == 404


async def test_create_without_auth_returns_401(client):
    response = await client.post("/items", json={"name": "Widget"})

    assert response.status_code == 401


async def test_create_and_update_with_auth(authenticated_client):
    create_response = await authenticated_client.post("/items", json={"name": "Widget"})
    item_id = create_response.json()["id"]

    update_response = await authenticated_client.patch(
        f"/items/{item_id}", json={"name": "Widget v2"}
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Widget v2"
