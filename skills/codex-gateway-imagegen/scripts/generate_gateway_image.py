#!/usr/bin/env python3
"""
Generate an image through the Responses-compatible gateway configured for Codex.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import ssl

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


DEFAULT_MODEL = "gpt-5.4"
DEFAULT_TIMEOUT = 600
DEFAULT_SIZE = "1024x1024"
STREAM_HEADER = "text/event-stream"
QUALITY_AUTO = "auto"


def load_config() -> tuple[str, str]:
    config_path = Path.home() / ".codex" / "config.toml"
    auth_path = Path.home() / ".codex" / "auth.json"

    if not config_path.exists():
        raise RuntimeError(f"Missing config file: {config_path}")
    if not auth_path.exists():
        raise RuntimeError(f"Missing auth file: {auth_path}")

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    base_url = (
        config.get("model_providers", {})
        .get(config.get("model_provider", ""), {})
        .get("base_url")
    )
    if not base_url:
        raise RuntimeError("Could not find model provider base_url in ~/.codex/config.toml")

    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    api_key = auth.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Could not find OPENAI_API_KEY in ~/.codex/auth.json")

    return str(base_url).rstrip("/"), str(api_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an image via the configured Responses gateway.")
    parser.add_argument("--prompt", required=True, help="Image generation prompt.")
    parser.add_argument("--out", required=True, help="Output image path.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Image size, e.g. 1024x1024 or 1024x1536.")
    parser.add_argument(
        "--quality",
        choices=(QUALITY_AUTO, "low", "medium", "high"),
        default=QUALITY_AUTO,
        help="Image quality. auto sets high when prompt asks for 高清/超清/4K/8K.",
    )
    parser.add_argument(
        "--action",
        choices=("auto", "generate", "edit"),
        default="auto",
        help="Image tool action. Use edit when providing a reference image or mask.",
    )
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Reference image path. Repeat the flag to include multiple images.",
    )
    parser.add_argument(
        "--image-url",
        action="append",
        default=[],
        help="Reference image URL. Repeat the flag to include multiple images.",
    )
    parser.add_argument(
        "--mask",
        help="Optional mask image path for edit workflows.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Responses model to call.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--stream",
        choices=("auto", "on", "off"),
        default="auto",
        help="Transport mode. auto tries stream first then falls back to non-stream JSON.",
    )
    return parser.parse_args()


def encode_image_data_url(image_path: str) -> str:
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"Image file does not exist: {path}")

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_payload(args: argparse.Namespace, *, stream: bool = False) -> bytes:
    input_content: list[dict[str, str]] = [
        {
            "type": "input_text",
            "text": args.prompt,
        }
    ]

    for image_path in args.image:
        input_content.append(
            {
                "type": "input_image",
                "image_url": encode_image_data_url(image_path),
            }
        )

    for image_url in args.image_url:
        input_content.append(
            {
                "type": "input_image",
                "image_url": image_url,
            }
        )

    if args.mask:
        input_content.append(
            {
                "type": "input_image_mask",
                "image_url": encode_image_data_url(args.mask),
            }
        )

    tool_payload: dict[str, str] = {
        "type": "image_generation",
        "size": args.size,
        "action": args.action,
    }

    quality = resolve_quality(args.prompt, args.quality)
    if quality:
        tool_payload["quality"] = quality

    payload = {
        "model": args.model,
        "input": [
            {
                "role": "user",
                "content": input_content,
            }
        ],
        "tools": [tool_payload],
    }
    if stream:
        payload["stream"] = True
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def resolve_quality(prompt: str, quality: str) -> str | None:
    if quality != QUALITY_AUTO:
        return quality

    normalized = prompt.strip().lower()
    negative_tokens = (
        "不要高清",
        "不需要高清",
        "非高清",
        "不要超清",
        "不需要超清",
        "非超清",
        "不要4k",
        "不需要4k",
        "不要8k",
        "不需要8k",
    )
    if any(token in normalized for token in negative_tokens):
        return None

    high_tokens = (
        "高清",
        "超清",
        "高分辨率",
        "high quality",
        "high-res",
        "high resolution",
        "ultra hd",
        "uhd",
        "4k",
        "8k",
    )
    if any(token in normalized for token in high_tokens):
        return "high"

    return None


def extract_image_base64(data: dict) -> str:
    for item in data.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"]
    fallback = find_best_base64(data)
    if fallback:
        return fallback
    raise RuntimeError("No image_generation_call result returned")


def normalize_base64(value: str) -> str | None:
    text = value.strip()
    if text.startswith("data:") and "," in text:
        text = text.split(",", 1)[1]
    text = "".join(text.split())
    if len(text) < 64:
        return None
    try:
        base64.b64decode(text, validate=True)
    except Exception:
        return None
    return text


def find_best_base64(payload: object) -> str | None:
    best: str | None = None
    stack: list[object] = [payload]

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if isinstance(value, (dict, list)):
                    stack.append(value)
                elif key in {"result", "partial_image_b64", "image_b64"} and isinstance(value, str):
                    normalized = normalize_base64(value)
                    if normalized and (best is None or len(normalized) > len(best)):
                        best = normalized
        elif isinstance(current, list):
            stack.extend(current)

    return best


def iter_sse_payloads(response) -> object:
    data_lines: list[str] = []
    for raw in response:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        yield "\n".join(data_lines)


def request_non_stream(base_url: str, api_key: str, body: bytes, timeout: int) -> dict:
    request = Request(
        f"{base_url}/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, context=ssl.create_default_context(), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def request_stream_image_base64(base_url: str, api_key: str, body: bytes, timeout: int) -> str:
    request = Request(
        f"{base_url}/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": STREAM_HEADER,
        },
        method="POST",
    )

    best: str | None = None
    with urlopen(request, context=ssl.create_default_context(), timeout=timeout) as response:
        for payload in iter_sse_payloads(response):
            if payload == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "response.failed":
                error_info = event.get("error") or event
                raise RuntimeError(f"Streaming response failed: {json.dumps(error_info, ensure_ascii=False)}")
            candidate = find_best_base64(event)
            if candidate and (best is None or len(candidate) > len(best)):
                best = candidate

    if not best:
        raise RuntimeError("No image payload found in stream events")
    return best


def format_exception(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        if body:
            return f"HTTP {exc.code}: {body}"
        return f"HTTP {exc.code}: {exc.reason}"
    return f"{type(exc).__name__}: {exc}"


def main() -> int:
    args = parse_args()

    try:
        base_url, api_key = load_config()
        mode_used = args.stream
        quality_used = resolve_quality(args.prompt, args.quality) or "default"

        if args.stream == "on":
            body = build_payload(args, stream=True)
            image_base64 = request_stream_image_base64(base_url, api_key, body, args.timeout)
            mode_used = "stream"
        elif args.stream == "off":
            body = build_payload(args, stream=False)
            data = request_non_stream(base_url, api_key, body, args.timeout)
            image_base64 = extract_image_base64(data)
            mode_used = "non_stream"
        else:
            stream_error: Exception | None = None
            try:
                body = build_payload(args, stream=True)
                image_base64 = request_stream_image_base64(base_url, api_key, body, args.timeout)
                mode_used = "stream"
            except Exception as exc:
                stream_error = exc
                try:
                    body = build_payload(args, stream=False)
                    data = request_non_stream(base_url, api_key, body, args.timeout)
                    image_base64 = extract_image_base64(data)
                    mode_used = "non_stream_fallback"
                except Exception as non_stream_exc:
                    raise RuntimeError(
                        "Both stream and non-stream generation failed. "
                        f"stream_error={format_exception(stream_error)}; "
                        f"non_stream_error={format_exception(non_stream_exc)}"
                    ) from non_stream_exc

        output_path = Path(args.out).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(image_base64))
        print(
            json.dumps(
                {
                    "saved": str(output_path),
                    "bytes": output_path.stat().st_size,
                    "mode": mode_used,
                    "quality": quality_used,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "error": "http_error",
                    "status": exc.code,
                    "body": message,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    except URLError as exc:
        print(json.dumps({"error": "network_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except TimeoutError as exc:
        print(json.dumps({"error": "timeout", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"error": "runtime_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
