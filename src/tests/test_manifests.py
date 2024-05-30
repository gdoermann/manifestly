import json
import pathlib
import shutil
import tempfile
import unittest

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

        # Copy all directories, files, and subdirectories to _tmpdir
        for f in self.manifest_dir.iterdir():
            if f.is_dir():
                shutil.copytree(str(f), str(_copy_dir / f.name))
            else:
                shutil.copy(str(f), str(_copy_dir))

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

        # Copy all directories, files, and subdirectories to _tmpdir
        for f in self.manifest_dir.iterdir():
            if f.is_dir():
                shutil.copytree(str(f), str(_orig_dir / f.name))
                shutil.copytree(str(f), str(_change_dir / f.name))
            else:
                shutil.copy(str(f), str(_orig_dir))
                shutil.copy(str(f), str(_change_dir))

        m1 = Manifest.generate(str(_orig_dir), str(_orig_dir / settings.MANIFEST_NAME))
        self.assertTrue(m1.manifest)
        m1.save()
        _manifest_file = m1._reopen()
        self.assertEqual(m1.manifest, json.loads(_manifest_file.open().read()))
        _old_manifest = m1.manifest
        m1.refresh()
        self.assertEqual(m1.manifest, _old_manifest)

        m2 = Manifest.generate(str(_change_dir), str(_change_dir / settings.MANIFEST_NAME))
        m2.refresh()
        m2.save()

        # No changes
        self.assertEqual(m1.changed(), NO_CHANGES)
        self.assertEqual(m2.changed(), NO_CHANGES)


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
