import os
from pathlib import Path


def resolve_cyrillic_font_ttf() -> Path:
    override = os.environ.get("LOBANOV_EXPORT_PDF_FONT")
    if override:
        p = Path(override)
        if p.is_file():
            return p
        err_msg = f"LOBANOV_EXPORT_PDF_FONT is not a file: {override}"
        raise FileNotFoundError(err_msg)

    bundled = Path(__file__).resolve().parent.parent / "resources" / "fonts" / "DejaVuSans.ttf"
    if bundled.is_file():
        return bundled

    windir = os.environ.get("WINDIR")
    if windir:
        arial = Path(windir) / "Fonts" / "arial.ttf"
        if arial.is_file():
            return arial

    for candidate in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ):
        if candidate.is_file():
            return candidate

    err_msg = (
        "No TTF found for PDF Cyrillic. Set LOBANOV_EXPORT_PDF_FONT to a .ttf path, "
        "or place lobanov/resources/fonts/DejaVuSans.ttf, or use Windows/macOS with Arial."
    )
    raise FileNotFoundError(err_msg)
