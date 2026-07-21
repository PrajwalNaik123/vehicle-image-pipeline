"""
Minimal smoke tests for the pure-function checks (no DB/queue needed).
Run with: pytest tests/
"""
import io
import os
import sys

from PIL import Image as PILImage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.checks.blur import check_blur
from app.checks.brightness import check_brightness
from app.checks.screenshot import check_screenshot


def _make_test_image(path, size=(400, 300), color=(120, 120, 120)):
    PILImage.new("RGB", size, color).save(path)


def test_blur_check_runs_on_solid_image(tmp_path):
    img_path = tmp_path / "solid.jpg"
    _make_test_image(str(img_path))
    result = check_blur(str(img_path))
    assert result["check_name"] == "blur_detection"
    # A flat solid-color image has zero variance -> should be flagged blurry
    assert result["passed"] is False


def test_brightness_check_flags_dark_image(tmp_path):
    img_path = tmp_path / "dark.jpg"
    _make_test_image(str(img_path), color=(5, 5, 5))
    result = check_brightness(str(img_path))
    assert result["passed"] is False
    assert "dark" in result["detail"].lower()


def test_brightness_check_passes_normal_image(tmp_path):
    img_path = tmp_path / "normal.jpg"
    _make_test_image(str(img_path), color=(130, 130, 130))
    result = check_brightness(str(img_path))
    assert result["passed"] is True


def test_screenshot_check_runs_without_crashing(tmp_path):
    img_path = tmp_path / "img.jpg"
    _make_test_image(str(img_path), size=(1080, 1920))
    result = check_screenshot(str(img_path))
    assert result["check_name"] == "screenshot_detection"
    assert isinstance(result["passed"], bool)
