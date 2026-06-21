async def test_register_login_and_me(client):
    r = await client.post("/auth/register", json={"email": "a@b.cz", "password": "secret12"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@b.cz"
    # password / hash never leaks into the response
    assert "secret12" not in r.text and "password" not in r.text

    r = await client.post("/auth/login", json={"email": "a@b.cz", "password": "secret12"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.cz"


async def test_wrong_password_and_unknown_email_are_indistinguishable(client):
    await client.post("/auth/register", json={"email": "x@y.cz", "password": "secret12"})
    r1 = await client.post("/auth/login", json={"email": "x@y.cz", "password": "wrongpass"})
    r2 = await client.post("/auth/login", json={"email": "nobody@y.cz", "password": "whatever1"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json() == {"code": "invalid_credentials"}


async def test_duplicate_email_rejected_on_commit(client):
    await client.post("/auth/register", json={"email": "dup@y.cz", "password": "secret12"})
    r = await client.post("/auth/register", json={"email": "dup@y.cz", "password": "secret12"})
    assert r.status_code == 422
    assert r.json()["details"]["field_errors"]["email"] == "duplicate"


async def test_me_without_token_is_401(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401
