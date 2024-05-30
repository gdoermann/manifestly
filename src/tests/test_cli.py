import pathlib
import shutil
import tempfile
import unittest

from click.testing import CliRunner

from manifestly import settings
from manifestly.cli import cli


class ManifestlyCLITestCase(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.manifest_dir = pathlib.Path(__file__).parent / 'test_files'
        self.copy_test_files(self._tmpdir)

    def tearDown(self):
        shutil.rmtree(str(self._tmpdir))

    def copy_test_files(self, dest):
        """
        Copy over files from the source to the destination
        """
        for f in self.manifest_dir.iterdir():
            if f.is_dir():
                shutil.copytree(str(f), str(dest / f.name))
            else:
                shutil.copy(str(f), str(dest))

    def test_generate_cmd(self):
        result = self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        self.assertEqual(result.exit_code, 0)
        manifest_file = self._tmpdir / settings.MANIFEST_NAME
        self.assertTrue(manifest_file.exists())

    def test_generate_cmd2(self):
        manifest_file = str(self._tmpdir / settings.MANIFEST_NAME)
        result = self.runner.invoke(cli, ['generate', str(self._tmpdir), '--output-file', manifest_file])
        self.assertEqual(result.exit_code, 0)
        manifest_file = self._tmpdir / settings.MANIFEST_NAME
        self.assertTrue(manifest_file.exists())

    def test_changed_cmd(self):
        # First, generate a manifest
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])

        # Now, change a file
        (self._tmpdir / 'new_file.txt').write_text('new content')

        result = self.runner.invoke(cli, ['changed', str(self._tmpdir / settings.MANIFEST_NAME)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Changed files:', result.output)

    def test_changed_cmd_no_changes(self):
        # First, generate a manifest
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])

        result = self.runner.invoke(cli, ['changed', str(self._tmpdir / settings.MANIFEST_NAME)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('No files have changed', result.output)
        self.assertNotIn('Changed files:', result.output)

    def test_refresh_cmd(self):
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        manifest_file = self._tmpdir / settings.MANIFEST_NAME
        self.assertTrue(manifest_file.exists())

        result = self.runner.invoke(cli, ['refresh', str(manifest_file)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Manifest refreshed', result.output)

    def test_sync_cmd(self):
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        manifest_file = self._tmpdir / settings.MANIFEST_NAME

        sync_dir = pathlib.Path(tempfile.mkdtemp())
        sync_manifest_file = sync_dir / 'sync_manifest.json'

        result = self.runner.invoke(cli, [
            'sync', str(manifest_file), str(sync_manifest_file),
            '--source_directory', str(self._tmpdir), '--target_directory', str(sync_dir), '--dry-run'
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Dry run completed', result.output)
        shutil.rmtree(str(sync_dir))

    def test_sync_cmd_refresh(self):
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        manifest_file = self._tmpdir / settings.MANIFEST_NAME

        sync_dir = pathlib.Path(tempfile.mkdtemp())
        sync_manifest_file = sync_dir / 'sync_manifest.json'

        result = self.runner.invoke(cli, [
            'sync', str(manifest_file), str(sync_manifest_file),
            '--source_directory', str(self._tmpdir), '--target_directory', str(sync_dir), '--refresh'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Synced', result.output)
        shutil.rmtree(str(sync_dir))

    def test_compare_cmd(self):
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        manifest_file = self._tmpdir / settings.MANIFEST_NAME

        compare_dir = pathlib.Path(tempfile.mkdtemp())
        self.copy_test_files(compare_dir)
        compare_manifest_file = compare_dir / 'compare_manifest.json'
        self.runner.invoke(cli, ['generate', str(compare_dir)])

        result = self.runner.invoke(cli, ['compare', str(manifest_file), str(compare_manifest_file)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('added', result.output)
        shutil.rmtree(str(compare_dir))

    def test_patch_cmd(self):
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        manifest_file = self._tmpdir / settings.MANIFEST_NAME

        patch_dir = pathlib.Path(tempfile.mkdtemp())
        self.copy_test_files(patch_dir)
        patch_manifest_file = patch_dir / 'patch_manifest.json'
        self.runner.invoke(cli, ['generate', str(patch_dir)])

        output_patch_file = self._tmpdir / 'output_patch.json'

        result = self.runner.invoke(cli, [
            'patch', str(manifest_file), str(patch_manifest_file), str(output_patch_file)
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Patch saved', result.output)
        self.assertTrue(output_patch_file.exists())
        shutil.rmtree(str(patch_dir))

    def test_pzip_cmd(self):
        self.runner.invoke(cli, ['generate', str(self._tmpdir)])
        manifest_file = self._tmpdir / settings.MANIFEST_NAME

        pzip_dir = pathlib.Path(tempfile.mkdtemp())
        self.copy_test_files(pzip_dir)
        pzip_manifest_file = pzip_dir / 'pzip_manifest.json'
        self.runner.invoke(cli, ['generate', str(pzip_dir)])

        output_zip_file = self._tmpdir / 'output.zip'

        result = self.runner.invoke(cli, [
            'pzip', str(manifest_file), str(pzip_manifest_file), str(output_zip_file)
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Zip file saved', result.output)
        self.assertTrue(output_zip_file.exists())
        shutil.rmtree(str(pzip_dir))


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
