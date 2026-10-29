import sys
from pathlib import Path

import pdfplumber
from docx import Document


def read_pdf(path: Path) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # layout=True keeps a gap between columns, so two-column
            # resumes don't get their left and right sides mixed up
            text = page.extract_text(layout=True) or ""
            pages.append(text)
    return "\n".join(pages)


def read_docx(path: Path) -> str:
    doc = Document(path)
    lines = []

    # Read paragraphs AND tables in the order they appear on the page.
    # Many resumes use a table for their layout (e.g. two columns).
    for block in doc.iter_inner_content():
        if hasattr(block, "rows"):  # it's a table
            for row in block.rows:
                last = None
                for cell in row.cells:
                    # merged cells show up more than once — keep just one copy
                    if cell.text != last:
                        lines.append(cell.text)
                    last = cell.text
        else:  # it's a normal paragraph
            lines.append(block.text)

    return "\n".join(lines)


def read_resume(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        text = read_pdf(path)
    elif ext == ".docx":
        text = read_docx(path)
    else:
        raise ValueError(f"Only PDF or DOCX supported, got: {ext}")

    # Clean up: drop blank lines and trailing spaces
    clean = "\n".join(line.rstrip() for line in text.splitlines() if line.strip())

    if not clean:
        raise ValueError(
            "No text found. File may be a scanned image — needs OCR, not supported yet."
        )
    return clean


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python read_file.py <resume.pdf|resume.docx>")
        sys.exit(1)

    text = read_resume(sys.argv[1])
    print(text)
    print(f"\n--- {len(text)} characters extracted ---")
