from revenant.redact import redact


def test_env_secret_and_url_and_email():
    out = redact("API_TOKEN=abc123 curl https://x.example.com/p?k=1 -u me@corp.com")
    assert "abc123" not in out and "x.example.com" not in out and "me@corp.com" not in out
    assert "API_TOKEN=<secret>" in out


def test_bearer_long_token_number_ip_and_names():
    out = redact("curl -H 'Authorization: Bearer abcdefghij1234' 10.1.2.3 acme-client 123456789", names=("acme-client",))
    assert "abcdefghij1234" not in out and "10.1.2.3" not in out and "acme-client" not in out and "123456789" not in out
    assert redact("deploy ghp_a1b2c3d4e5f6g7h8i9j0k1l2m3") == "deploy <token>"


def test_plain_commands_are_unchanged():
    assert redact("git push origin main") == "git push origin main"
    assert redact("ls -la ~/Documents") == "ls -la ~/Documents"
