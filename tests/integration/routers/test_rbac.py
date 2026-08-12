async def test_delete_without_permission_returns_403(authenticated_client):
    create_response = await authenticated_client.post("/items", json={"name": "Widget"})
    item_id = create_response.json()["id"]

    response = await authenticated_client.delete(f"/items/{item_id}")

    assert response.status_code == 403


async def test_delete_with_admin_permission_succeeds(admin_client):
    create_response = await admin_client.post("/items", json={"name": "Widget"})
    item_id = create_response.json()["id"]

    response = await admin_client.delete(f"/items/{item_id}")

    assert response.status_code == 204
    get_response = await admin_client.get(f"/items/{item_id}")
    assert get_response.status_code == 404
