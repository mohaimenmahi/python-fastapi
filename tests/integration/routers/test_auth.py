async def test_register_then_login_sets_cookies(client):
    register_response = await client.post(
        "/auth/register", json={"email": "e@example.com", "password": "Passw0rd!"}
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "e@example.com"

    login_response = await client.post(
        "/auth/login", json={"email": "e@example.com", "password": "Passw0rd!"}
    )
    assert login_response.status_code == 200
    assert "access_token" in client.cookies
    assert "refresh_token" in client.cookies


async def test_register_duplicate_email_returns_409(client):
    await client.post("/auth/register", json={"email": "dup@example.com", "password": "Passw0rd!"})

    response = await client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "Passw0rd!"}
    )

    assert response.status_code == 409


async def test_login_wrong_password_returns_401(client):
    await client.post("/auth/register", json={"email": "f@example.com", "password": "Passw0rd!"})

    response = await client.post("/auth/login", json={"email": "f@example.com", "password": "wrong"})

    assert response.status_code == 401


async def test_logout_without_cookie_returns_401(client):
    response = await client.post("/auth/logout")

    assert response.status_code == 401


async def test_logout_clears_cookies(authenticated_client):
    old_refresh = authenticated_client.cookies["refresh_token"]

    response = await authenticated_client.post("/auth/logout")

    assert response.status_code == 200
    assert "access_token" not in authenticated_client.cookies
    assert "refresh_token" not in authenticated_client.cookies

    authenticated_client.cookies.set("refresh_token", old_refresh)
    refresh_after_logout = await authenticated_client.post("/auth/refresh")

    assert refresh_after_logout.status_code == 401


async def test_login_cookies_have_security_attributes(client):
    await client.post(
        "/auth/register", json={"email": "cookie-attrs@example.com", "password": "Passw0rd!"}
    )

    response = await client.post(
        "/auth/login", json={"email": "cookie-attrs@example.com", "password": "Passw0rd!"}
    )

    set_cookie_headers = response.headers.get_list("set-cookie")
    assert len(set_cookie_headers) == 2
    for header in set_cookie_headers:
        assert "httponly" in header.lower()
        assert "samesite=lax" in header.lower()
        assert "secure" not in header.lower()


async def test_refresh_rotates_and_reuse_is_rejected(client):
    await client.post("/auth/register", json={"email": "g@example.com", "password": "Passw0rd!"})
    await client.post("/auth/login", json={"email": "g@example.com", "password": "Passw0rd!"})
    old_refresh = client.cookies["refresh_token"]

    first_refresh = await client.post("/auth/refresh")
    assert first_refresh.status_code == 200
    rotated_refresh = client.cookies["refresh_token"]
    assert rotated_refresh != old_refresh

    client.cookies.delete("refresh_token")
    client.cookies.set("refresh_token", old_refresh)
    reuse_response = await client.post("/auth/refresh")

    assert reuse_response.status_code == 401

    client.cookies.delete("refresh_token")
    client.cookies.set("refresh_token", rotated_refresh)
    cascade_response = await client.post("/auth/refresh")

    assert cascade_response.status_code == 401
