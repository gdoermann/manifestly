"""
Manifestly is a Python library for generating, loading, comparing, and syncing file manifests.

This is the core module that provides the core functionality for generating, loading, comparing,
and syncing file manifests.
"""

import fnmatch
import hashlib
import json
from itertools import chain
from json import JSONDecodeError
from typing import Union

import fsspec
from fsspec.core import OpenFile

from manifestly import settings


class ManifestlyIgnore:
    """
    Handles a .manifestlyignore file that works like a .gitignore file
    You can specify files or directories to ignore.
    This loads the .manifestlyignore file and provides a method to check if a file should be ignored.
    """

    def __init__(self, ignore_file: Union[str, OpenFile]):
        if isinstance(ignore_file, str):
            ignore_file = fsspec.open(ignore_file, 'r')
        self.ignore_file = ignore_file
        self.ignore_patterns = self.load_ignore_patterns()

    def load_ignore_patterns(self):
        """
        Load the ignore patterns from the .manifestlyignore file
        """
        ignore = [settings.MANIFEST_NAME]
        try:
            with self.ignore_file.open() as f:
                return ignore + [self.normalize_path(p) for p in f.read().splitlines()]
        except FileNotFoundError:
            return ignore

    def should_ignore(self, file_path: str) -> bool:
        """
        Check if a file should be ignored.
        :param file_path: The path to the file.
        :return: True if the file should be ignored, False otherwise.
        """
        # Normalize the file path to always use forward slashes
        normalized_path = self.normalize_path(file_path)

        for pattern in self.ignore_patterns:
            _pattern = pattern.strip('/')

            if any(fnmatch.fnmatch(part, _pattern) for part in normalized_path.split('/')):
                return True

        return False

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize a path to always use forward slashes
        :param path: The path to normalize
        :return: The normalized path
        """
        return path.replace('\\', '/')

    def add_ignore_pattern(self, name: Union[str, OpenFile]):
        """
        Add an ignore pattern
        :param name: pattern to ignore
        """
        if isinstance(name, OpenFile):
            name = self.normalize_path(name.path).split('/')[-1]
        if name not in self.ignore_patterns:
            self.ignore_patterns.append(self.normalize_path(name))


class Manifest:
    """
    A class to represent a manifest
    """

    def __init__(self, manifest_file: Union[str, OpenFile], manifest: dict = None,
                 root: str = None, ignore: ManifestlyIgnore = None):
        if isinstance(manifest_file, str):
            manifest_file = fsspec.open(manifest_file)
        self.manifest_file: OpenFile = manifest_file
        self.manifest: dict = manifest
        self.root = root
        if self.manifest is None:
            self.load()
        if ignore is None:
            ignore = ManifestlyIgnore(self.default_ignore_file(self.root))
        self.ignore = ignore

    def _reopen(self, mode='r'):
        return fsspec.open(self.manifest_file.path, mode)

    def save(self):
        """
        Save the manifest to a file
        :param file_path: The path to the manifest file
        """
        _file = self._reopen('w')
        # Make sure directories exist
        _file.fs.makedirs(_file.fs._parent(_file.path), exist_ok=True)

        with _file.open() as f:
            f.seek(0)
            json.dump(self.manifest, f, indent=2)

    def items(self):
        """
        Get the items in the manifest
        :return:
        """
        return self.manifest.items()

    def keys(self):
        """
        Get the keys in the manifest
        :return:
        """
        return self.manifest.keys()

    def values(self):
        """
        Get the values in the manifest
        :return:
        """
        return self.manifest.values()

    def __eq__(self, other):
        """
        Check if the manifest is equal to another manifest
        :param other: The other manifest
        :return: True if the manifests are equal, False otherwise
        """
        if not isinstance(other, Manifest):
            return False
        return self.manifest == other.manifest

    def __contains__(self, item):
        """
        Check if the manifest contains a file
        :param item: The file to check
        :return: True if the file is in the manifest, False otherwise
        """
        return item in self.manifest

    def load(self):
        """
        Load a manifest from a file
        :return: The loaded manifest
        """
        try:
            with self._reopen() as f:
                _data = f.read()
                if not _data:
                    self.manifest = {}
                else:
                    self.manifest = json.loads(_data)
        except FileNotFoundError:
            self.manifest = {}
            self.save()
        except IsADirectoryError:
            # The manifest file is a directory, so we need to append the default manifest file name
            self.root = self.manifest_file
            self.manifest_file = self.default_manifest_file(self.manifest_file)
            self.load()
        except JSONDecodeError:
            self.manifest = {}
        if self.root is None:
            # Resolve the root path from the manifest file
            fs, path = fsspec.core.url_to_fs(self.manifest_file.path)
            self.root = fs._parent(path)

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
    def default_ignore_file(cls, directory: Union[str, OpenFile]) -> OpenFile:
        """
        Get the default manifest file for a directory.
        The directory must be a string or an fsspec.core.OpenFile object.

        :param directory: The directory
        :return: The path to the manifest file
        """
        fs, path = fsspec.core.url_to_fs(directory)
        manifest_path = fs.sep.join([path.rstrip(fs.sep), settings.MANIFESTLY_IGNORE])
        return fsspec.open(manifest_path, 'r')

    @classmethod
    def generate(cls, directory, manifest_file: Union[str, OpenFile] = None, root_path: str = None,
                 hash_algorithm=settings.DEFAULT_HASH_ALGORITHM, ignore: ManifestlyIgnore = None) -> 'Manifest':
        """
        Generate a manifest for a directory
        :param directory: The directory to generate the manifest for
        :param manifest_file: Optional path to the manifest file
        :param root_path: The root path to use (all paths will be relative to this)
        :param hash_algorithm: Hash algorithm to use
        :param ignore: The ignore file
        :return: The generated manifest
        """
        manifest = {}
        fs, path = fsspec.core.url_to_fs(directory)
        if root_path is None:
            root_path = path
        elif isinstance(root_path, OpenFile):
            root_path = root_path.path

        # Load the ignore file if it exists
        if ignore is None:
            ignore = ManifestlyIgnore(cls.default_ignore_file(directory))
        ignore.add_ignore_pattern(settings.MANIFEST_NAME)
        if manifest_file:
            if isinstance(manifest_file, OpenFile):
                _ignore_file = manifest_file.path
            else:
                _ignore_file = manifest_file
            _ignore_file = _ignore_file.split('/')[-1].split('\\')[-1]
            ignore.add_ignore_pattern(_ignore_file)

        for file_path in fs.find(path):
            if fs.isfile(file_path):
                # Check ignore patterns
                if ignore.should_ignore(file_path):
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
        return cls(manifest_file, manifest, root=root_path, ignore=ignore)

    def changed(self) -> dict:
        """
        Get the files that have changed
        This returns a dictionary of added, removed, and changed files
        :return: Dictionary of changed files
        """
        self.load()
        fs, path = fsspec.core.url_to_fs(self.root)
        changed = {
            'added': {},
            'removed': {},
            'changed': {}
        }
        for file, _hash in self.manifest.items():
            file_path = f'{path}/{file}'
            if not fs.exists(file_path):
                changed['removed'][file] = _hash
                continue
            _new_hash = self.calculate_hash(fs.open(file_path))
            if _hash != _new_hash:
                changed['changed'][file] = _new_hash
        for file in fs.find(path):
            if self.ignore.should_ignore(file):
                continue
            relative_path = file[len(path):].lstrip('/')
            if relative_path not in self.manifest:
                changed['added'][relative_path] = self.calculate_hash(fs.open(file))
        return changed

    def sync(self, target_manifest, dry_run=False) -> 'Manifest':
        """
        Sync the target directory to match the source manifest
        :param target_manifest: The path to the target manifest file or a Manifest object
        :param dry_run: Perform a dry run
        """
        if isinstance(target_manifest, str):
            target_manifest = Manifest(target_manifest)
        diff = self.diff(target_manifest)

        fs_source, source_path = fsspec.core.url_to_fs(self.root)
        fs_target, target_path = fsspec.core.url_to_fs(target_manifest.root)

        for file in chain(diff['added'].keys(), diff['changed'].keys()):
            source_file = f'{source_path}/{file}'
            target_file = f'{target_path}/{file}'
            fs_target.mkdirs(fs_target._parent(target_file), exist_ok=True)
            # Check if the file still exists before copying
            if not fs_source.exists(source_file):
                print(f'File {source_file} does not exist')
                continue

            if dry_run:
                print(f'Copy {source_file} to {target_file}')
                continue
            with fs_source.open(source_file, 'rb') as src, fs_target.open(target_file, 'wb') as tgt:
                tgt.write(src.read())

        for file in diff['removed']:
            target_file = f'{target_path}/{file}'
            if fs_target.exists(target_file):
                if dry_run:
                    print(f'Remove {target_file}')
                    continue
                fs_target.rm(target_file)

        if not dry_run:
            # Regenerate the target manifest
            target_manifest.refresh()
        return target_manifest

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
        _m = self.generate(directory=directory, manifest_file=self.manifest_file, root_path=self.root,
                           ignore=self.ignore)
        self.manifest = _m.manifest

    def diff(self, target_manifest) -> dict:
        """
        Compare the manifest with another manifest
        :param target_manifest: The path to the target manifest file or a Manifest object
        :return: A dictionary with the differences
        """
        if not isinstance(target_manifest, Manifest):
            target_manifest = Manifest(target_manifest)
        diff = {
            'added': {},
            'removed': {},
            'changed': {}
        }
        for file, _hash in self.items():
            if file not in target_manifest.manifest:
                diff['added'][file] = _hash
            elif target_manifest.manifest[file] != _hash:
                diff['changed'][file] = _hash
        for file, _hash in target_manifest.items():
            if file not in self.manifest:
                diff['removed'][file] = _hash
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
            json.dump(diff, f, indent=2)
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
                for file in chain(diff['added'].keys(), diff['changed'].keys()):
                    # resolve the full path from the root
                    _fpath = f'{self.root}/{file}'
                    with fs.open(_fpath, 'rb') as f:
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
