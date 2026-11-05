"""Every endpoint requires a (mock ID Austria) login – except the three intentionally public ones.

Static scanners (e.g. Floorplan's health check) don't recognise our `require()` / `get_context` dependency as a login
check; this test proves the behaviour by calling every OpenAPI operation without credentials.
"""

import re

PUBLIC = {("get", "/api/health"), ("get", "/api/identity/personas"), ("post", "/api/identity/login")}


def test_all_endpoints_reject_anonymous_calls(client):
    spec = client.app.openapi()
    checked, leaks = 0, []
    for path, ops in spec["paths"].items():
        url = re.sub(r"\{[^}]+\}", "x", path)
        for method in ops:
            if (method, path) in PUBLIC:
                continue
            r = client.request(method.upper(), url, json={} if method in ("post", "put", "patch") else None)
            checked += 1
            if r.status_code != 401:
                leaks.append(f"{method.upper()} {path} -> {r.status_code}")
    assert checked > 60 and not leaks, leaks
