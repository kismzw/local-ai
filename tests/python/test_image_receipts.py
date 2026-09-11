from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("image_receipts", ROOT / "scripts/image-receipts.py")
image_receipts = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(image_receipts)


def test_missing_receipt_requires_explicit_adoption(tmp_path: Path):
    image = tmp_path / "image.sif"
    image.write_bytes(b"first")
    receipt = tmp_path / "receipts.toml"
    source = "docker://repo@sha256:" + "a" * 64
    with pytest.raises(image_receipts.ReceiptError, match="receipt is missing"):
        image_receipts.verify(receipt, "llama", source, image, None)
    image_receipts.adopt(receipt, "llama", source, image, None)
    assert image_receipts.verify(receipt, "llama", source, image, None) == "verified"


def test_receipt_rejects_source_or_artifact_tampering(tmp_path: Path):
    image = tmp_path / "image.sif"
    image.write_bytes(b"first")
    receipt = tmp_path / "receipts.toml"
    source = "docker://repo@sha256:" + "a" * 64
    image_receipts.record(receipt, "llama", source, image, None)
    with pytest.raises(image_receipts.ReceiptError, match="source"):
        image_receipts.verify(receipt, "llama", "docker://repo@sha256:" + "b" * 64, image, None)
    image.write_bytes(b"changed")
    with pytest.raises(image_receipts.ReceiptError, match="artifact_sha256"):
        image_receipts.verify(receipt, "llama", source, image, None)


def test_refresh_record_replaces_an_old_oci_source(tmp_path: Path):
    image = tmp_path / "image.sif"
    image.write_bytes(b"new artifact")
    receipt = tmp_path / "receipts.toml"
    old_source = "docker://repo@sha256:" + "a" * 64
    new_source = "docker://repo@sha256:" + "b" * 64
    image_receipts.record(receipt, "llama", old_source, image, None)
    image_receipts.record(receipt, "llama", new_source, image, None)
    assert image_receipts.verify(receipt, "llama", new_source, image, None) == "verified"


def test_refresh_accepts_new_artifact_for_same_source(tmp_path: Path):
    image = tmp_path / "tool.sif"
    definition = tmp_path / "tool.def"
    image.write_bytes(b"first")
    definition.write_text("Bootstrap: docker\n", encoding="utf-8")
    receipt = tmp_path / "receipts.toml"
    image_receipts.record(receipt, "tool", None, image, definition)
    image.write_bytes(b"rebuilt differently")
    image_receipts.record(receipt, "tool", None, image, definition)
    assert image_receipts.verify(receipt, "tool", None, image, definition) == "verified"
    assert "source" not in image_receipts.load(receipt)["tool"]


def test_tool_definition_change_is_rejected(tmp_path: Path):
    image = tmp_path / "tool.sif"
    definition = tmp_path / "tool.def"
    image.write_bytes(b"image")
    definition.write_text("Bootstrap: docker\n", encoding="utf-8")
    receipt = tmp_path / "receipts.toml"
    image_receipts.record(receipt, "tool", None, image, definition)
    definition.write_text("Bootstrap: localimage\n", encoding="utf-8")
    with pytest.raises(image_receipts.ReceiptError, match="definition_sha256"):
        image_receipts.verify(receipt, "tool", None, image, definition)
    image_receipts.record(receipt, "tool", None, image, definition)
    assert image_receipts.verify(receipt, "tool", None, image, definition) == "verified"
