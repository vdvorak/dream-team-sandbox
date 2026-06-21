async def test_create_and_list(client):
    r = await client.post("/examples", json={"label": "hello"})
    assert r.status_code == 201
    assert r.json()["label"] == "hello"

    r = await client.get("/examples")
    assert r.status_code == 200
    labels = [e["label"] for e in r.json()["items"]]
    assert "hello" in labels


async def test_validation_rejects_blank_label(client):
    # pydantic min_length=1 → FastAPI request validation → 422
    r = await client.post("/examples", json={"label": ""})
    assert r.status_code == 422


async def test_validate_only_is_dry_run(client):
    # ?validate=true → validation only, does NOT persist
    r = await client.post("/examples?validate=true", json={"label": "dryrun"})
    assert r.status_code == 200
    assert r.json() == {"valid": True, "field_errors": {}}

    # nothing was persisted
    r = await client.get("/examples")
    assert "dryrun" not in [e["label"] for e in r.json()["items"]]


async def test_duplicate_label_revalidated_on_commit(client):
    assert (await client.post("/examples", json={"label": "dup"})).status_code == 201

    # commit re-validates server-side → 422 {code, details.field_errors}
    r = await client.post("/examples", json={"label": "dup"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_failed"
    assert body["details"]["field_errors"]["label"] == "duplicate"

    # validate-only on a duplicate → valid:false (UX hint)
    r = await client.post("/examples?validate=true", json={"label": "dup"})
    assert r.json() == {"valid": False, "field_errors": {"label": "duplicate"}}
