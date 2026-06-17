import base64
import io
import os
import random
import string
import time
import uuid

from PIL import Image, ImageDraw, ImageFont

CAPTCHA_LENGTH = 4
CAPTCHA_TTL_SECONDS = 300  # 5 minutes
CAPTCHA_WIDTH = 120
CAPTCHA_HEIGHT = 40
MAX_CAPTCHA_STORE_SIZE = int(os.getenv("MAX_CAPTCHA_STORE_SIZE", "200"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "10"))

_CAPTCHA_STORE: dict[str, tuple[str, float]] = {}  # captcha_id → (code, created_at)
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}


def _clean_expired() -> None:
    now = time.time()
    expired = [cid for cid, (_, ts) in _CAPTCHA_STORE.items() if now - ts > CAPTCHA_TTL_SECONDS]
    for cid in expired:
        del _CAPTCHA_STORE[cid]


def _trim_store_to_capacity() -> None:
    while len(_CAPTCHA_STORE) >= MAX_CAPTCHA_STORE_SIZE:
        oldest = min(_CAPTCHA_STORE.items(), key=lambda item: item[1][1])[0]
        del _CAPTCHA_STORE[oldest]


def _random_code() -> str:
    chars = string.ascii_uppercase + string.digits
    # Remove easily confused characters
    chars = chars.translate(str.maketrans("", "", "0O1IL"))
    return "".join(random.choices(chars, k=CAPTCHA_LENGTH))


def _generate_image(code: str) -> bytes:
    img = Image.new("RGB", (CAPTCHA_WIDTH, CAPTCHA_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw characters
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    for i, char in enumerate(code):
        x = 8 + i * 26 + random.randint(-3, 3)
        y = random.randint(4, 12)
        color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
        draw.text((x, y), char, fill=color, font=font)

    # Draw noise lines
    for _ in range(3):
        x1 = random.randint(0, CAPTCHA_WIDTH)
        y1 = random.randint(0, CAPTCHA_HEIGHT)
        x2 = random.randint(0, CAPTCHA_WIDTH)
        y2 = random.randint(0, CAPTCHA_HEIGHT)
        draw.line([(x1, y1), (x2, y2)], fill=(180, 180, 180), width=1)

    # Draw noise dots
    for _ in range(30):
        x = random.randint(0, CAPTCHA_WIDTH - 1)
        y = random.randint(0, CAPTCHA_HEIGHT - 1)
        draw.point((x, y), fill=(200, 200, 200))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_captcha() -> dict:
    _clean_expired()
    _trim_store_to_capacity()
    captcha_id = str(uuid.uuid4())
    code = _random_code()
    _CAPTCHA_STORE[captcha_id] = (code, time.time())
    image_bytes = _generate_image(code)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    return {
        "captcha_id": captcha_id,
        "image_base64": f"data:image/png;base64,{image_b64}",
    }


def verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    _clean_expired()
    entry = _CAPTCHA_STORE.get(captcha_id)
    if entry is None:
        return False
    stored_code, _ = entry
    # Consume the captcha after verification attempt
    del _CAPTCHA_STORE[captcha_id]
    return captcha_code.upper().strip() == stored_code.upper()


def check_login_rate_limit(identifier: str) -> None:
    now = time.time()
    key = identifier.strip().lower() or "anonymous"
    attempts = [ts for ts in _LOGIN_ATTEMPTS.get(key, []) if now - ts <= LOGIN_RATE_LIMIT_WINDOW_SECONDS]
    if len(attempts) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        raise ValueError("Too many login attempts. Please try again later.")
    attempts.append(now)
    _LOGIN_ATTEMPTS[key] = attempts


def clear_login_rate_limit(identifier: str) -> None:
    _LOGIN_ATTEMPTS.pop(identifier.strip().lower() or "anonymous", None)
