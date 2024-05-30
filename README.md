# Manifestly

**Manifestly** is a powerful Python package that generates a detailed manifest of a directory's contents, including file
paths and their hashes. It enables precise synchronization between two directories based on content, ensuring efficient
and accurate file management.

## Features

- **Generate Directory Manifest**: Create a JSON manifest file that lists all files in a directory with their
  corresponding hashes.
- **Content-Based Synchronization**: Compare manifests from different directories to synchronize files based on content
  differences.
- **Support for Large Directories**: Efficiently handle directories with a large number of files and varying sizes.
- **Customizable Hash Algorithms**: Choose from different hash algorithms (e.g., MD5, SHA256) to suit your needs.

## Installation

You can install Manifestly using pip:

```sh
pip install manifestly
```

## Usage

### Generate a Manifest

To generate a manifest for a directory:

```python
import manifestly

directory_to_scan = "path/to/your/directory"
output_file = ".manifestly.json"
manifest = manifestly.Manifest.generate(directory_to_scan, output_file)
manifest.save()
print(f"Manifest saved to {output_file}")
```

Or through the cli:

```bash
python -m manifestly.cli generate [--output-file .manifestly.json] path/to/your/directory
```

### Synchronize Directories

To synchronize local directories based on two manifest files:

```python
import manifestly

source_manifest_file = "source_manifest.json"
target_manifest_file = "target_manifest.json"
source_directory = "path/to/source/directory"
target_directory = "path/to/target/directory"

manifest = manifestly.Manifest(source_manifest_file)
manifest.sync(target_manifest_file, source_directory, target_directory)
```

Or through the cli:

```bash
python -m manifestly.cli sync [--refresh] source_manifest.json target_manifest.json [--source-directory path/to/source/directory] [--target-directory path/to/target/directory]
```

The `--refresh` flag will update the source manifest file before syncing.

If the target manifest does not exist, it will simply copy all files from the source directory to the target directory.

### Refreshing a Manifest

To refresh a manifest file:

```python
import manifestly

manifest_file = "manifest.json"
directory_to_scan = "path/to/your/directory"

manifest = manifestly.Manifest(manifest_file, root=directory_to_scan)
manifest.refresh()
```

Or through the cli:

```bash
python -m manifestly.cli refresh manifest.json [--root=path/to/your/directory]
```

The default root directory is the directory where the manifest file is located.

### Detecting Changes

If you have an existing manifest file and want to detect changes in the directory:

```python
import manifestly

manifest_file = "manifest.json"
directory_to_scan = "path/to/your/directory"

manifest = manifestly.Manifest(manifest_file, root=directory_to_scan)
changes = manifest.changed()
print(changes)
```

Or through the cli:

```bash
python -m manifestly.cli changed manifest.json [--root=path/to/your/directory]
```

The default root directory is the directory where the manifest file is located.

### Comparing Manifests

To compare two manifest files:

```python
import manifestly

source_manifest_file = "source_manifest.json"
target_manifest_file = "target_manifest.json"

source = manifestly.Manifest(source_manifest_file)

diff = source.diff(target_manifest_file)
print(diff)
```

Or through the cli:

```bash
python -m manifestly.cli compare source_manifest.json target_manifest.json
```

### Patching Directories

To create a patch file based on two manifest files:

```python
import manifestly

source_manifest_file = "source_manifest.json"
target_manifest_file = "target_manifest.json"
output_patch_file = "patch.json"

source = manifestly.Manifest(source_manifest_file)
source.patch(target_manifest_file, output_patch_file)
```

Or through the cli:

```bash
python -m manifestly.cli patch source_manifest.json target_manifest.json output.patch
```

### Creating a Zip File of Changed Files

Patch files work great for text only changes, but falls apart if you have any binary files. To create a zip file of
changed files based on two manifest files:

```python
import manifestly

source_manifest_file = "source_manifest.json"
target_manifest_file = "target_manifest.json"
output_zip_file = "changed_files.zip"

manifestly.pzip(source_manifest_file, target_manifest_file, output_zip_file)
```

Or through the cli:

```bash
python -m manifestly.cli pzip source_manifest.json target_manifest.json output.zip
```

The output zip file will contain the files that have changed between the two manifest files.
The order of manifest files matters. Files in the target manifest that have changed will be included in the zip file.
We also create the .manifestly.diff file that contains the json comparison of the two manifest files.
This diff is a dictionary with the keys `added`, `removed`, and `changed`. This can be used to determine what files
have changed (including what to remove if you are syncing directories).

### Remote Sync

Anywhere that you provide a local file path, you may also provide a remote path.
We use the `fsspec` library, so any path that `fsspec` supports, we support.
This includes S3, GCS, Azure, and more. For example, you can use the following paths:

```bash
s3://bucket/sync/prefix/.manifestly.json
gcs://bucket/sync/prefix/.manifestly.json
az://bucket/sync/prefix/.manifestly.json
```

You may need to install the appropriate library for the remote path you are using.  
For example, to use S3, you will need to install `s3fs`:

```bash
pip install s3fs
```

# Module Usage

Manifestly can also be run as a module from the command line. The following commands are available:

```bash
# Example usage
python -m manifestly.compare [OPTIONS] manifest1.json manifest2.json
python -m manifestly.generate [OPTIONS] path/to/directory
python -m manifestly.sync [OPTIONS] source_manifest.json target_manifest.json
python -m manifestly.patch [OPTIONS] source_manifest.json target_manifest.json output.patch
python -m manifestly.pzip [OPTIONS] source_manifest.json target_manifest.json output.zip

# S3 usage is the same but simply provide the S3 path instead of the local file path
python -m manifestly.compare [OPTIONS] local_manifest.json s3://bucket/sync/prefix/.manifestly.json
python -m manifestly.generate [OPTIONS] s3://bucket/sync/prefix
python -m manifestly.sync [OPTIONS] s3://bucket/sync/prefix/.manifestly.json local_manifest.json
python -m manifestly.sync [OPTIONS] local_manifest.json s3://bucket/sync/prefix/.manifestly.json
python -m manifestly.patch [OPTIONS] local_manifest.json s3://bucket/sync/prefix/.manifestly.json output.patch
python -m manifestly.pzip [OPTIONS] local_manifest.json s3://bucket/sync/prefix/.manifestly.json output.zip


Options:
    --hash-algorithm TEXT  The hash algorithm to use for file hashing.
    --name TEXT  The default manifest name.
    --exclude TEXT  Exclude files or directories based on patterns.
    --include TEXT  Include only files or directories based on patterns.
    --format TEXT  The format of the generated manifest file.
    --log-level TEXT  The logging level for detailed logging.
    
Common Command Options: (only applies for some commands)
    --target-directory TEXT  The target directory for the sync operation.
    --source-directory TEXT  The source directory for the sync operation.
```

# Script Usage

Manifestly provides a command-line interface for generating, comparing, and synchronizing manifests. You can use the
following commands:

```bash
Usage: manifestly [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.
  --version  Show the version and exit.
  --hash-algorithm TEXT  The hash algorithm to use for file hashing.
  --name TEXT  The default manifest name.
  --exclude TEXT  Exclude files or directories based on patterns.
  --include TEXT  Include only files or directories based on patterns.
  --format TEXT  The format of the generated manifest file.
  --log-level TEXT  The logging level for detailed logging.

Commands:
    compare  Compare two manifest files.
    generate  Generate a manifest for a directory.
    sync  Synchronize directories based on manifest files.
    patch Create a patch file based on two manifest files.
    pzip Create a zip file of changed files based on two manifest files.
  ```

# Customization

Manifestly provides several options for customizing the manifest generation process:

* **Hash Algorithm**: Choose from a variety of hash algorithms, such as MD5, SHA1, SHA256, and more.
* **Exclusion Patterns**: Exclude specific files or directories from the manifest based on patterns.
* **Include Patterns**: Include only specific files or directories in the manifest based on patterns.
* **Manifest Format**: Customize the format of the generated manifest file (e.g., JSON, YAML).
* **Manifest Output**: Specify the output location and format of the manifest file.
* **Logging**: Enable detailed logging to track the manifest generation process.

## Environment Variables

Manifestly supports the following environment variables for configuration:

* **MANIFESTLY_HASH_ALGORITHM**: Set the hash algorithm to use for file hashing (default is SHA256).
* **MANIFESTLY_NAME**: The default manifest name (default is `.manifestly.json`).
* **MANIFESTLY_CHUNK_SIZE**: The chunk size for reading files (default is 8192 bytes).

# Hash Algorithms

Algorithms supported by Python's hashlib module are available for use in Manifestly:

* **MD5**: MD5
* **SHA-1**: SHA1
* **SHA-224**: SHA224
* **SHA-256**: SHA256
* **SHA-384**: SHA384
* **SHA-512**: SHA512
* **SHA-3-224**: SHA3_224
* **SHA-3-256**: SHA3_256
* **SHA-3-384**: SHA3_384
* **SHA-3-512**: SHA3_512
* **SHAKE-128**: SHAKE_128
* **SHAKE-256**: SHAKE_256
* **BLAKE2b**: BLAKE2b
* **BLAKE2s**: BLAKE2s

# Ignore Files

Manifestly supports the use of `.manifestignore` files to exclude specific files or directories from the manifest.
The `.manifestignore` file should be placed in the root directory of the manifest and can contain patterns to match
files or directories to exclude. This file is tracked by default and will be included in the manifest/synchronized
when present.

# Contributing

We welcome contributions to Manifestly! If you would like to contribute, please fork the repository and submit a pull
request.

# License

Manifestly is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more information.

