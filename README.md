# PDF Image Scraper

This project extracts embedded images from PDF files using PyMuPDF.

It is designed around a simple folder workflow:

- put one or more PDF files into `input/`
- run the script
- collect extracted images from `output/`

Each PDF gets its own subfolder inside `output/`, named after the source file.

<h3>How It Works</h3>

When you run the script, it will:

1. look for `.pdf` files inside `input/`
2. open each PDF and scan every page for embedded images
3. save extracted images into `output/<pdf-name>/`
4. skip invalid or password-protected PDFs without stopping the whole batch

<h3>Project Structure</h3>

```text
pdf-image-scraper/
├── input/
├── output/
├── main.py
├── requirements.txt
└── README.md
```

<h3>Requirements</h3>

- Python 3.10 or newer
- pip

<h3>Installation</h3>

Clone the repository and install the dependency:

```bash
pip install -r requirements.txt
```

<h3>Usage</h3>

1. Copy your PDF files into `input/`.
2. Run the script:

```bash
python main.py
```

3. Open `output/` to find the extracted images.

<h3>Output Layout</h3>

If you place a file named `report.pdf` inside `input/`, the output will look like this:

```text
output/
└── report/
	├── image_p1_1.png
	├── image_p1_2.jpeg
	└── image_p3_1.png
```

File names follow this pattern:

```text
image_p<page-number>_<image-number>.<extension>
```

<h3>Error Handling</h3>

The script handles a few common problems automatically:

- if `input/` does not exist, it reports the problem and stops
- if `input/` contains no PDFs, it exits cleanly
- if a PDF is invalid, empty, or unreadable, it is skipped
- if a PDF is password-protected, it is skipped
- if one PDF fails, the script continues processing the rest

<h3>Troubleshooting</h3>

### `ModuleNotFoundError: No module named 'frontend'`

This usually means Python is importing the wrong `fitz` package instead of PyMuPDF.

This project imports PyMuPDF through `pymupdf`, so installing from `requirements.txt` should be enough:

```bash
pip install -r requirements.txt
```

If your environment already has the unrelated `fitz` package installed, remove it:

```bash
python -m pip uninstall fitz
```

### No images were extracted

Some PDFs do not contain embedded images. In those cases, the script will still scan the file, but nothing will be written to the output folder.

<h3>Notes</h3>

- `input/` and `output/` contents are ignored by Git
- the script uses paths relative to the project folder, so you can run it from another working directory and it will still use this repository's `input/` and `output/` folders

<h3>License</h3>

This project is licensed under the terms in [LICENSE](LICENSE).
