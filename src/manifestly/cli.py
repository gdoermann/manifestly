"""
Manifestly CLI

Usage:
    manifestly generate <directory> [--hash-algorithm=<hash_algorithm>] [--output-file=<output_file>]
    manifestly sync <source_manifest> <target_manifest> <source_directory> <target_directory>
    manifestly compare <manifest1> <manifest2>
    manifestly patch <source_manifest> <target_manifest> <output_patch_file>
    manifestly pzip <source_manifest> <target_manifest> <output_zip_file>
"""
import pathlib

import click

from .core import Manifest


@click.group()
def cli():
    """
    Manifestly CLI
    :return:
    """
    pass


@cli.command('generate')
@click.argument('directory')
@click.option('--hash-algorithm', default='sha256')
@click.option('--output-file', default=None)
def generate_cmd(directory, hash_algorithm, output_file):
    """
    Generate a manifest file
    :param directory: The directory to generate the manifest for
    :param hash_algorithm: The hash algorithm to use
    :param output_file: The output file
    """
    if output_file is None:
        output_file = Manifest.default_manifest_file(directory)
    Manifest.generate(directory, manifest_file=output_file, hash_algorithm=hash_algorithm)
    click.echo(f"Manifest saved to {output_file.path}")


@cli.command('sync')
@click.argument('source_manifest')
@click.argument('target_manifest')
@click.option('--refresh', is_flag=True, help="Refresh the source manifest first.", default=False)
@click.option('--source_directory', default=None, help="The source directory")
@click.option('--target_directory', default=None, help="The target directory")
def sync_cmd(source_manifest, target_manifest, source_directory=None, target_directory=None, refresh=False):
    """
    Sync two directories using manifest files
    :param source_manifest: Source manifest file
    :param target_manifest: Target manifest file
    :param source_directory: The source directory
    :param target_directory: The target directory
    :param refresh: Refresh the source manifest first
    """
    if source_directory is None:
        source_directory = pathlib.Path(source_manifest).parent
    if target_directory is None:
        target_directory = pathlib.Path(target_manifest).parent
    s_manifest = Manifest(source_manifest)
    if refresh:
        s_manifest.refresh()
    s_manifest.sync(target_manifest, source_directory, target_directory)
    click.echo(f"Synced {source_directory} with {target_directory}")


@cli.command('compare')
@click.argument('source_manifest')
@click.argument('target_manifest')
def compare_cmd(source_manifest, target_manifest):
    """
    Compare two manifest files and print the diff
    :param source_manifest: The source manifest file
    :param target_manifest: The target manifest file
    """
    s_manifest = Manifest(source_manifest)
    diff = s_manifest.diff(target_manifest)
    click.echo(diff)


@cli.command('patch')
@click.argument('source_manifest')
@click.argument('target_manifest')
@click.argument('output_patch_file')
def patch_cmd(source_manifest, target_manifest, output_patch_file):
    """
    Generate a patch file
    :param source_manifest: The source manifest file
    :param target_manifest:  The target manifest file
    :param output_patch_file: The output patch file
    :return:
    """
    s_manifest = Manifest(source_manifest)
    s_manifest.patch(target_manifest, output_patch_file)
    click.echo(f"Patch saved to {output_patch_file}")


@cli.command('pzip')
@click.argument('source_manifest')
@click.argument('target_manifest')
@click.argument('output_zip_file')
def pzip_cmd(source_manifest, target_manifest, output_zip_file):
    """
    Generate a zip file with the differences
    :param source_manifest: The source manifest file
    :param target_manifest: The target manifest file
    :param output_zip_file: Path to the output zip file
    """
    s_manifest = Manifest(source_manifest)
    s_manifest.pzip(target_manifest, output_zip_file)
    click.echo(f"Zip file saved to {output_zip_file}")


if __name__ == '__main__':
    cli()
