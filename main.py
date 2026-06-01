"""Extract embedded images from PDF files placed in the project's input directory.

The script scans the input folder for PDF files, extracts any embedded images
from each document, and writes them into a dedicated output subdirectory named
after the source PDF. When a page contains multiple image fragments that belong
together, the script composes them into a single page-level image.
"""

from io import BytesIO
from pathlib import Path

import pymupdf as fitz
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent


def resolve_project_path(path_value: str | Path) -> Path:
    """Return an absolute path rooted at the project directory when needed.

    Args:
        path_value: A relative or absolute filesystem path.

    Returns:
        A resolved path. Relative values are interpreted from the directory that
        contains this script.
    """
    path = Path(path_value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def list_pdf_files(input_dir: Path) -> list[Path]:
    """Return all PDF files found in the provided input directory.

    Args:
        input_dir: Directory to scan for PDF files.

    Returns:
        A sorted list of PDF file paths.
    """
    return sorted(
        file_path for file_path in input_dir.iterdir() if file_path.suffix.lower() == ".pdf"
    )


def build_output_directory(output_dir: Path, pdf_path: Path) -> Path:
    """Return the destination directory for a PDF's extracted images.

    Args:
        output_dir: Root directory for all extraction output.
        pdf_path: Source PDF path.

    Returns:
        The subdirectory that should contain images extracted from the PDF.
    """
    return output_dir / pdf_path.stem


def build_image_path(output_dir: Path, page_number: int, image_number: int, extension: str) -> Path:
    """Build the output file path for an extracted image.

    Args:
        output_dir: Destination directory for the image file.
        page_number: One-based page number containing the image.
        image_number: One-based image number within the page.
        extension: File extension reported by PyMuPDF.

    Returns:
        The full path where the extracted image should be written.
    """
    image_name = f"image_p{page_number}_{image_number}.{extension}"
    return output_dir / image_name


def build_page_image_path(output_dir: Path, page_number: int) -> Path:
    """Build the output file path for a page-level composed image.

    Args:
        output_dir: Destination directory for the composed page image.
        page_number: One-based page number.

    Returns:
        The full path where the composed page image should be written.
    """
    return output_dir / f"image_p{page_number}.png"


def clear_generated_images(output_dir: Path) -> None:
    """Remove previously generated page image files from an output directory.

    Args:
        output_dir: Directory containing generated image files for a PDF.
    """
    if not output_dir.exists():
        return

    for file_path in output_dir.glob("image_p*"):
        if file_path.is_file():
            file_path.unlink()


def load_embedded_image(image_bytes: bytes) -> Image.Image:
    """Load embedded image bytes into a Pillow image.

    Args:
        image_bytes: Raw image bytes returned by PyMuPDF.

    Returns:
        A Pillow image converted to RGBA for consistent composition.
    """
    with Image.open(BytesIO(image_bytes)) as image:
        return image.convert("RGBA")


def compose_page_image(page: fitz.Page, image_list: list[tuple], pdf_document: fitz.Document) -> Image.Image:
    """Compose all embedded images on a page into a single canvas.

    Args:
        page: The PDF page being processed.
        image_list: Embedded image metadata returned by PyMuPDF.
        pdf_document: The open PDF document.

    Returns:
        A Pillow image containing all page images placed using their page positions.
    """
    scale = 2
    page_rect = page.rect
    canvas_width = max(1, int(round(page_rect.width * scale)))
    canvas_height = max(1, int(round(page_rect.height * scale)))
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))

    for image_info in image_list:
        xref = image_info[0]
        rects = page.get_image_rects(xref)

        if not rects:
            continue

        base_image = pdf_document.extract_image(xref)
        source_image = load_embedded_image(base_image["image"])

        for rect in rects:
            target_width = max(1, int(round(rect.width * scale)))
            target_height = max(1, int(round(rect.height * scale)))
            target_x = max(0, int(round(rect.x0 * scale)))
            target_y = max(0, int(round(rect.y0 * scale)))
            resized_image = source_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            canvas.alpha_composite(resized_image, dest=(target_x, target_y))

    return canvas


def write_page_output(
    pdf_document: fitz.Document,
    page_index: int,
    image_list: list[tuple],
    output_dir: Path,
) -> int:
    """Write the output artifact for a page.

    Args:
        pdf_document: The open PDF document.
        page_index: Zero-based page index.
        image_list: Embedded image metadata returned by PyMuPDF.
        output_dir: Destination directory for extracted output.

    Returns:
        The number of output files written for the page.
    """
    page_number = page_index + 1

    if len(image_list) == 1:
        xref = image_list[0][0]
        base_image = pdf_document.extract_image(xref)
        image_path = build_image_path(
            output_dir=output_dir,
            page_number=page_number,
            image_number=1,
            extension=base_image["ext"],
        )
        image_path.write_bytes(base_image["image"])
        return 1

    page = pdf_document[page_index]
    composed_image = compose_page_image(page, image_list, pdf_document)
    page_image_path = build_page_image_path(output_dir, page_number)
    composed_image.save(page_image_path, format="PNG")
    return 1


def extract_page_images(pdf_document: fitz.Document, page_index: int, output_dir: Path) -> int:
    """Extract page imagery from a single PDF page.

    Args:
        pdf_document: The open PDF document.
        page_index: Zero-based index of the page to inspect.
        output_dir: Destination directory for extracted images.

    Returns:
        The number of output files written for the requested page.
    """
    page = pdf_document[page_index]
    image_list = page.get_images(full=True)

    if image_list:
        print(f"Found {len(image_list)} image(s) on page {page_index + 1}")

    if not image_list:
        return 0

    return write_page_output(pdf_document, page_index, image_list, output_dir)


def extract_images_from_pdf(pdf_path: Path, output_dir: Path) -> int:
    """Extract page imagery from a single PDF file.

    Args:
        pdf_path: Path to the PDF file that should be processed.
        output_dir: Directory where extracted images should be stored.

    Returns:
        The total number of output files written for the PDF. Returns zero when
        the file is invalid, password-protected, or cannot be processed.
    """
    print(f"Analyzing '{pdf_path}'...")

    try:
        with fitz.open(pdf_path) as pdf_document:
            if pdf_document.needs_pass:
                print(f"Skipping password-protected PDF: '{pdf_path}'")
                return 0

            output_dir.mkdir(parents=True, exist_ok=True)
            clear_generated_images(output_dir)
            image_count = 0

            for page_index in range(len(pdf_document)):
                image_count += extract_page_images(pdf_document, page_index, output_dir)

        print(f"Wrote {image_count} output image file(s) to '{output_dir}'")
        return image_count
    except (fitz.FileDataError, fitz.EmptyFileError) as error:
        print(f"Skipping invalid PDF '{pdf_path}': {error}")
        return 0
    except Exception as error:
        print(f"Failed to process '{pdf_path}': {error}")
        return 0


def process_input_folder(input_dir: str | Path = "input", output_dir: str | Path = "output") -> int:
    """Process every PDF in the configured input directory.

    Args:
        input_dir: Folder containing source PDF files.
        output_dir: Root folder that should receive extracted images.

    Returns:
        The total number of images extracted across every processed PDF.
    """
    source_dir = resolve_project_path(input_dir)
    destination_dir = resolve_project_path(output_dir)

    if not source_dir.is_dir():
        print(f"Input folder not found: '{source_dir}'")
        return 0

    destination_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = list_pdf_files(source_dir)

    if not pdf_files:
        print(f"No PDF files found in '{source_dir}'")
        return 0

    total_images = 0

    for pdf_path in pdf_files:
        pdf_output_dir = build_output_directory(destination_dir, pdf_path)
        total_images += extract_images_from_pdf(pdf_path, pdf_output_dir)

    print(f"Processed {len(pdf_files)} PDF file(s) and wrote {total_images} output image file(s) in total.")
    return total_images


def main() -> int:
    """Run the default batch extraction workflow for the project.

    Returns:
        The total number of extracted images.
    """
    return process_input_folder()


if __name__ == "__main__":
    main()

