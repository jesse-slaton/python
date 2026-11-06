"""Command-line interface for update-catalog-fetcher."""

import argparse
import sys
from pathlib import Path

from .catalog_client import UpdateCatalogClient
from .metadata_generator import MetadataGenerator
from .script_generator import PowerShellScriptGenerator


def progress_callback(downloaded: int, total: int) -> None:
    """Progress callback for downloads."""
    if total > 0:
        percent = (downloaded / total) * 100
        print(f"\rDownloading: {percent:.1f}% ({downloaded}/{total} bytes)", end="")
    else:
        print(f"\rDownloading: {downloaded} bytes", end="")


def main() -> int:  # noqa: PLR0911, PLR0912, PLR0915  CLI entry point; splitting main() is a refactor deferred to burn-down
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch Windows updates from Microsoft Update Catalog and generate Tanium Deploy packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch a specific KB for Windows 10 x64
  %(prog)s --kb KB5034441 --os "Windows 10" --arch x64

  # Fetch a KB for Windows 11
  %(prog)s --kb 5034441 --os "Windows 11" --arch x64 --output ./packages

  # Fetch for Windows Server 2022
  %(prog)s --kb KB5034129 --os "Windows Server 2022" --arch x64

  # Specify OS requirements for Tanium Deploy
  %(prog)s --kb KB5034441 --os "Windows 10" --arch x64 \\
           --os-edition-id Professional \\
           --os-product-name "Windows 10 Pro" \\
           --os-build 19045
        """,
    )

    parser.add_argument(
        "--kb",
        required=True,
        help="KB number to fetch (e.g., KB5034441 or 5034441)",
    )

    parser.add_argument(
        "--os",
        help='Operating system filter (e.g., "Windows 10", "Windows 11", "Windows Server 2022")',
    )

    parser.add_argument(
        "--arch",
        choices=["x64", "x86", "ARM64"],
        default="x64",
        help="Architecture filter (default: x64)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory for generated package (default: current directory)",
    )

    parser.add_argument(
        "--os-edition-id",
        help="Windows Edition ID for OS requirements (e.g., Professional, Enterprise)",
    )

    parser.add_argument(
        "--os-product-name",
        help="Windows Product Name for OS requirements (e.g., 'Windows 10 Pro')",
    )

    parser.add_argument(
        "--os-build",
        help="Windows Build number for OS requirements (e.g., 19045, 22631)",
    )

    parser.add_argument(
        "--allow-restart",
        action="store_true",
        help="Allow automatic restart after installation (default: disabled)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Use verbose installation instead of quiet (default: quiet)",
    )

    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list matching updates without downloading",
    )

    parser.add_argument(
        "--select",
        type=int,
        default=0,
        help="Select specific update by index if multiple matches (default: first match)",
    )

    args = parser.parse_args()

    try:
        # Initialize client
        print(f"Searching for {args.kb}...")
        client = UpdateCatalogClient()

        # Search for updates
        updates = list(
            client.search(
                kb=args.kb,
                os_filter=args.os,
                arch_filter=args.arch,
            )
        )

        if not updates:
            print(f"Error: No updates found for KB {args.kb}")
            if args.os:
                print(f"  OS Filter: {args.os}")
            if args.arch:
                print(f"  Architecture: {args.arch}")
            return 1

        print(f"\nFound {len(updates)} update(s):")
        for i, update in enumerate(updates):
            print(f"\n[{i}] {update.title}")
            print(f"    KB: {update.kb}")
            print(f"    Products: {update.products}")
            print(f"    Architecture: {update.architecture or 'Unknown'}")
            print(f"    Size: {update.size}")
            print(f"    Date: {update.last_updated.strftime('%Y-%m-%d')}")

        if args.list_only:
            return 0

        # Select update
        if args.select >= len(updates):
            print(f"\nError: Invalid selection {args.select}. Only {len(updates)} update(s) found.")
            return 1

        selected_update = updates[args.select]
        print(f"\nSelected: {selected_update.title}")

        # Create output directory
        kb_safe = args.kb.upper().replace("KB", "")
        package_dir = args.output / f"KB{kb_safe}"
        package_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nOutput directory: {package_dir}")

        # Get download URL
        print("\nRetrieving download URL...")
        download_url = client.get_download_url(selected_update.update_id)

        if not download_url:
            print("Error: Could not retrieve download URL")
            return 1

        selected_update.download_url = download_url
        print(f"Download URL: {download_url}")

        # Determine file extension from URL
        url_lower = download_url.lower()
        if ".msu" in url_lower:
            file_ext = ".msu"
        elif ".cab" in url_lower:
            file_ext = ".cab"
        elif ".exe" in url_lower:
            file_ext = ".exe"
        else:
            file_ext = ".bin"

        # Download update
        update_file_name = f"{args.os or 'windows'}-KB{kb_safe}-{args.arch}{file_ext}".replace(
            " ", "-"
        ).lower()
        update_file_path = package_dir / update_file_name

        print(f"\nDownloading to: {update_file_name}")
        client.download_update(
            selected_update,
            str(update_file_path),
            progress_callback=progress_callback,
        )
        print("\nDownload complete!")

        # Generate install script
        print("\nGenerating install script...")
        install_script_name = f"Install-KB{kb_safe}.ps1"
        install_script = PowerShellScriptGenerator.generate_install_script(
            selected_update,
            update_file_name,
            quiet=not args.verbose,
            no_restart=not args.allow_restart,
        )
        PowerShellScriptGenerator.save_script(
            install_script,
            package_dir / install_script_name,
        )
        print(f"Created: {install_script_name}")

        # Generate remove script
        print("Generating remove script...")
        remove_script_name = f"Remove-KB{kb_safe}.ps1"
        remove_script = PowerShellScriptGenerator.generate_remove_script(
            selected_update,
            quiet=not args.verbose,
            no_restart=not args.allow_restart,
        )
        PowerShellScriptGenerator.save_script(
            remove_script,
            package_dir / remove_script_name,
        )
        print(f"Created: {remove_script_name}")

        # Generate metadata
        print("Generating Tanium Deploy metadata...")
        metadata_file_name = "tanium-deploy-metadata.json"
        metadata = MetadataGenerator.generate_metadata(
            selected_update,
            install_script_name,
            remove_script_name,
            update_file_name,
            os_edition_id=args.os_edition_id,
            os_product_name=args.os_product_name,
            os_build=args.os_build,
        )
        MetadataGenerator.save_metadata(
            metadata,
            package_dir / metadata_file_name,
        )
        print(f"Created: {metadata_file_name}")

        # Generate README
        print("Generating README...")
        readme_content = MetadataGenerator.generate_readme(
            selected_update,
            update_file_name,
            install_script_name,
            remove_script_name,
            metadata_file_name,
        )
        readme_path = package_dir / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:  # noqa: PTH123  open() is fine here; Path migration is a refactor deferred to burn-down
            f.write(readme_content)
        print("Created: README.md")

        print(f"\n{'=' * 60}")
        print("Package created successfully!")
        print(f"Location: {package_dir}")
        print(f"{'=' * 60}")
        print("\nPackage contents:")
        for item in sorted(package_dir.iterdir()):
            size = item.stat().st_size
            size_str = f"{size:,} bytes" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            print(f"  - {item.name} ({size_str})")

        print("\nNext steps:")
        print("1. Review the generated scripts and metadata")
        print("2. Upload the entire package directory to Tanium Deploy")
        print("3. Configure install/remove operations using the generated scripts")
        print("4. Import metadata from tanium-deploy-metadata.json")

        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback  # noqa: PLC0415  deferred import limits traceback import to the error path

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
