from app.auth.passwords import hash_password, verify_password


def test_roundtrip_and_salting() -> None:
    a, b = hash_password("correct horse"), hash_password("correct horse")
    assert a != b  # random salt
    assert verify_password("correct horse", a)
    assert not verify_password("wrong", a)


def test_malformed_hash_is_just_a_failure() -> None:
    for stored in ("", "plain", "scrypt$x$y", "md5$1$2$3$4$5"):
        assert not verify_password("anything", stored)
