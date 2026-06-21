async def test_register_login_cookie_and_me(client):
    r = await client.post("/auth/register", json={"email": "a@b.cz", "password": "secret12"})
    assert r.status_code == 201

    r = await client.post("/auth/login", json={"email": "a@b.cz", "password": "secret12"})
    assert r.status_code == 200
    assert client.cookies.get("session")

    # httpx keeps a cookie jar → /me uses the session cookie automatically
    r = await client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.cz"


async def test_logout_invalidates_session(client):
    await client.post("/auth/register", json={"email": "l@y.cz", "password": "secret12"})
    await client.post("/auth/login", json={"email": "l@y.cz", "password": "secret12"})
    assert (await client.get("/auth/me")).status_code == 200
    await client.post("/auth/logout")
    assert (await client.get("/auth/me")).status_code == 401


async def test_wrong_password_and_unknown_email_are_indistinguishable(client):
    await client.post("/auth/register", json={"email": "x@y.cz", "password": "secret12"})
    r1 = await client.post("/auth/login", json={"email": "x@y.cz", "password": "wrongpass"})
    r2 = await client.post("/auth/login", json={"email": "nobody@y.cz", "password": "whatever1"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json() == {"code": "invalid_credentials"}


async def test_me_without_cookie_is_401(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401
