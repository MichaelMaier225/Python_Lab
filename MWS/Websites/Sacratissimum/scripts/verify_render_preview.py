"""Local integration check of Render's actual start script. No cloud resources.

Run with the project's venv Python. Requires installed requirements and Bash.
Uses a random throwaway secret, temporary SQLite databases and a local port.
"""
import gzip
from html.parser import HTMLParser
import http.client
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HOST = "sacratissimum-smoke.onrender.com"


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        keys = {"img": ("src",), "script": ("src",), "link": ("href",), "button": ("data-concept",)}
        for key in keys.get(tag, ()):
            url = attrs.get(key, "")
            if url.startswith("/static/"):
                self.urls.add(url)


def request(port, path, *, host=HOST, https=True, gzip_enabled=False):
    headers = {"Host": host}
    if https:
        headers["X-Forwarded-Proto"] = "https"
    if gzip_enabled:
        headers["Accept-Encoding"] = "gzip"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def serve_and_check(environment):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    environment = {**environment, "PORT": str(port)}
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            ["bash", "start.sh"], cwd=ROOT, env=environment,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise AssertionError("Preview start script exited before serving")
                try:
                    status, _, body = request(port, "/")
                    if status == 200:
                        break
                except (OSError, http.client.HTTPException):
                    pass
                if time.monotonic() > deadline:
                    raise AssertionError("Timed out waiting for preview")
                time.sleep(0.15)

            urls = set()
            for path in ("/", "/collection/", "/our-story/", "/collection/demo-most-sacred/", "/collection/demo-walk-in-faith/", "/collection/demo-abide/"):
                status, _, body = request(port, path)
                assert status == 200, f"Page failed: {path}: {status}"
                parser = Assets()
                parser.feed(body.decode())
                urls.update(parser.urls)
            assert len(urls) >= 8, "Expected demo images and site assets"
            for url in sorted(urls):
                status, headers, body = request(port, url, gzip_enabled=True)
                assert status == 200 and body, f"Static asset failed: {url}"
                assert headers.get("X-Content-Type-Options") == "nosniff", url
                if ".css" in url:
                    assert headers.get("Content-Encoding") == "gzip", "WhiteNoise CSS compression missing"
                    assert b"Sacratissimum" in gzip.decompress(body)
            assert request(port, "/", host="untrusted.example.test")[0] == 400
            assert request(port, "/", https=False)[0] == 301
            assert request(port, "/not-a-real-page/")[0] == 404
            admin_status, _, admin_body = request(port, "/admin/login/")
            assert admin_status == 200 and b"otp_token" in admin_body, "Production admin must request OTP"
            assert request(port, "/account/register/")[0] == 503, "Disposable preview must not collect customer accounts"
            assert request(port, "/bag/")[0] == 503

            with sqlite3.connect(environment["SACRATISSIMUM_DB_PATH"]) as database:
                assert database.execute("SELECT count(*) FROM store_product").fetchone()[0] == 3
                assert database.execute("SELECT count(*) FROM store_productvariant").fetchone()[0] == 15
                assert database.execute("SELECT count(*) FROM auth_user").fetchone()[0] == 0
            print(f"PASS: Gunicorn pages, {len(urls)} static assets, HTTPS/host checks, 3 demo products, 15 variants, no accounts")
        except Exception:
            log.seek(0)
            print(log.read(), file=sys.stderr)
            raise
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=15)


def main():
    with tempfile.TemporaryDirectory(prefix="sacratissimum-render-") as directory:
        environment = {
            **os.environ,
            "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "RENDER": "true", "RENDER_EXTERNAL_HOSTNAME": HOST,
            "DJANGO_DEBUG": "false", "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DJANGO_ALLOWED_HOSTS": "", "DJANGO_CSRF_TRUSTED_ORIGINS": "",
            "SACRATISSIMUM_PREVIEW": "true",
            "SACRATISSIMUM_DB_PATH": str(Path(directory) / "preview.sqlite3"),
        }
        subprocess.run(["bash", "build.sh"], cwd=ROOT, env=environment, check=True)
        subprocess.run([sys.executable, "manage.py", "check", "--deploy"], cwd=ROOT, env=environment, check=True)
        serve_and_check(environment)
        serve_and_check(environment)  # Same database: must not duplicate demo records.
        Path(environment["SACRATISSIMUM_DB_PATH"]).unlink()
        serve_and_check(environment)  # Lost free-instance storage: rebuild from scratch.
        print("PASS: repeat startup and fresh-database recovery")


if __name__ == "__main__":
    main()
