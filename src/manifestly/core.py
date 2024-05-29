"""
Manifestly is a Python library for generating, loading, comparing, and syncing file manifests.

This is the core module that provides the core functionality for generating, loading, comparing,
and syncing file manifests.
"""

import hashlib
import json
from typing import Union

import fsspec
from fsspec.core import OpenFile

from manifestly import settings


class Manifest:
    """
    A class to represent a manifest
    """

    def __init__(self, manifest_file: Union[str, OpenFile], manifest=None,
                 root: str = None):
        if isinstance(manifest_file, str):
            manifest_file = fsspec.open(manifest_file)
        self.manifest_file: OpenFile = manifest_file
        self.manifest = manifest
        self.root = root
        if self.manifest is None:
            self.load()

    def save(self, file_path):
        """
        Save the manifest to a file
        :param file_path: The path to the file
        """
        if not isinstance(file_path, OpenFile):
            file_path = fsspec.open(file_path, 'w')
        # Check if we are in write mode...
        if 'w' not in file_path.mode:
            # Reopen in write mode
            file_path = fsspec.open(file_path.path, 'w')
        # Make sure directories exist
        file_path.fs.makedirs(file_path.fs._parent(file_path.path), exist_ok=True)

        with file_path.open() as f:
            json.dump(self.manifest, f, indent=2)

    def items(self):
        """
        Get the items in the manifest
        :return:
        """
        return self.manifest.items()

    def load(self):
        """
        Load a manifest from a file
        :return: The loaded manifest
        """
        try:
            with self.manifest_file as f:
                self.manifest = json.load(f)
        except FileNotFoundError:
            self.manifest = {}
            self.save(self.manifest_file)

    @classmethod
    def default_manifest_file(cls, directory: Union[str, OpenFile]) -> OpenFile:
        """
        Get the default manifest file for a directory.
        The directory must be a string or an fsspec.core.OpenFile object.

        :param directory: The directory
        :return: The path to the manifest file
        """
        fs, path = fsspec.core.url_to_fs(directory)
        manifest_path = fs.sep.join([path.rstrip(fs.sep), settings.MANIFEST_NAME])
        return fsspec.open(manifest_path)

    @classmethod
    def generate(cls, directory, manifest_file: Union[str, OpenFile] = None, root_path: str = None,
                 hash_algorithm=settings.DEFAULT_HASH_ALGORITHM) -> 'Manifest':
        """
        Generate a manifest for a directory
        :param directory: The directory to generate the manifest for
        :param manifest_file: Optional path to the manifest file
        :param root_path: The root path to use (all paths will be relative to this)
        :param hash_algorithm: Hash algorithm to use
        :return: The generated manifest
        """
        manifest = {}
        fs, path = fsspec.core.url_to_fs(directory)
        if root_path is None:
            root_path = path

        for file_path in fs.find(path):
            if fs.isfile(file_path):
                if file_path.endswith(settings.MANIFEST_NAME):
                    continue
                relative_path = file_path[len(root_path):].lstrip('/')
                manifest[relative_path] = cls.calculate_hash(fs.open(file_path), algorithm=hash_algorithm)

        if manifest_file:
            if not isinstance(manifest_file, OpenFile):
                manifest_file = fsspec.open(manifest_file, 'w')
            elif 'w' not in manifest_file.mode:
                manifest_file = fsspec.open(manifest_file.path, 'w')
            with manifest_file as f:
                json.dump(manifest, f, indent=2)
        return cls(manifest_file, manifest, root=root_path)

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

        fs_source, source_path = fsspec.core.url_to_fs(source_directory)
        fs_target, target_path = fsspec.core.url_to_fs(target_directory)

        for file in diff['added'] + diff['changed']:
            source_file = f'{source_path}/{file}'
            target_file = f'{target_path}/{file}'
            fs_target.mkdirs(fs_target._parent(target_file), exist_ok=True)
            # Check if the file still exists before copying
            if not fs_source.exists(source_file):
                print(f'File {source_file} does not exist')
                continue

            with fs_source.open(source_file, 'rb') as src, fs_target.open(target_file, 'wb') as tgt:
                tgt.write(src.read())

        for file in diff['removed']:
            target_file = f'{target_path}/{file}'
            if fs_target.exists(target_file):
                fs_target.rm(target_file)

        # Regenerate the target manifest
        target_manifest.refresh()

    def refresh(self):
        """
        Regenerate the manifest
        """
        self.manifest = {}
        directory = self.root
        if directory is None:
            # Resolve the directory from the manifest file
            fs, path = fsspec.core.url_to_fs(self.manifest_file)  # noqa
            directory = fs._parent(path)  # noqa
        self.generate(directory=directory, manifest_file=self.manifest_file, root_path=self.root)

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
        with fsspec.open(output_patch_file, 'w') as f:
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
        fs, _ = fsspec.core.url_to_fs('')
        with fsspec.open(output_zip_file, 'wb') as zf:
            with zipfile.ZipFile(zf, 'w') as zipf:
                for file in diff['added'] + diff['changed']:
                    with fs.open(file, 'rb') as f:
                        zipf.writestr(file, f.read())
                # Create a '.manifestly.diff' of the diff contents
                with fsspec.open('.manifestly.diff', 'w') as f:
                    f.write(json.dumps(diff))

    @staticmethod
    def calculate_hash(file: OpenFile, algorithm=settings.DEFAULT_HASH_ALGORITHM):
        """
        Calculate the hash of a file
        :param file: The OpenFile object
        :param algorithm: The hash algorithm to use
        :return: The hash of the file
        """
        hasher = hashlib.new(algorithm)
        with file as f:
            while chunk := f.read(settings.CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()
