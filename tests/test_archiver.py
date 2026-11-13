# -*- coding: utf-8 -*-
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from app.core import archiver
from app.core import importer


class ArchiverDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _executable(self, *parts):
        path = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as stream:
            stream.write(b"MZ")
        return path

    def test_prefers_bundled_component_over_installed_and_path(self):
        bundled = self._executable("7zip", "7z.exe")
        installed = self._executable("installed", "7z.exe")
        on_path = self._executable("path", "7z.exe")

        found = archiver.find_archiver(
            resource_root=self.root,
            installed_paths=[installed],
            path_lookup=lambda _name: on_path,
        )

        self.assertEqual(found.path, bundled)
        self.assertEqual(found.kind, "7z")
        self.assertEqual(found.source, "bundled")

    def test_uses_remembered_manual_path_when_bundled_component_is_missing(self):
        remembered = self._executable("manual", "7z.exe")
        installed = self._executable("installed", "7z.exe")

        found = archiver.find_archiver(
            remembered_path=remembered,
            resource_root=self.root,
            installed_paths=[installed],
            path_lookup=lambda _name: "",
        )

        self.assertEqual(found.path, remembered)
        self.assertEqual(found.source, "remembered")

    def test_uses_system_path_as_last_fallback(self):
        installed = self._executable("installed", "WinRAR.exe")
        on_path = self._executable("path", "7z.exe")

        found = archiver.find_archiver(
            resource_root=self.root,
            installed_paths=[installed],
            path_lookup=lambda name: on_path if name == "7z.exe" else "",
        )

        self.assertEqual(found.path, installed)
        self.assertEqual(found.kind, "winrar")
        self.assertEqual(found.source, "installed")

        found = archiver.find_archiver(
            resource_root=self.root,
            installed_paths=[],
            path_lookup=lambda name: on_path if name == "7z.exe" else "",
        )
        self.assertEqual(found.path, on_path)
        self.assertEqual(found.source, "path")

    def test_returns_none_when_no_component_is_available(self):
        found = archiver.find_archiver(
            resource_root=self.root,
            installed_paths=[],
            path_lookup=lambda _name: "",
        )
        self.assertIsNone(found)

    def test_accepts_an_explicitly_selected_7z_executable(self):
        selected = self._executable("manual", "7z.exe")
        found = archiver.from_path(selected)
        self.assertEqual(found.path, selected)
        self.assertEqual(found.kind, "7z")
        self.assertEqual(found.source, "manual")

    def test_rejects_an_unsupported_executable(self):
        selected = self._executable("manual", "not-an-archiver.exe")
        self.assertIsNone(archiver.from_path(selected))


class ArchiverCommandTests(unittest.TestCase):
    def test_builds_7zip_extraction_command(self):
        info = archiver.ArchiverInfo(r"C:\tools\7z.exe", "7z", "bundled")
        command = info.extract_command(r"C:\mods\test.rar", r"C:\temp\out")
        self.assertEqual(
            command,
            [r"C:\tools\7z.exe", "x", "-y", r"-oC:\temp\out",
             "--", r"C:\mods\test.rar"],
        )

    def test_builds_winrar_extraction_command(self):
        info = archiver.ArchiverInfo(r"C:\tools\WinRAR.exe", "winrar", "installed")
        command = info.extract_command(r"C:\mods\test.rar", r"C:\temp\out")
        self.assertEqual(
            command,
            [r"C:\tools\WinRAR.exe", "x", "-ibck", "-y",
             "--", r"C:\mods\test.rar", "C:\\temp\\out\\"],
        )

    def test_extracts_missing_component_error_from_text(self):
        with self.assertRaises(archiver.ArchiverNotFoundError):
            archiver.find_archiver(
                resource_root=os.path.join(tempfile.gettempdir(), "missing-7zip"),
                installed_paths=[],
                path_lookup=lambda _name: "",
                require=True,
            )

    def test_importer_uses_the_selected_archiver(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "mod.7z")
            destination = os.path.join(root, "out")
            with open(source, "wb") as stream:
                stream.write(b"7z")
            selected = archiver.ArchiverInfo(
                os.path.join(root, "chosen", "7z.exe"), "7z", "remembered")
            completed = mock.Mock(returncode=0, stdout="", stderr="")

            with mock.patch(
                    "app.core.importer.subprocess.run",
                    return_value=completed) as run:
                count = importer.extract_archive(
                    source, destination, archiver_info=selected)

            self.assertEqual(count, 0)
            run.assert_called_once_with(
                selected.extract_command(source, destination),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace",
            )

    def test_msi_extraction_quotes_paths_that_contain_spaces(self):
        completed = mock.Mock(returncode=0, stdout="", stderr="")
        with tempfile.TemporaryDirectory() as root:
            msi = os.path.join(root, "7zip installer.msi")
            destination = os.path.join(root, "extracted files")
            with mock.patch(
                    "app.core.archiver.subprocess.run",
                    return_value=completed) as run:
                archiver._extract_msi(msi, destination)

        command = run.call_args.args[0]
        self.assertIn('"%s"' % msi, command)
        self.assertIn('TARGETDIR="%s"' % destination, command)


class DownloadSelectionTests(unittest.TestCase):
    def test_selects_the_official_x64_msi_from_download_page(self):
        html = """
        <a href="a/7z2600-extra.7z">Extra</a>
        <a href="a/7z2600-x64.msi">64-bit Windows x64</a>
        <a href="a/7z2600.exe">32-bit Windows</a>
        """
        selected = archiver.select_windows_installer(html)
        self.assertEqual(
            selected,
            "https://www.7-zip.org/a/7z2600-x64.msi",
        )

    def test_accepts_the_official_7zip_github_release(self):
        html = (
            '<a href="https://github.com/ip7z/7zip/releases/download/26.06/'
            '7z2606-x64.msi">Download</a>'
        )
        selected = archiver.select_windows_installer(html)
        self.assertEqual(
            selected,
            "https://github.com/ip7z/7zip/releases/download/26.06/"
            "7z2606-x64.msi",
        )

    def test_rejects_a_lookalike_github_repository(self):
        html = (
            '<a href="https://github.com/not-7zip/7zip/releases/download/'
            '26.06/7z2606-x64.msi">Download</a>'
        )
        with self.assertRaises(archiver.ArchiverError):
            archiver.select_windows_installer(html)

    def test_reads_the_published_sha256_for_the_selected_asset(self):
        html = """
        <a href="/ip7z/7zip/releases/download/26.06/7z2606-x64.msi">
          7z2606-x64.msi
        </a>
        <span>sha256:6dc822569e777d9a3ecd5ffcbc22b55600af87e6c5d9810a64e8566cf5a4af9f</span>
        <a href="/ip7z/7zip/releases/download/26.06/7z2606.exe">7z2606.exe</a>
        <span>sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</span>
        """
        digest = archiver.release_digest_from_html(
            html, "7z2606-x64.msi")
        self.assertEqual(
            digest,
            "6dc822569e777d9a3ecd5ffcbc22b55600af87e6c5d9810a64e8566cf5a4af9f",
        )

    def test_verifies_a_downloaded_file_sha256(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "installer.msi")
            with open(path, "wb") as stream:
                stream.write(b"official installer")
            wrong_digest = "0" * 64
            # The helper computes the real digest; an altered digest must fail.
            archiver.verify_sha256(path, archiver.sha256_file(path))
            with self.assertRaises(archiver.ArchiverError):
                archiver.verify_sha256(path, wrong_digest)


class BundledComponentIntegrationTests(unittest.TestCase):
    def test_bundled_7zip_contains_rar_codecs_and_extracts_7z(self):
        info = archiver.find_archiver()
        if not info or info.source != "bundled":
            self.skipTest("bundled 7-Zip component is not available")

        codecs = subprocess.run(
            [info.path, "i"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        self.assertEqual(codecs.returncode, 0)
        self.assertIn("Rar5", codecs.stdout)

        with tempfile.TemporaryDirectory() as root:
            source_dir = os.path.join(root, "source")
            extract_dir = os.path.join(root, "extracted")
            os.makedirs(source_dir)
            payload = os.path.join(source_dir, "payload.txt")
            with open(payload, "wb") as stream:
                stream.write(b"L4D2 archiver integration")
            archive = os.path.join(root, "payload.7z")
            created = subprocess.run(
                [info.path, "a", "-t7z", archive, "payload.txt"],
                cwd=source_dir, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            self.assertEqual(created.returncode, 0, created.stderr)

            count = importer.extract_archive(
                archive, extract_dir, archiver_info=info)
            self.assertEqual(count, 1)
            with open(os.path.join(extract_dir, "payload.txt"), "rb") as stream:
                self.assertEqual(stream.read(), b"L4D2 archiver integration")


if __name__ == "__main__":
    unittest.main()
