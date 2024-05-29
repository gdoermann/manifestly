"""
Manifestly is a Python library for generating, loading, comparing, and syncing file manifests.

This is the core module that provides the core functionality for generating, loading, comparing,
and syncing file manifests.
"""

import hashlib
import json
import pathlib
from typing import Union

from manifestly import settings


class Manifest:
    """
    A class to represent a manifest
    """

    def __init__(self, manifest_file: Union[str, pathlib.Path], manifest=None):
        if isinstance(manifest_file, str):
            manifest_file = pathlib.Path(manifest_file)
        self.manifest_file: pathlib.Path = manifest_file
        self.manifest = manifest
        if self.manifest is None:
            self.load()

    def save(self, file_path):
        """
        Save the manifest to a file
        :param file_path: The path to the file
        """
        with open(file_path, 'w') as f:
            json.dump(self.manifest, f)

    def items(self):
        """
        Get the items in the manifest
        :return:
        """
        return self.manifest.items()

    def load(self):
        """
        Load a manifest from a file
        :param manifest_file: The path to the manifest file
        :return: The loaded manifest
        """
        with self.manifest_file.open() as f:
            self.manifest = json.load(f)

    @classmethod
    def generate(cls, directory, manifest_file: str = None,
                 hash_algorithm=settings.DEFAULT_HASH_ALGORITHM) -> 'Manifest':
        """
        Generate a manifest for a directory
        :param directory: The directory to generate the manifest for
        :param manifest_file: Optional path to the manifest file
        :param hash_algorithm: Hash algorithm to use
        :return: The generated manifest
        """
        manifest = {}
        for file_path in pathlib.Path(directory).rglob('*'):
            if file_path.is_file():
                # Skip anything with the settings.MANIFEST_NAME
                if file_path.name == settings.MANIFEST_NAME:
                    continue
                manifest[str(file_path)] = cls.calculate_hash(file_path, algorithm=hash_algorithm)

        if manifest_file:
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f)
        return cls(manifest_file, manifest)

    def sync(self, target_manifest, source_directory, target_directory):
        """
        Sync the target directory to match the source manifest
        :param target_manifest: The path to the target manifest file or a Manifest object
        :param source_directory: The source directory
        :param target_directory: The target directory
        """
        if isinstance(target_manifest, str):
            target_manifest = Manifest(target_manifest)
        diff = self.diff(target_manifest)

        source_directory = pathlib.Path(source_directory)
        target_directory = pathlib.Path(target_directory)

        for file in diff['added'] + diff['changed']:
            source_file = source_directory / file
            target_file = target_directory / file
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(source_file.read_bytes())

        for file in diff['removed']:
            target_file = target_directory / file
            if target_file.exists():
                target_file.unlink()

    def diff(self, target_manifest) -> dict:
        """
        Compare the manifest with another manifest
        :param target_manifest: The path to the target manifest file or a Manifest object
        :return: A dictionary with the differences
        """
        if not isinstance(target_manifest, Manifest):
            target_manifest = Manifest(target_manifest)
        diff = {
            'added': [],
            'removed': [],
            'changed': []
        }
        for file, hash in self.items():
            if file not in target_manifest.items():
                diff['added'].append(file)
            elif target_manifest.items()[file] != hash:
                diff['changed'].append(file)
        for file in target_manifest.items():
            if file not in self.items():
                diff['removed'].append(file)
        return diff

    def patch(self, target_manifest, output_patch_file) -> dict:
        """
        Generate a patch file that can be used to update the target manifest to match the source manifest.
        :param target_manifest: The path to the target manifest file or a Manifest object
        :param output_patch_file: The path to the output patch/json file
        :return: The diff dictionary
        """
        if not isinstance(target_manifest, Manifest):
            target_manifest = Manifest(target_manifest)
        diff = self.diff(target_manifest)
        with open(output_patch_file, 'w') as f:
            json.dump(diff, f)
        return diff

    def pzip(self, target_manifest, output_zip_file):
        """
        Generate a zip file containing the files that need to be added or updated to make the target manifest match
        :param target_manifest: The path to the target manifest file or a Manifest object
        :param output_zip_file: The path to the output zip file
        """
        import zipfile
        if not isinstance(target_manifest, Manifest):
            target_manifest = Manifest(target_manifest)
        diff = self.diff(target_manifest)
        with zipfile.ZipFile(output_zip_file, 'w') as zf:
            for file in diff['added'] + diff['changed']:
                zf.write(file)
            with open('deleted_files.txt', 'w') as f:
                f.write("\n".join(diff['removed']))
            zf.write('deleted_files.txt')
            pathlib.Path('deleted_files.txt').unlink()

    @staticmethod
    def calculate_hash(file_path, algorithm=settings.DEFAULT_HASH_ALGORITHM):
        """
        Calculate the hash of a file
        :param file_path: The path to the file
        :param algorithm: The hash algorithm to use
        :return: The hash of the file
        """
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            while chunk := f.read(settings.CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()
