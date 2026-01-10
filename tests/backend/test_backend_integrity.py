import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


class TestBackendIntegrity(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.build_dir = self.test_dir / "build" / "exe"
        self.build_dir.mkdir(parents=True)
        self.electron_dir = self.test_dir / "electron"
        self.electron_dir.mkdir()

        # Create some files in build/exe
        self.files = {
            "ReticulumMeshChatX": "binary content",
            "lib/some_lib.so": "library content",
        }

        for rel_path, content in self.files.items():
            p = self.build_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w") as f:
                f.write(content)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def generate_manifest(self):
        manifest = {
            "_metadata": {
                "version": 1,
                "date": "2026-01-03",
                "time": "12:00:00",
            },
            "files": {},
        }
        for root, _, files in os.walk(self.build_dir):
            for file in files:
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(self.build_dir))
                with open(full_path, "rb") as f:
                    hash = hashlib.sha256(f.read()).hexdigest()
                manifest["files"][rel_path] = hash

        manifest_path = self.electron_dir / "backend-manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)
        return manifest_path

    def test_manifest_generation(self):
        """Test that the build script logic produces a valid manifest."""
        manifest_path = self.generate_manifest()
        with open(manifest_path) as f:
            manifest = json.load(f)

        self.assertEqual(len(manifest["files"]), 2)
        self.assertIn("ReticulumMeshChatX", manifest["files"])
        self.assertIn("lib/some_lib.so", manifest["files"])
        self.assertIn("_metadata", manifest)

    def test_tampering_detection_logic(self):
        """Test that modifying a file changes its hash (logic check)."""
        manifest_path = self.generate_manifest()
        with open(manifest_path) as f:
            manifest = json.load(f)

        old_hash = manifest["files"]["ReticulumMeshChatX"]

        # Tamper
        with open(self.build_dir / "ReticulumMeshChatX", "w") as f:
            f.write("malicious code")

        with open(self.build_dir / "ReticulumMeshChatX", "rb") as f:
            new_hash = hashlib.sha256(f.read()).hexdigest()

        self.assertNotEqual(old_hash, new_hash)


if __name__ == "__main__":
    unittest.main()
