#!/usr/bin/env python3
"""
Generate sample PDF files demonstrating the expected format for seed_from_pdf.py.

Run:  python scripts/generate_sample_pdfs.py

Creates sample PDFs in  scripts/seed_pdfs/  that you can open, inspect, and
use as templates.  Replace the sample data with your real data and re-run
seed_from_pdf.py.

Requires: pip install fpdf2
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fpdf import FPDF
except ImportError:
    print("Install fpdf2 first:  pip install fpdf2")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _make_pdf(filename: str, title: str, headers: list[str],
              rows: list[list[str]]):
    """Create a single-page PDF with a table."""
    pdf = FPDF()
    pdf.add_page("L")  # landscape for wide tables
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(5)

    # Calculate column widths
    n = len(headers)
    page_w = pdf.w - 2 * pdf.l_margin
    col_w = page_w / n

    # Header row
    pdf.set_font("Helvetica", "B", 9)
    for h in headers:
        pdf.cell(col_w, 8, h, border=1, align="C")
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", "", 8)
    for row in rows:
        for i, cell in enumerate(row):
            pdf.cell(col_w, 7, str(cell), border=1)
        pdf.ln()

    path = os.path.join(OUTPUT_DIR, filename)
    pdf.output(path)
    print(f"  Created: {path}")


def main():
    print(f"Generating sample PDFs in {OUTPUT_DIR}/\n")

    # 1. college.pdf
    _make_pdf("college.pdf", "College Information",
              ["Name", "Affiliation", "City"],
              [["CVM University", "Gujarat Technological University (GTU)", "Anand"]])

    # 2. departments.pdf
    _make_pdf("departments.pdf", "Departments",
              ["Code", "Name"],
              [
                  ["CP",  "Computer Engineering"],
                  ["CSD", "Computer Science & Design"],
                  ["EC",  "Electronics & Communication Engineering"],
                  ["ME",  "Mechanical Engineering"],
                  ["CH",  "Chemical Engineering"],
              ])

    # 3. faculty.pdf  (sample — 3 faculty)
    _make_pdf("faculty.pdf", "Faculty",
              ["Department", "Name", "EmployeeID", "Email", "Phone",
               "Expertise", "MaxLoad", "PreferredTime", "Role"],
              [
                  ["CP", "Dr. Nilesh Patel", "CP001", "hod.cp@cvmu.edu.in",
                   "+919876500001", "AI, ML, DS", "12", "morning", "HOD"],
                  ["CP", "Dr. Rajesh Patel", "CP002", "rajesh.patel@cvmu.edu.in",
                   "+919876501001", "CN, OS", "24", "morning", "Faculty"],
                  ["CP", "Prof. Meena Shah", "CP003", "meena.shah@cvmu.edu.in",
                   "+919876501002", "DBMS, SE", "24", "morning", "Faculty"],
                  ["CSD", "Dr. Hiral Desai", "CSD001", "hod.csd@cvmu.edu.in",
                   "+919876500002", "HCI, UX, SE", "12", "morning", "HOD"],
                  ["CSD", "Prof. Jignesh Chauhan", "CSD002", "jignesh.chauhan@cvmu.edu.in",
                   "+919876502001", "DBMS, DS", "24", "morning", "Faculty"],
              ])

    # 4. subjects.pdf  (sample — common + department-specific)
    _make_pdf("subjects.pdf", "Subjects",
              ["Department", "Name", "Code", "Semester", "Credits",
               "LectureHours", "LabHours", "BatchSize"],
              [
                  # "Common" = added to all departments
                  ["Common", "Mathematics-I",               "00010100", "1", "4", "3", "0", "60"],
                  ["Common", "Physics",                     "00010200", "1", "4", "3", "2", "60"],
                  ["Common", "Chemistry",                   "00010300", "1", "4", "3", "2", "60"],
                  ["Common", "Engineering Graphics",        "00010400", "1", "3", "1", "2", "60"],
                  # Department-specific
                  ["CP",     "Data Structures",             "01030100", "3", "4", "3", "2", "60"],
                  ["CP",     "Digital Logic Design",        "01030200", "3", "4", "3", "2", "60"],
                  ["CP",     "Operating Systems",           "01040200", "4", "4", "3", "2", "60"],
                  ["CSD",    "Data Structures & Algorithms","02030100", "3", "4", "3", "2", "60"],
                  ["CSD",    "UI/UX Design Fundamentals",   "02030600", "3", "3", "2", "2", "60"],
              ])

    # 5. rooms.pdf
    _make_pdf("rooms.pdf", "Rooms & Labs",
              ["Name", "Capacity", "Type", "Projector", "Computers", "AC"],
              [
                  ["CP-01",          "80", "CLASSROOM", "Y", "N", "Y"],
                  ["CP-02",          "80", "CLASSROOM", "Y", "N", "Y"],
                  ["CP-03",          "60", "CLASSROOM", "Y", "N", "Y"],
                  ["Computer Lab 1", "40", "LAB",       "Y", "Y", "Y"],
                  ["Computer Lab 2", "40", "LAB",       "Y", "Y", "Y"],
                  ["Seminar Hall 1", "120","SEMINAR",   "Y", "N", "Y"],
              ])

    # 6. venues.pdf
    _make_pdf("venues.pdf", "Exam Venues",
              ["Name", "Capacity", "Type"],
              [
                  ["Main Examination Hall", "250", "HALL"],
                  ["Exam Hall A",           "120", "HALL"],
                  ["Exam Hall B",           "120", "HALL"],
              ])

    # 7. timeslots.pdf
    _make_pdf("timeslots.pdf", "Time Slots",
              ["Order", "Label", "StartTime", "EndTime", "Type"],
              [
                  ["1", "Period 1", "09:00", "10:00", "LECTURE"],
                  ["2", "Period 2", "10:00", "11:00", "LECTURE"],
                  ["3", "Period 3", "11:00", "12:00", "LECTURE"],
                  ["4", "Period 4", "12:00", "13:00", "LECTURE"],
                  ["5", "Lunch",    "13:00", "14:00", "BREAK"],
                  ["6", "Period 5", "14:00", "15:00", "LECTURE"],
                  ["7", "Period 6", "15:00", "16:00", "LECTURE"],
                  ["8", "Period 7", "16:00", "17:00", "LECTURE"],
              ])

    # 8. batches.pdf
    _make_pdf("batches.pdf", "Batches",
              ["Department", "Semester", "Name", "Size"],
              [
                  ["CP",  "1", "A", "20"],
                  ["CP",  "1", "B", "20"],
                  ["CP",  "1", "C", "20"],
                  ["CP",  "3", "A", "20"],
                  ["CP",  "3", "B", "20"],
                  ["CSD", "1", "A", "20"],
                  ["CSD", "1", "B", "20"],
                  ["CSD", "3", "A", "20"],
              ])

    print(f"\nDone! {8} sample PDFs created in {OUTPUT_DIR}/")
    print("Edit them with your real data, then run:")
    print("  python scripts/seed_from_pdf.py")


if __name__ == "__main__":
    main()
