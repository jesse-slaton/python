"""Tests for KB identifier validation in generators."""

import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from update_catalog_fetcher.metadata_generator import MetadataGenerator
from update_catalog_fetcher.models import WindowsUpdate, validate_kb
from update_catalog_fetcher.script_generator import PowerShellScriptGenerator


def make_update(kb: str | None) -> WindowsUpdate:
    return WindowsUpdate(
        title="Test Update",
        kb=kb,
        products="Windows 10",
        classification="Security Updates",
        last_updated=datetime.now(),
        version="1.0",
        size="100 MB",
        update_id="12345",
        architecture="x64",
    )


BAD_KB = 'KB123"; x'
GOOD_KB = "KB5034441"


class TestValidateKb(unittest.TestCase):
    def test_accepts_valid(self):
        for kb in ("KB5034441", "kb5034441", "5034441"):
            with self.subTest(kb=kb):
                self.assertEqual(validate_kb(kb), kb)

    def test_rejects_invalid(self):
        for kb in ('KB1"2', "KB 123", "KB$(x)", "$(1)", "", "KB"):
            with self.subTest(kb=kb), self.assertRaisesRegex(ValueError, "invalid KB identifier"):
                validate_kb(kb)


class TestGeneratorsValidateKb(unittest.TestCase):
    def test_install_script(self):
        with self.assertRaises(ValueError):
            PowerShellScriptGenerator.generate_install_script(make_update(BAD_KB), "f.msu")
        out = PowerShellScriptGenerator.generate_install_script(make_update(GOOD_KB), "f.msu")
        self.assertIn(GOOD_KB, out)

    def test_install_script_without_kb(self):
        out = PowerShellScriptGenerator.generate_install_script(make_update(None), "f.msu")
        self.assertIn("Windows Update", out)

    def test_remove_script(self):
        with self.assertRaises(ValueError):
            PowerShellScriptGenerator.generate_remove_script(make_update(BAD_KB))
        out = PowerShellScriptGenerator.generate_remove_script(make_update(GOOD_KB))
        self.assertIn("5034441", out)

    def test_metadata(self):
        with self.assertRaises(ValueError):
            MetadataGenerator.generate_metadata(make_update(BAD_KB), "i.ps1", "r.ps1", "f.msu")
        meta = MetadataGenerator.generate_metadata(make_update(GOOD_KB), "i.ps1", "r.ps1", "f.msu")
        self.assertIn(GOOD_KB, meta.install_verification or "")

    def test_wql(self):
        with self.assertRaises(ValueError):
            MetadataGenerator._generate_wql_verification(make_update(BAD_KB))
        out = MetadataGenerator._generate_wql_verification(make_update(GOOD_KB))
        self.assertIn(GOOD_KB, out)

    def test_wql_mixed_case_prefix(self):
        for kb in ("KB5034441", "kb5034441", "Kb5034441", "kB5034441", "5034441"):
            with self.subTest(kb=kb):
                self.assertEqual(make_update(kb).kb_number, "5034441")
                out = MetadataGenerator._generate_wql_verification(make_update(kb))
                self.assertIn('HotFixID="KB5034441"', out)

    def test_readme(self):
        # generate_readme interpolates the non-existent Path.ctime (pre-existing
        # bug, out of scope here); stub it so the good-KB path can be exercised.
        with mock.patch.object(Path, "ctime", "now", create=True):
            with self.assertRaises(ValueError):
                MetadataGenerator.generate_readme(
                    make_update(BAD_KB), "f.msu", "i.ps1", "r.ps1", "m.json"
                )
            out = MetadataGenerator.generate_readme(
                make_update(GOOD_KB), "f.msu", "i.ps1", "r.ps1", "m.json"
            )
        self.assertIn(GOOD_KB, out)
