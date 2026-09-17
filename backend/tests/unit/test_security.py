from app.core.security import decrypt, encrypt, redact


def test_encrypt_roundtrip_and_not_plaintext():
    token = encrypt("Hik12345!")
    assert "Hik12345" not in token
    assert decrypt(token) == "Hik12345!"


def test_redact_urls_and_xml_passwords():
    text = "rtsp://admin:Hik12345@10.0.0.5:554/x <password>Hik12345</password>"
    cleaned = redact(text)
    assert "Hik12345" not in cleaned
    assert "rtsp://***:***@10.0.0.5:554/x" in cleaned
