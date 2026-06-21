"""Unit testy — error-code registry 1:1 s contracts/error-codes.md (fail-closed)."""

from server.cage.errors import CageError, ERROR_CODES

# Přesná sada kódů z contracts/error-codes.md (mimo ERR_UNKNOWN_TOOL, který patří appce).
EXPECTED_CODES = {
    "ERR_NO_POLICY",
    "ERR_POLICY_APPLY_FAILED",
    "ERR_CAGE_DRIFT",
    "ERR_PROXY_DOWN",
    "ERR_INVM_FW_FAILED",
    "ERR_CAP_DROP_FAILED",
    "ERR_NNP_FAILED",
    "ERR_INGRESS_LEAK",
    "ERR_SECRET_LEAK",
    "ERR_GIT_WRITE_CRED",
    "ERR_LOGIN_PERSIST",
}


def test_registry_matches_contract_exactly():
    assert set(ERROR_CODES.keys()) == EXPECTED_CODES


def test_every_error_carries_machine_code():
    for code, cls in ERROR_CODES.items():
        err = cls("detail")
        assert err.code == code
        assert isinstance(err, CageError)
        assert code in str(err)
