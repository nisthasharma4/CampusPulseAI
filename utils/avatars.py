"""Avatar management and generation utilities for CampusPulse AI.

Provides:
- Initials-based vector SVG generator
- 6 themed vector SVG presets in Design System V4 palette
- Secure photo upload, PIL thumbnailing (512x512) and storage in data/avatars/
- Base64 data URI HTML rendering for crisp display anywhere in Streamlit
"""

from __future__ import annotations

import base64
from io import BytesIO
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import uuid

from PIL import Image

# Storage directory
AVATARS_DIR = Path("data/avatars")

# Upload constraints
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TARGET_AVATAR_SIZE = (512, 512)

# Palette
COLOR_IRIS = "#5C559A"
COLOR_MIDNIGHT = "#272539"
COLOR_APRICOT = "#E9B67D"
COLOR_TERRACOTTA = "#C87863"
COLOR_SAGE = "#6B8B7F"
COLOR_IVORY = "#FAF9F6"
COLOR_LAVENDER = "#EAE7F2"

# 6 Vector SVG Presets
PRESET_AVATARS: Dict[str, Dict[str, str]] = {
    "classic_student": {
        "title": "Classic Scholar",
        "category": "Academic",
        "description": "Graduation cap & academic focus",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">
  <defs>
    <linearGradient id="cs_grad_{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5C559A" />
      <stop offset="100%" stop-color="#3D366B" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#cs_grad_{uid})" stroke="#E9B67D" stroke-width="2.5" />
  <!-- Graduation Cap -->
  <polygon points="50,26 78,38 50,50 22,38" fill="#FAF9F6" />
  <polygon points="50,28 74,38 50,48 26,38" fill="#EAE7F2" />
  <!-- Cap Skull -->
  <path d="M34,44 L34,55 Q50,65 66,55 L66,44 Q50,52 34,44 Z" fill="#EAE7F2" opacity="0.9" />
  <!-- Tassel -->
  <path d="M72,39 C73,46 76,52 75,58" stroke="#E9B67D" stroke-width="2.5" fill="none" stroke-linecap="round" />
  <circle cx="75" cy="59" r="2.5" fill="#E9B67D" />
  <!-- Shoulders -->
  <path d="M22,86 Q50,68 78,86" fill="none" stroke="#FAF9F6" stroke-width="3" stroke-linecap="round" />
</svg>""",
    },
    "academic_explorer": {
        "title": "Academic Explorer",
        "category": "STEM & Discovery",
        "description": "Compass star & discovery",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">
  <defs>
    <linearGradient id="ae_grad_{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6B8B7F" />
      <stop offset="100%" stop-color="#272539" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#ae_grad_{uid})" stroke="#6B8B7F" stroke-width="2.5" />
  <!-- Outer Compass Ring -->
  <circle cx="50" cy="50" r="32" fill="none" stroke="#FAF9F6" stroke-width="1.8" stroke-dasharray="2,2" opacity="0.6" />
  <!-- Compass Star -->
  <polygon points="50,22 55,45 78,50 55,55 50,78 45,55 22,50 45,45" fill="#E9B67D" />
  <polygon points="50,22 50,50 22,50" fill="#FAF9F6" opacity="0.35" />
  <polygon points="78,50 50,50 50,78" fill="#FAF9F6" opacity="0.35" />
  <circle cx="50" cy="50" r="4.5" fill="#FAF9F6" />
</svg>""",
    },
    "tech_student": {
        "title": "Tech Innovator",
        "category": "Engineering & Code",
        "description": "Code brackets & digital core",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">
  <defs>
    <linearGradient id="ti_grad_{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#272539" />
      <stop offset="100%" stop-color="#1A1826" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#ti_grad_{uid})" stroke="#5C559A" stroke-width="2.5" />
  <!-- Code Brackets -->
  <path d="M36,36 L24,50 L36,64" fill="none" stroke="#E9B67D" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
  <path d="M64,36 L76,50 L64,64" fill="none" stroke="#E9B67D" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Slash -->
  <line x1="56" y1="34" x2="44" y2="66" stroke="#FAF9F6" stroke-width="3" stroke-linecap="round" />
  <!-- Glowing Chip Dot -->
  <circle cx="50" cy="74" r="2.5" fill="#6B8B7F" />
</svg>""",
    },
    "creative_learner": {
        "title": "Creative Mind",
        "category": "Design & Arts",
        "description": "Spark of inspiration & palette",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">
  <defs>
    <linearGradient id="cm_grad_{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#C87863" />
      <stop offset="100%" stop-color="#5C559A" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#cm_grad_{uid})" stroke="#E9B67D" stroke-width="2.5" />
  <!-- Palette / Lightbulb Hybrid -->
  <path d="M50,22 C38,22 30,31 30,42 C30,51 36,55 38,62 L62,62 C64,55 70,51 70,42 C70,31 62,22 50,22 Z" fill="#FAF9F6" opacity="0.95" />
  <!-- Filament Spark -->
  <path d="M44,40 L50,32 L56,40 L50,48 Z" fill="#E9B67D" />
  <!-- Base -->
  <rect x="42" y="65" width="16" height="3" rx="1.5" fill="#272539" />
  <rect x="45" y="70" width="10" height="3" rx="1.5" fill="#272539" />
</svg>""",
    },
    "focused_scholar": {
        "title": "Focused Scholar",
        "category": "Literature & Research",
        "description": "Open book & radiant beacon",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">
  <defs>
    <linearGradient id="fs_grad_{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5C559A" />
      <stop offset="100%" stop-color="#C87863" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#fs_grad_{uid})" stroke="#FAF9F6" stroke-width="2.5" />
  <!-- Open Book Pages -->
  <path d="M50,42 C40,36 28,38 22,42 L22,68 C28,64 40,62 50,68 C60,62 72,64 78,68 L78,42 C72,38 60,36 50,42 Z" fill="#FAF9F6" />
  <line x1="50" y1="42" x2="50" y2="68" stroke="#5C559A" stroke-width="2" />
  <!-- Page Lines -->
  <line x1="28" y1="48" x2="44" y2="46" stroke="#5C559A" stroke-width="1.5" stroke-linecap="round" opacity="0.7" />
  <line x1="28" y1="54" x2="44" y2="52" stroke="#5C559A" stroke-width="1.5" stroke-linecap="round" opacity="0.7" />
  <line x1="56" y1="46" x2="72" y2="48" stroke="#5C559A" stroke-width="1.5" stroke-linecap="round" opacity="0.7" />
  <line x1="56" y1="52" x2="72" y2="54" stroke="#5C559A" stroke-width="1.5" stroke-linecap="round" opacity="0.7" />
  <!-- Quill / Sunburst above -->
  <polygon points="50,22 53,32 50,30 47,32" fill="#E9B67D" />
</svg>""",
    },
    "minimal_portrait": {
        "title": "Minimalist Icon",
        "category": "Modern",
        "description": "Clean modern silhouette",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">
  <defs>
    <linearGradient id="mp_grad_{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#272539" />
      <stop offset="100%" stop-color="#5C559A" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#mp_grad_{uid})" stroke="#E9B67D" stroke-width="2.5" />
  <!-- Head -->
  <circle cx="50" cy="40" r="15" fill="#FAF9F6" />
  <!-- Shoulders -->
  <path d="M26,76 C26,62 36,58 50,58 C64,58 74,62 74,76 Z" fill="#FAF9F6" />
  <!-- Accent collar -->
  <polygon points="50,66 45,58 55,58" fill="#E9B67D" />
</svg>""",
    },
}


def extract_initials(name: Optional[str]) -> str:
    """Extract 1 or 2 uppercase initials from a name."""
    if not name or not str(name).strip():
        return "CP"
    parts = [p.strip() for p in str(name).strip().split() if p.strip()]
    if not parts:
        return "CP"
    if len(parts) == 1:
        clean = parts[0]
        return clean[:2].upper() if len(clean) >= 2 else clean[0].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()


def generate_initials_svg(
    name: Optional[str],
    size: int = 64,
    bg_color: str = COLOR_IRIS,
    text_color: str = COLOR_IVORY,
    border_color: str = COLOR_APRICOT,
) -> str:
    """Generate a clean, high-contrast SVG circular avatar with student initials."""
    initials = extract_initials(name)
    font_size = int(size * 0.42)
    radius = size // 2
    stroke_width = max(2, int(size * 0.035))
    inner_radius = radius - stroke_width

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs>
    <linearGradient id="init_grad_{abs(hash(name or '')) % 10000}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_color}" />
      <stop offset="100%" stop-color="{COLOR_MIDNIGHT}" />
    </linearGradient>
  </defs>
  <circle cx="{radius}" cy="{radius}" r="{inner_radius}" fill="url(#init_grad_{abs(hash(name or '')) % 10000})" stroke="{border_color}" stroke-width="{stroke_width}" />
  <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" fill="{text_color}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif" font-weight="700" font-size="{font_size}px" letter-spacing="0.5px">
    {initials}
  </text>
</svg>"""
    return svg


def render_preset_svg(preset_key: str, size: int = 64) -> str:
    """Return the filled SVG markup for a given preset key."""
    if preset_key not in PRESET_AVATARS:
        preset_key = "classic_student"
    template = PRESET_AVATARS[preset_key]["svg"]
    uid = uuid.uuid4().hex[:6]
    return template.format(size=size, uid=uid)


def svg_to_data_uri(svg_content: str) -> str:
    """Convert an SVG string into a base64 data URI."""
    encoded = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def image_file_to_data_uri(file_path: Union[str, Path]) -> Optional[str]:
    """Convert an on-disk image file to a base64 data URI."""
    path = Path(file_path)
    if not path.is_file():
        return None
    try:
        suffix = path.suffix.lower().replace(".", "")
        mime = f"image/{suffix if suffix != 'jpg' else 'jpeg'}"
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None


def get_avatar_html(
    profile_or_name: Any,
    preset: Optional[str] = None,
    path: Optional[str] = None,
    size: int = 64,
    border: bool = True,
    class_name: str = "",
) -> str:
    """Generate safe, self-contained HTML for displaying the student avatar.

    Hierarchy:
    1. Custom photo from path (if file exists)
    2. Preset vector SVG (if preset specified and exists)
    3. Initials-based vector SVG
    """
    name = None
    avatar_preset = preset
    avatar_path = path

    if isinstance(profile_or_name, dict):
        name = profile_or_name.get("name")
        avatar_preset = avatar_preset or profile_or_name.get("avatar_preset")
        avatar_path = avatar_path or profile_or_name.get("avatar_path")
    elif isinstance(profile_or_name, str):
        name = profile_or_name
    elif hasattr(profile_or_name, "name"):
        name = getattr(profile_or_name, "name", None)
        avatar_preset = avatar_preset or getattr(profile_or_name, "avatar_preset", None)
        avatar_path = avatar_path or getattr(profile_or_name, "avatar_path", None)

    border_css = f"border: 2px solid {COLOR_APRICOT};" if border else "border: none;"
    style = (
        f"width: {size}px; height: {size}px; border-radius: 50%; "
        f"object-fit: cover; display: inline-block; vertical-align: middle; "
        f"box-shadow: 0 4px 12px rgba(39, 37, 57, 0.15); {border_css}"
    )

    # 1. Custom photo check
    if avatar_path:
        disk_path = Path(avatar_path)
        if disk_path.is_file():
            data_uri = image_file_to_data_uri(disk_path)
            if data_uri:
                return (
                    f'<img src="{data_uri}" alt="{name or "Student"}" '
                    f'class="st-cp-avatar {class_name}" style="{style}" />'
                )

    # 2. Preset SVG check
    if avatar_preset and avatar_preset in PRESET_AVATARS:
        svg_markup = render_preset_svg(avatar_preset, size=size)
        data_uri = svg_to_data_uri(svg_markup)
        return (
            f'<img src="{data_uri}" alt="{name or "Student"}" '
            f'class="st-cp-avatar {class_name}" style="{style}" />'
        )

    # 3. Default initials SVG
    init_svg = generate_initials_svg(name, size=size)
    data_uri = svg_to_data_uri(init_svg)
    return (
        f'<img src="{data_uri}" alt="{name or "Student"}" '
        f'class="st-cp-avatar {class_name}" style="{style}" />'
    )


def validate_and_save_avatar_upload(
    uploaded_file: Any,
    storage_dir: Path = AVATARS_DIR,
) -> Tuple[bool, str, Optional[str]]:
    """Validate uploaded photo, crop to square, resize to 512x512, and save to storage_dir.

    Returns:
        (success, message, saved_relative_path)
    """
    if uploaded_file is None:
        return False, "No file uploaded.", None

    # Size check
    file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    if len(file_bytes) > MAX_AVATAR_BYTES:
        mb = round(len(file_bytes) / (1024 * 1024), 2)
        return False, f"File size ({mb} MB) exceeds maximum allowed 2.0 MB limit.", None

    # Extension check
    file_name = getattr(uploaded_file, "name", "upload.png")
    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"Unsupported format '{ext}'. Please upload PNG, JPG, JPEG, or WEBP.",
            None,
        )

    # PIL verification and square thumbnailing
    try:
        image = Image.open(BytesIO(file_bytes))
        image.verify()  # Verify image integrity
        # Re-open after verify
        image = Image.open(BytesIO(file_bytes))
    except Exception as e:
        return False, f"Invalid or corrupted image file: {e}", None

    try:
        # Convert to RGB (or RGBA if transparency is present)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        # Center square crop
        width, height = image.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        image_cropped = image.crop((left, top, right, bottom))

        # High-quality resize to 512x512
        image_resized = image_cropped.resize(
            TARGET_AVATAR_SIZE,
            resample=Image.Resampling.LANCZOS,
        )

        storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"avatar_{uuid.uuid4().hex[:12]}.png"
        target_path = storage_dir / filename
        image_resized.save(target_path, format="PNG", optimize=True)

        return True, "Avatar image saved successfully.", str(target_path.as_posix())
    except Exception as e:
        return False, f"Failed to process image: {e}", None


def delete_custom_avatar_file(file_path: Optional[str]) -> bool:
    """Safely delete an avatar file from data/avatars/."""
    if not file_path:
        return False
    try:
        path = Path(file_path)
        if path.is_file() and ("avatars" in path.parts or "data" in path.parts):
            path.unlink(missing_ok=True)
            return True
    except Exception:
        pass
    return False
