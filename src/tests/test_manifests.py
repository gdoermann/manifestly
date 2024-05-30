import json
import pathlib
import shutil
import tempfile
import unittest

import fsspec

from manifestly import Manifest
from manifestly import settings

NO_CHANGES = {'added': {}, 'removed': {}, 'changed': {}}


class ManifestlyGeneralTestCase(unittest.TestCase):

    def test_version(self):
        import manifestly
        self.assertEqual(manifestly.get_version(), manifestly.__version__)


class ManifestlyManifestTestCase(unittest.TestCase):

    def setUp(self):
        """
        Common setup for all tests
        """

        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self._syncdir = pathlib.Path(tempfile.mkdtemp())

        # This has the test files, do not create manifests in this as it is checked into git
        # Copy files into the tmpdir
        self.manifest_dir = pathlib.Path(__file__).parent / 'test_files'

    def copy_test_files(self, dest):
        """
        Copy over files from the source to the destination
        """
        for f in self.manifest_dir.iterdir():
            if f.is_dir():
                shutil.copytree(str(f), str(dest / f.name))
            else:
                shutil.copy(str(f), str(dest))

    def tearDown(self):
        """
        Common teardown for all tests
        """
        shutil.rmtree(str(self._tmpdir))
        shutil.rmtree(str(self._syncdir))

    def test_manifest_creation(self):
        manifest_dir = pathlib.Path(__file__).parent / 'test_files'
        _manifest_file = self._tmpdir / '.manifest.json'
        m = Manifest(str(_manifest_file), root=str(manifest_dir))
        m.refresh()
        self.assertTrue(_manifest_file.exists())
        self.assertTrue(m.manifest)
        print(m.manifest)

    def test_manifest_sync(self):
        _sync_manifest = self._syncdir / '.manifestly.json'

        _manifest_file = self._tmpdir / '.manifest.json'
        m = Manifest(str(_manifest_file), root=str(self.manifest_dir))
        m.refresh()
        self.assertTrue(_manifest_file.exists())

        self.assertFalse(_sync_manifest.exists())
        m.sync(Manifest(str(_sync_manifest), root=str(self._syncdir)), dry_run=True)
        self.assertTrue(_sync_manifest.exists())
        self.assertEqual(_sync_manifest.read_text(), '{}')
        m.sync(Manifest(str(_sync_manifest), root=str(self._syncdir)))
        self.assertTrue(_sync_manifest.exists())
        print(m.manifest)

        # Load from directory
        m2 = Manifest(str(self._syncdir))
        self.assertTrue(m2.manifest)

    def test_resolve_root(self):
        _sync_manifest = self._syncdir / '.manifestly.json'

        _manifest_file = self._tmpdir / '.manifest.json'
        m = Manifest(str(_manifest_file), root=str(self.manifest_dir))
        m.sync(Manifest(str(_sync_manifest), root=str(self._syncdir)))
        self.assertTrue(_sync_manifest.exists())

        # Resolve root from valid manifest file
        m2 = Manifest(str(_manifest_file))
        m2.refresh()
        self.assertTrue(m2.manifest)
        self.assertTrue(m2.root, str(self._tmpdir))

    def test_generation(self):
        _copy_dir = self._tmpdir / 'test_files'
        self.copy_test_files(_copy_dir)

        m = Manifest.generate(str(_copy_dir), str(_copy_dir / settings.MANIFEST_NAME))
        m.refresh()
        self.assertTrue(m.manifest)

        # Generate based of the original files
        m2 = Manifest(str(self._tmpdir / '.manifestly.json'), root=str(self.manifest_dir))
        m2.refresh()
        self.assertTrue(m2.manifest)

        self.assertEqual(m2.changed(), NO_CHANGES)

        # Test the generated manifest
        self.assertEqual(m.manifest, m2.manifest)

        # Test the diff
        diff = m.diff(m2)
        self.assertEqual(diff, NO_CHANGES)

        self.assertEqual(m, m2)

        self.assertTrue('.manifestlyignore' in m)
        self.assertNotEqual(m, 'test')
        self.assertTrue('.manifestlyignore' in m.keys())
        self.assertTrue('0cc6c7041e35947e9cb27e32f237ed4db36745ea362000ad4d377e2653a63775' in m.values())

    def test_changes(self):
        _orig_dir = self._tmpdir / 'orig_files'
        _change_dir = self._tmpdir / 'change_files'
        self.copy_test_files(_orig_dir)
        self.copy_test_files(_change_dir)

        orig_manifest = Manifest.generate(str(_orig_dir), str(_orig_dir / settings.MANIFEST_NAME))
        self.assertTrue(orig_manifest.manifest)
        orig_manifest.save()
        _manifest_file = orig_manifest._reopen()
        self.assertEqual(orig_manifest.manifest, json.loads(_manifest_file.open().read()))
        _old_manifest = orig_manifest.manifest
        orig_manifest.refresh()
        self.assertEqual(orig_manifest.manifest, _old_manifest)

        change_manifest = Manifest.generate(str(_change_dir), str(_change_dir / settings.MANIFEST_NAME))
        original_change_manifest = change_manifest.manifest.copy()
        change_manifest.root = None
        change_manifest.refresh()
        self.assertEqual(change_manifest.manifest, original_change_manifest)
        change_manifest.save()

        # No changes
        self.assertEqual(orig_manifest.changed(), NO_CHANGES)
        self.assertEqual(change_manifest.changed(), NO_CHANGES)

        # Remove the test_css.css file
        (_change_dir / 'test_css.css').unlink()
        # Add a file
        _f = _change_dir / 'new_file.txt'
        _f.write_text('test')

        # Update a file
        _uf = _change_dir / 'subdirectory' / 'sub_ts.ts'
        _uf.write_text(_uf.read_text() + '\n// New line')
        changes = change_manifest.changed()
        self.assertNotEqual(changes, NO_CHANGES)
        for key in NO_CHANGES.keys():
            # All categories should have changes
            self.assertTrue(changes[key])

        self.assertEqual(orig_manifest.changed(), NO_CHANGES)

        # You have to refresh/regenerate the manifest to get the changes
        change_manifest.refresh()

        # Test the diff
        # Should be able to pass in the manifest object or the path to the manifest file/directory
        diff = change_manifest.diff(str(_orig_dir))
        diff2 = change_manifest.diff(orig_manifest)
        self.assertEqual(diff, diff2)

        self.assertNotEqual(diff, NO_CHANGES)
        for key in NO_CHANGES.keys():
            # All categories should have changes
            self.assertTrue(diff[key])

        # Create the patch
        patch_file = self._tmpdir / 'patch.json'
        patch = change_manifest.patch(str(_orig_dir), str(patch_file))
        self.assertTrue(patch)
        self.assertTrue(patch_file.exists())

        # Create a pzip (patch zip) with changed files, then check the patch
        zip_file = self._tmpdir / 'patch.zip'
        # Pass in the directory so we hit the case where we have a directory
        # You usually pass in the manifest object
        change_manifest.pzip(str(_orig_dir), str(zip_file))
        self.assertTrue(zip_file.exists())
        self.assertTrue(zip_file.stat().st_size > 0)
        import zipfile
        extracted_dir = self._tmpdir / 'extracted'
        with zipfile.ZipFile(str(zip_file), 'r') as z:
            z.extractall(str(extracted_dir))
        self.assertTrue((self._tmpdir / 'extracted').exists())

        # Check the files in the extracted zip
        self.assertTrue((extracted_dir / 'new_file.txt').exists())
        self.assertTrue((extracted_dir / 'subdirectory' / 'sub_ts.ts').exists())
        self.assertFalse((extracted_dir / 'test_css.css').exists())

        # Synchronize the changes to the original directory
        change_manifest.sync(str(_orig_dir), dry_run=True)

        # Remove the added file and make sure it doesn't throw errors when we sync
        (_change_dir / 'new_file.txt').unlink()
        self.assertFalse((_change_dir / 'new_file.txt').exists())
        change_manifest.sync(orig_manifest)
        self.assertFalse((_orig_dir / 'new_file.txt').exists())

        root = fsspec.open(str(change_manifest.root))
        new_manifest = Manifest.generate(str(_change_dir),
                                         str(_change_dir / settings.MANIFEST_NAME), root_path=root)
        new_manifest.save()

        # Test the diff
        diff = new_manifest.diff(orig_manifest)
        self.assertEqual(diff, NO_CHANGES)

    def test_bad_manifest(self):
        _orig_dir = self._tmpdir / 'orig_files'
        self.copy_test_files(_orig_dir)

        m1 = Manifest.generate(str(_orig_dir), str(_orig_dir / settings.MANIFEST_NAME))
        m1.save()
        _manifest_file = m1._reopen()
        self.assertEqual(m1.manifest, json.loads(_manifest_file.open().read()))

        # Corrupt the manifest
        m1._reopen('w').open().write('bad json')
        m1.load()
        self.assertEqual(m1.manifest, {})

        m1._reopen('w').open().write('')
        m1.load()
        self.assertEqual(m1.manifest, {})


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
