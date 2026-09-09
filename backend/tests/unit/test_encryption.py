from app.security.encryption import FieldEncryptor, generate_key, random_subject_token


def test_encrypt_decrypt_roundtrip():
    enc = FieldEncryptor("test-key-32-bytes-long-xxxxxxxxxx")
    payload = {"q1": 3, "q2": "sometimes", "nested": [1, 2, 3]}
    token = enc.encrypt(payload)
    assert token != str(payload)
    assert enc.decrypt(token) == payload


def test_encrypt_raw_roundtrip():
    enc = FieldEncryptor("test-key-32-bytes-long-xxxxxxxxxx")
    assert enc.decrypt_raw(enc.encrypt_raw("hello")) == "hello"


def test_wrong_key_cannot_decrypt():
    a = FieldEncryptor("test-key-32-bytes-long-xxxxxxxxxx")
    b = FieldEncryptor("another-key-32-bytes-long-yyyyyyyy")
    token = a.encrypt({"x": 1})
    try:
        b.decrypt(token)
        assert False, "decryption with wrong key should fail"
    except ValueError:
        pass


def test_subject_token_unique():
    assert random_subject_token() != random_subject_token()


def test_generate_key_format():
    key = generate_key()
    assert isinstance(key, str) and len(key) > 0
