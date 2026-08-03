"""Convert a PDF document to Markdown with MarkItDown."""

from argparse import ArgumentParser
from pathlib import Path

from markitdown import MarkItDown


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = PROJECT_ROOT / "resources" / "file1.pdf"


def read_pdf(pdf_path: Path) -> str:
    """Return the contents of a PDF as Markdown text."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, received: {pdf_path}")

    result = MarkItDown().convert(pdf_path)
    return result.text_content


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "pdf",
        nargs="?",
        type=Path,
        default=DEFAULT_PDF,
        help=f"PDF to read (default: {DEFAULT_PDF.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write the converted Markdown to this file instead of stdout.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown = read_pdf(args.pdf.expanduser())

    if args.output is None:
        print(markdown)
        return

    output_path = args.output.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Markdown written to {output_path}")


if __name__ == "__main__":
    main()
