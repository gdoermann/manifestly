"""
Manifestly CLI

Usage:
    manifestly generate <directory> [--hash-algorithm=<hash_algorithm>] [--output-file=<output_file>]
    manifestly sync <source_manifest> <target_manifest> <source_directory> <target_directory>
    manifestly compare <manifest1> <manifest2>
    manifestly patch <source_manifest> <target_manifest> <output_patch_file>
    manifestly pzip <source_manifest> <target_manifest> <output_zip_file>
"""
import click
import fsspec

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
    else:
        output_file = fsspec.open(output_file, 'w')
    Manifest.generate(directory, manifest_file=output_file, hash_algorithm=hash_algorithm)
    click.echo(f"Manifest saved to {output_file.path}")


@cli.command('changed')
@click.argument('manifest')
@click.option('--root', default=None)
def changed_cmd(manifest, root):
    """
    Print the files that have changed
    :param manifest: The manifest file
    :param root: The root directory
    """
    m = Manifest(manifest, root=root)
    _changed = m.changed()
    if not any(_changed.values()):
        click.echo('No files have changed')
        return
    click.echo('Changed files:')
    for category, files in _changed.items():
        if not files:
            continue
        click.echo(f"{category}:")
        for file in files:
            click.echo(f"  {file}")


@cli.command('refresh')
@click.argument('manifest')
@click.option('--root', default=None)
def refresh_cmd(manifest, root=None):
    """
    Refresh the manifest file
    :param manifest: The manifest file
    :param root: The root directory
    """
    m = Manifest(manifest, root=root)
    m.refresh()
    click.echo(f"Manifest refreshed")


@cli.command('sync')
@click.argument('source_manifest')
@click.argument('target_manifest')
@click.option('--refresh', is_flag=True, help="Refresh the source manifest first.", default=False)
@click.option('--dry-run', is_flag=True, help="Perform a dry run", default=False)
@click.option('--source_directory', default=None, help="The source directory")
@click.option('--target_directory', default=None, help="The target directory")
def sync_cmd(source_manifest, target_manifest, source_directory=None, target_directory=None, refresh=False,
             dry_run=False):
    """
    Sync two directories using manifest files
    :param source_manifest: Source manifest file
    :param target_manifest: Target manifest file
    :param source_directory: The source directory
    :param target_directory: The target directory
    :param refresh: Refresh the source manifest first
    :param dry_run: Perform a dry run
    """
    s_manifest = Manifest(source_manifest, root=source_directory)
    if refresh:
        s_manifest.refresh()
    t_manifest = Manifest(target_manifest, root=target_directory)
    s_manifest.sync(t_manifest, dry_run=dry_run)
    if dry_run:
        click.echo(f"Dry run completed for {source_directory} to {target_directory}")
    else:
        click.echo(f"Synced {s_manifest.root} with {t_manifest.root}")


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
    cli()  # pragma: no cover
