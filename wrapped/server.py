"""The Wrapped web app: a small FastAPI server over wrapped.webapi.

    .venv/bin/python -m wrapped.server --port 8770 [--claude]

Uploads are read into memory with a hard size cap and parsed there; nothing
from a chat is written to disk or logged (the access log shows paths only).
Starlette's multipart parser normally spills files over 1 MB to a temp file,
so uploads are parsed with a subclass that keeps the whole part in memory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.formparsers import MultiPartException, MultiPartParser

from . import captions, webapi

DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
# Room for the multipart envelope and the small form fields around the file.
BODY_CAP = webapi.MAX_BYTES + 64 * 1024


class _InMemoryParser(MultiPartParser):
    spool_max_size = BODY_CAP  # never roll a part over to a temp file


class _TooBig(Exception):
    pass


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _read_capped(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > BODY_CAP:
        raise _TooBig
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > BODY_CAP:
            raise _TooBig
        chunks.append(chunk)
    return b"".join(chunks)


async def _upload(request: Request) -> tuple[bytes, dict[str, list[str]]]:
    """(file bytes, the other form fields), all in memory."""
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise webapi.UploadError("Send the chat as a multipart form upload with a 'file' field.")
    body = await _read_capped(request)

    async def stream():
        yield body

    parser = _InMemoryParser(request.headers, stream(), max_files=1, max_fields=50, max_part_size=BODY_CAP)
    try:
        form = await parser.parse()
    except MultiPartException:
        raise webapi.UploadError("That upload couldn't be read as a form.") from None
    upload = form.get("file")
    if upload is None or isinstance(upload, str):
        raise webapi.UploadError("Pick a chat export file first.")
    data = await upload.read()
    await upload.close()
    fields: dict[str, list[str]] = {}
    for key, value in form.multi_items():
        if isinstance(value, str):
            fields.setdefault(key, []).append(value)
    return data, fields


def _optin(fields: dict[str, list[str]]) -> list[str]:
    names = []
    for raw in fields.get("optin", []):
        names.extend(n.strip() for n in raw.split(",") if n.strip())
    return names


def create_app(client=None, dist: Path = DIST) -> FastAPI:
    app = FastAPI(title="Group Chat Wrapped", docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(RequestValidationError)
    async def _invalid(request, exc):  # FastAPI's default echoes the input back
        return _error(422, "That request was missing something.")

    @app.exception_handler(_TooBig)
    async def _too_big(request, exc):
        return _error(413, f"That file is over {webapi.MAX_BYTES // (1024 * 1024)} MB. Export without media and try again.")

    @app.exception_handler(webapi.UploadError)
    async def _bad_upload(request, exc):
        return _error(400, str(exc))

    @app.get("/api/health")
    async def health():
        return {"ok": True, "captions": "claude" if client is not None else "template"}

    @app.get("/api/demo")
    async def demo():
        return webapi.demo_payload(client)

    @app.post("/api/members")
    async def members(request: Request):
        data, fields = await _upload(request)
        messages, fmt = webapi.parse_upload(data, (fields.get("format") or ["auto"])[0])
        return webapi.members_payload(messages, fmt)

    @app.post("/api/wrapped")
    async def wrapped(request: Request):
        data, fields = await _upload(request)
        messages, fmt = webapi.parse_upload(data, (fields.get("format") or ["auto"])[0])
        name = ((fields.get("name") or [""])[0].strip() or "Your group chat")[:80]
        return webapi.wrapped_payload(messages, _optin(fields), name, client) | {"format": fmt}

    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    p = argparse.ArgumentParser(prog="wrapped.server", description="Serve the Group Chat Wrapped web app.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--claude", action="store_true", help="write captions with Claude (needs the Keychain key)")
    args = p.parse_args(argv)
    client = None
    if args.claude:
        client = captions.make_client()
        print("captions: Claude" if client else "captions: templates (no anthropic SDK or no Keychain key)", file=sys.stderr)
    if not DIST.is_dir():
        print(f"note: {DIST} not built; run `npm run build` in web/. The API still works.", file=sys.stderr)
    uvicorn.run(create_app(client), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
