#!/usr/bin/env python3

import os
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get(
    "COMMENT_SIDECAR_BASE_URL",
    "http://localhost",
).rstrip("/")
DELIVERY_URL = f"{BASE_URL}/comment-sidecar-js-delivery.php"

GENERIC_ERROR = "Internal server error."


def assert_missing_resource_is_generic(relative_path):
    resource = ROOT_DIR / relative_path
    backup = resource.with_name(resource.name + ".r2-seal-backup")

    assert resource.exists()
    assert not backup.exists()

    resource.rename(backup)
    try:
        response = requests.get(DELIVERY_URL, timeout=10)
    finally:
        backup.rename(resource)

    assert response.status_code == 500
    assert response.text == GENERIC_ERROR
    assert str(ROOT_DIR) not in response.text
    assert relative_path not in response.text


def test_missing_javascript_template_does_not_leak_path():
    assert_missing_resource_is_generic("src/comment-sidecar.js")


def test_missing_form_template_does_not_leak_path():
    assert_missing_resource_is_generic(
        "src/form-templates/bootstrap-default.html"
    )


def test_missing_translation_does_not_leak_path():
    assert_missing_resource_is_generic("src/translations/en.php")
