# Seeding from PDF Files

Instead of hardcoding data in `seed.py`, you can provide your college data via **multiple PDF files** — one per entity type.

## Quick Start

```bash
# 1. Install dependencies
pip install pdfplumber fpdf2

# 2. Generate sample PDFs to see the expected format
python scripts/generate_sample_pdfs.py

# 3. Replace sample data in scripts/seed_pdfs/ with your real PDFs

# 4. Seed the database
python scripts/seed_from_pdf.py                        # default folder: scripts/seed_pdfs/
python scripts/seed_from_pdf.py /path/to/your/pdfs     # custom folder
```

## Expected PDF Files

Place all PDFs in one folder. Each file must have **tables with header rows**. The script ignores non-table content (paragraphs, images, etc.).

| File | Description | Required Columns |
|------|-------------|-----------------|
| `college.pdf` | College info (1 row) | Name, Affiliation, City |
| `departments.pdf` | Department list | Code, Name |
| `faculty.pdf` | All faculty incl. HODs | Department, Name, EmployeeID, Email, Phone, Expertise, MaxLoad, PreferredTime, Role |
| `subjects.pdf` | All subjects | Department, Name, Code, Semester, Credits, LectureHours, LabHours, BatchSize |
| `rooms.pdf` | Classrooms, labs, seminar halls | Name, Capacity, Type, Projector, Computers, AC |
| `venues.pdf` | Exam venues | Name, Capacity, Type |
| `timeslots.pdf` | Period configuration | Order, Label, StartTime, EndTime, Type |
| `batches.pdf` | Student batches | Department, Semester, Name, Size |

**All files are optional** — only present PDFs are processed.

## Column Name Flexibility

Column headers are matched **flexibly** (case-insensitive, ignoring spaces/underscores). Examples:

| You write | Recognized as |
|-----------|--------------|
| `Employee ID` | `employeeid` |
| `employee_id` | `employeeid` |
| `Emp ID` | `employeeid` |
| `Lecture Hours` | `lecturehours` |
| `Lec` | `lecturehours` |
| `Lab` | `labhours` |
| `Sem` | `semester` |

See [`pdf_parser.py`](pdf_parser.py) for the full alias list.

## Data Format Rules

### faculty.pdf
- **Department**: Must match a code from `departments.pdf` (e.g., `CP`, `CSD`)
- **Expertise**: Comma-separated list (e.g., `AI, ML, DS`)
- **Role**: `HOD` or `Faculty` (HODs get `DEPT_ADMIN` role, default password `hod123`; faculty get password `faculty123`)
- **PreferredTime**: `morning`, `afternoon`, or `any`

### subjects.pdf
- **Department**: Use department code. Use `Common` or `All` for subjects shared across all departments (e.g., Sem 1-2 common subjects)
- **Code**: 8-digit format `BBSSNNVV` where BB=branch, SS=semester, NN=serial, VV=variant
- **LectureHours / LabHours**: Integer (weekly hours)

### rooms.pdf
- **Type**: `CLASSROOM`, `LAB`, or `SEMINAR`
- **Projector / Computers / AC**: `Y` or `N`

### venues.pdf
- **Type**: `HALL`, `LAB`, or `OUTDOOR`

### timeslots.pdf
- **Type**: `LECTURE`, `LAB`, or `BREAK`
- **StartTime / EndTime**: `HH:MM` format (e.g., `09:00`)

### batches.pdf
- **Department**: Must match a code from `departments.pdf`
- **Semester**: Integer 1–8
- **Name**: Batch label (e.g., `A`, `B`, `C`)

## How to Create Your PDFs

You can create the PDFs using **any tool** that produces tables:

1. **Google Docs / Microsoft Word** — Insert a table, fill data, export as PDF
2. **Google Sheets / Excel** — Create a spreadsheet with headers in row 1, data below, export/print as PDF
3. **LibreOffice Calc** — Same as above
4. **Python (fpdf2)** — Run `python scripts/generate_sample_pdfs.py` for reference

> **Tip**: The simplest method is to create tables in **Google Sheets or Excel** and export each sheet as a separate PDF file.

## Multi-Page PDFs

If your data spans multiple pages (e.g., hundreds of subjects), that's fine — the parser reads tables across **all pages** of each PDF.
