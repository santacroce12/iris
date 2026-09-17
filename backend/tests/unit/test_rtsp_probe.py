import asyncio
import hashlib

import pytest

from app.drivers.errors import AuthenticationFailed, CameraUnreachable
from app.drivers.rtsp import probe
from app.drivers.rtsp.probe import RtspTarget

SDP = (
    "v=0\r\no=- 0 0 IN IP4 0.0.0.0\r\ns=Media Presentation\r\n"
    "m=video 0 RTP/AVP 96\r\na=rtpmap:96 H265/90000\r\n"
    "m=audio 0 RTP/AVP 8\r\na=rtpmap:8 PCMA/8000\r\n"
)


def test_digest_matches_rfc2617_example(monkeypatch):
    monkeypatch.setattr(probe.secrets, "token_hex", lambda _: "0a4f113b")
    challenge = (
        'Digest realm="testrealm@host.com", qop="auth,auth-int", '
        'nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41"'
    )
    header = probe.authorization_header(
        challenge, "GET", "/dir/index.html", "Mufasa", "Circle Of Life"
    )
    assert 'response="6629fae49393a05397450978507c4ef1"' in header
    assert 'opaque="5ccc069c403ebaf9f0171e9517f40e41"' in header


def test_parse_sdp_codecs():
    assert probe.parse_sdp(SDP) == [
        {"type": "video", "codec": "H265"},
        {"type": "audio", "codec": "PCMA"},
    ]


def test_credential_url_escapes_special_characters():
    target = RtspTarget("10.0.0.5", 554, "admin", "p@ss:word")
    assert probe.credential_url(target, "/x") == "rtsp://admin:p%40ss%3Aword@10.0.0.5:554/x"


async def _fake_camera(password: str):
    """Servidor RTSP mínimo que exige Digest como una Hikvision."""
    realm, nonce = "IP Camera", "abc123"

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        while True:
            head = await reader.readuntil(b"\r\n\r\n")
            lines = head.decode().split("\r\n")
            uri = lines[0].split(" ")[1]
            headers = dict(line.split(": ", 1) for line in lines[1:] if ": " in line)
            cseq = headers["CSeq"]
            auth = headers.get("Authorization", "")
            ha1 = hashlib.md5(f"admin:{realm}:{password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"DESCRIBE:{uri}".encode()).hexdigest()
            expected = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            if f'response="{expected}"' in auth:
                writer.write(
                    f"RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\nServer: FakeHik\r\n"
                    f"Content-Length: {len(SDP)}\r\n\r\n{SDP}".encode()
                )
            else:
                writer.write(
                    f"RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\n"
                    f'WWW-Authenticate: Digest realm="{realm}", nonce="{nonce}", stale="FALSE"\r\n'
                    f'WWW-Authenticate: Basic realm="{realm}"\r\n\r\n'.encode()
                )
            await writer.drain()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def test_describe_authenticates_and_reads_sdp():
    server, port = await _fake_camera("secreto")
    async with server:
        result = await probe.describe(
            RtspTarget("127.0.0.1", port, "admin", "secreto"), "/Streaming/Channels/101"
        )
    assert result.status == 200
    assert result.server == "FakeHik"
    assert result.media[0] == {"type": "video", "codec": "H265"}


async def test_describe_wrong_password():
    server, port = await _fake_camera("secreto")
    async with server:
        with pytest.raises(AuthenticationFailed):
            await probe.describe(RtspTarget("127.0.0.1", port, "admin", "otra"), "/x")


async def test_describe_closed_port():
    server, port = await _fake_camera("x")
    server.close()
    await server.wait_closed()
    with pytest.raises(CameraUnreachable):
        await probe.describe(RtspTarget("127.0.0.1", port, "admin", "x", timeout_s=2), "/x")
