# scripts/seed.py
"""
Seed the database with comprehensive demo data for CVM University (Anand, Gujarat).

Departments : CP, CSD, EC, ME, CH
Semesters   : 1–8 (common first year + branch-specific 3–8)
Faculty     : ~60 (HODs + regular, all with user accounts)
Subjects    : ~230+ (all semesters incl. open & program electives)
Rooms       : 35 classrooms (7/dept) + 50 labs + 3 seminar halls
Exam Venues : 4
Batches     : A, B, C per dept per semester (20 students each)
Time Slots  : 7 lecture periods + 5-min breaks between + lunch

Usage: python scripts/seed.py
"""
import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, AsyncSessionLocal
from models.college import College, Department
from models.user import User, UserRole
from models.faculty import Faculty
from models.subject import Subject
from models.room import Room, RoomType, Venue, VenueType
from models.timeslot import TimeSlotConfig, SlotType
from models.batch import Batch
from utils.security import hash_password


def _id():
    return str(uuid.uuid4())


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            print("Delete timetable_dev.db and re-run to reseed.")
            return

        # ════════════════════════════════════════════════════════
        # COLLEGE
        # ════════════════════════════════════════════════════════
        college_id = _id()
        db.add(College(
            college_id=college_id,
            name="CVM University",
            affiliation="Gujarat Technological University (GTU)",
            city="Anand",
        ))

        # ════════════════════════════════════════════════════════
        # DEPARTMENTS
        # ════════════════════════════════════════════════════════
        departments = {
            "CP":  ("Computer Engineering", _id()),
            "CSD": ("Computer Science & Design", _id()),
            "EC":  ("Electronics & Communication Engineering", _id()),
            "ME":  ("Mechanical Engineering", _id()),
            "CH":  ("Chemical Engineering", _id()),
        }
        for code, (name, dept_id) in departments.items():
            db.add(Department(
                dept_id=dept_id,
                college_id=college_id,
                name=name,
                code=code,
            ))

        # ════════════════════════════════════════════════════════
        # SUPER ADMIN
        # ════════════════════════════════════════════════════════
        db.add(User(
            user_id=_id(),
            email="admin@cvmu.edu.in",
            phone="+919876500000",
            hashed_password=hash_password("admin123"),
            full_name="Dr. Mahesh Parmar",
            role=UserRole.SUPER_ADMIN,
            college_id=college_id,
            dept_id=None,
        ))

        # ════════════════════════════════════════════════════════
        # HODs  (dept_admin user + faculty profile)
        # ════════════════════════════════════════════════════════
        hod_data = {
            "CP":  ("Dr. Nilesh Patel",    "hod.cp@cvmu.edu.in",  "+919876500001", "CP001",  ["AI", "ML", "DS"],       "morning"),
            "CSD": ("Dr. Hiral Desai",     "hod.csd@cvmu.edu.in", "+919876500002", "CSD001", ["HCI", "UX", "SE"],      "morning"),
            "EC":  ("Dr. Suresh Joshi",    "hod.ec@cvmu.edu.in",  "+919876500003", "EC001",  ["VLSI", "ES", "DSP"],    "morning"),
            "ME":  ("Dr. Jagdish Shah",    "hod.me@cvmu.edu.in",  "+919876500004", "ME001",  ["TOM", "DOM", "MD"],     "morning"),
            "CH":  ("Dr. Kavita Raval",    "hod.ch@cvmu.edu.in",  "+919876500005", "CH001",  ["CRE", "MTO", "PCT"],    "morning"),
        }
        for code, (name, email, phone, emp_id, expertise, pref) in hod_data.items():
            uid, fid = _id(), _id()
            dept_id = departments[code][1]
            db.add(User(
                user_id=uid, email=email, phone=phone,
                hashed_password=hash_password("hod123"),
                full_name=name, role=UserRole.DEPT_ADMIN,
                college_id=college_id, dept_id=dept_id,
            ))
            db.add(Faculty(
                faculty_id=fid, dept_id=dept_id, user_id=uid,
                name=name, employee_id=emp_id, expertise=expertise,
                max_weekly_load=12, preferred_time=pref,
            ))

        # ════════════════════════════════════════════════════════
        # FACULTY  (user + faculty profile per member)
        # ════════════════════════════════════════════════════════
        faculty_by_dept = {
            "CP": [
                ("Dr. Rajesh Patel",       "CP002", "rajesh.patel@cvmu.edu.in",      "+919876501001", ["CN", "OS"],              24, "morning"),
                ("Prof. Meena Shah",       "CP003", "meena.shah@cvmu.edu.in",        "+919876501002", ["DBMS", "SE"],            24, "morning"),
                ("Dr. Amit Desai",         "CP004", "amit.desai@cvmu.edu.in",        "+919876501003", ["DAA", "TOC"],            24, "afternoon"),
                ("Prof. Priya Joshi",      "CP005", "priya.joshi@cvmu.edu.in",       "+919876501004", ["WT", "CN"],              24, "any"),
                ("Dr. Kiran Mehta",        "CP006", "kiran.mehta@cvmu.edu.in",       "+919876501005", ["OS", "DAA"],             24, "morning"),
                ("Prof. Sneha Trivedi",    "CP007", "sneha.trivedi@cvmu.edu.in",     "+919876501006", ["SE", "DBMS", "WT"],      24, "afternoon"),
                ("Prof. Vaishali Parikh",  "CP008", "vaishali.parikh@cvmu.edu.in",   "+919876501007", ["DS", "OOP", "DM"],       24, "morning"),
                ("Dr. Hiren Gandhi",       "CP009", "hiren.gandhi@cvmu.edu.in",      "+919876501008", ["CC", "IoT", "CO"],       24, "afternoon"),
                ("Prof. Ruchi Kothari",    "CP010", "ruchi.kothari@cvmu.edu.in",     "+919876501009", ["CD", "OS", "DLD"],       24, "any"),
                ("Dr. Pranav Solanki",     "CP011", "pranav.solanki@cvmu.edu.in",    "+919876501010", ["AI", "ML", "BDA"],       24, "morning"),
                ("Prof. Nidhi Thaker",     "CP012", "nidhi.thaker@cvmu.edu.in",      "+919876501011", ["IS", "BC", "CC"],        24, "afternoon"),
                ("Prof. Sameer Vora",      "CP013", "sameer.vora@cvmu.edu.in",       "+919876501012", ["MP", "COA", "ES"],       24, "morning"),
            ],
            "CSD": [
                ("Prof. Jignesh Chauhan",  "CSD002", "jignesh.chauhan@cvmu.edu.in",  "+919876502001", ["DBMS", "DS"],            24, "morning"),
                ("Dr. Pooja Sharma",       "CSD003", "pooja.sharma@cvmu.edu.in",     "+919876502002", ["CN", "IS"],              24, "morning"),
                ("Prof. Rakesh Thakkar",   "CSD004", "rakesh.thakkar@cvmu.edu.in",   "+919876502003", ["OOP", "HCI"],            24, "afternoon"),
                ("Dr. Dipti Mistry",       "CSD005", "dipti.mistry@cvmu.edu.in",     "+919876502004", ["AI", "ML", "DM"],        24, "any"),
                ("Prof. Bharat Panchal",   "CSD006", "bharat.panchal@cvmu.edu.in",   "+919876502005", ["IoT", "ES", "DE"],       24, "morning"),
                ("Dr. Neha Vyas",          "CSD007", "neha.vyas@cvmu.edu.in",        "+919876502006", ["SE", "DBMS", "OS"],      24, "afternoon"),
                ("Prof. Chirag Modi",      "CSD008", "chirag.modi@cvmu.edu.in",      "+919876502007", ["WAD", "CN", "GD"],       24, "any"),
                ("Prof. Darshana Patel",   "CSD009", "darshana.patel@cvmu.edu.in",   "+919876502008", ["CG", "DV", "UIX"],       24, "morning"),
                ("Dr. Mayur Bambhania",    "CSD010", "mayur.bambhania@cvmu.edu.in",  "+919876502009", ["ML", "DL", "CV"],        24, "afternoon"),
                ("Prof. Foram Shah",       "CSD011", "foram.shah@cvmu.edu.in",       "+919876502010", ["MAD", "AR", "PDM"],      24, "any"),
                ("Prof. Vishal Kothari",   "CSD012", "vishal.kothari@cvmu.edu.in",   "+919876502011", ["CC", "DevOps", "SE"],    24, "morning"),
            ],
            "EC": [
                ("Prof. Anand Trivedi",    "EC002", "anand.trivedi@cvmu.edu.in",     "+919876503001", ["PE", "ED"],              24, "morning"),
                ("Dr. Rashmi Bhatt",       "EC003", "rashmi.bhatt@cvmu.edu.in",      "+919876503002", ["CS", "SS"],              24, "morning"),
                ("Prof. Manish Soni",      "EC004", "manish.soni@cvmu.edu.in",       "+919876503003", ["EM", "IC"],              24, "afternoon"),
                ("Dr. Paresh Pandya",      "EC005", "paresh.pandya@cvmu.edu.in",     "+919876503004", ["PS", "PM"],              24, "any"),
                ("Prof. Dimple Patel",     "EC006", "dimple.patel@cvmu.edu.in",      "+919876503005", ["EI", "MU", "NA"],        24, "morning"),
                ("Dr. Ashish Raval",       "EC007", "ashish.raval@cvmu.edu.in",      "+919876503006", ["PE", "ED", "AC"],        24, "afternoon"),
                ("Prof. Kavita Mehta",     "EC008", "kavita.mehta@cvmu.edu.in",      "+919876503007", ["SS", "DSP", "DE"],       24, "any"),
                ("Prof. Hitesh Solanki",   "EC009", "hitesh.solanki@cvmu.edu.in",    "+919876503008", ["NA", "EM", "DC"],        24, "morning"),
                ("Dr. Swati Bhavsar",      "EC010", "swati.bhavsar@cvmu.edu.in",     "+919876503009", ["VLSI", "ES", "MC"],      24, "afternoon"),
                ("Prof. Nilam Prajapati",  "EC011", "nilam.prajapati@cvmu.edu.in",   "+919876503010", ["WC", "OC", "IP"],        24, "any"),
            ],
            "ME": [
                ("Prof. Hemant Prajapati", "ME002", "hemant.prajapati@cvmu.edu.in",  "+919876504001", ["FM", "HT"],              24, "morning"),
                ("Dr. Vijay Rathod",       "ME003", "vijay.rathod@cvmu.edu.in",      "+919876504002", ["MD", "MP"],              24, "morning"),
                ("Prof. Nisha Chaudhary",  "ME004", "nisha.chaudhary@cvmu.edu.in",   "+919876504003", ["TE", "RAC"],             24, "afternoon"),
                ("Dr. Tushar Bhavsar",     "ME005", "tushar.bhavsar@cvmu.edu.in",    "+919876504004", ["CAD", "FEA"],            24, "any"),
                ("Prof. Sanjay Gohil",     "ME006", "sanjay.gohil@cvmu.edu.in",      "+919876504005", ["FM", "ICE", "SOM"],      24, "morning"),
                ("Dr. Alpesh Vaghela",     "ME007", "alpesh.vaghela@cvmu.edu.in",    "+919876504006", ["TOM", "MD", "DOM"],      24, "afternoon"),
                ("Prof. Ishita Jadeja",    "ME008", "ishita.jadeja@cvmu.edu.in",     "+919876504007", ["IE", "OR", "MS"],        24, "any"),
                ("Prof. Kalpesh Dave",     "ME009", "kalpesh.dave@cvmu.edu.in",      "+919876504008", ["MP", "EG", "SOM"],       24, "morning"),
                ("Dr. Gaurav Panchal",     "ME010", "gaurav.panchal@cvmu.edu.in",    "+919876504009", ["ATD", "PPE", "KOM"],     24, "afternoon"),
                ("Prof. Shital Patel",     "ME011", "shital.patel@cvmu.edu.in",      "+919876504010", ["RAC", "HM", "MQC"],     24, "any"),
            ],
            "CH": [
                ("Prof. Dhaval Bhatt",     "CH002", "dhaval.bhatt@cvmu.edu.in",      "+919876505001", ["CPC", "CET"],            24, "morning"),
                ("Dr. Sweta Pandya",       "CH003", "sweta.pandya@cvmu.edu.in",      "+919876505002", ["HTO", "MO"],             24, "morning"),
                ("Prof. Nirav Doshi",      "CH004", "nirav.doshi@cvmu.edu.in",       "+919876505003", ["MTO", "CRE"],            24, "afternoon"),
                ("Dr. Priti Barot",        "CH005", "priti.barot@cvmu.edu.in",       "+919876505004", ["PDC", "TP"],             24, "any"),
                ("Prof. Kamlesh Solanki",  "CH006", "kamlesh.solanki@cvmu.edu.in",   "+919876505005", ["PRE", "BE"],             24, "morning"),
                ("Dr. Reena Trivedi",      "CH007", "reena.trivedi@cvmu.edu.in",     "+919876505006", ["IPC", "PCT"],            24, "afternoon"),
                ("Prof. Tarun Mehta",      "CH008", "tarun.mehta@cvmu.edu.in",       "+919876505007", ["CPI", "PDE"],            24, "any"),
                ("Prof. Anjali Rathod",    "CH009", "anjali.rathod@cvmu.edu.in",     "+919876505008", ["PSO", "SHA", "FT"],      24, "morning"),
                ("Dr. Jayesh Mistry",      "CH010", "jayesh.mistry@cvmu.edu.in",     "+919876505009", ["OC", "PC", "MS"],        24, "afternoon"),
            ],
        }

        total_faculty = 0
        all_faculty_info = []
        for dept_code, members in faculty_by_dept.items():
            dept_id = departments[dept_code][1]
            for name, emp_id, email, phone, expertise, max_load, pref in members:
                uid, fid = _id(), _id()
                db.add(User(
                    user_id=uid, email=email, phone=phone,
                    hashed_password=hash_password("faculty123"),
                    full_name=name, role=UserRole.FACULTY,
                    college_id=college_id, dept_id=dept_id,
                ))
                db.add(Faculty(
                    faculty_id=fid, dept_id=dept_id, user_id=uid,
                    name=name, employee_id=emp_id, expertise=expertise,
                    max_weekly_load=max_load, preferred_time=pref,
                ))
                total_faculty += 1
                all_faculty_info.append((dept_code, emp_id, name))

        # ════════════════════════════════════════════════════════
        # SUBJECTS  (Semesters 1–8, all departments)
        # ════════════════════════════════════════════════════════
        #
        # Code format: BBSSNNVV (8 digits)
        #   BB = Branch  (00=Common, 01=CP, 02=CSD, 03=EC, 04=ME, 05=CH)
        #   SS = Semester (01–08)
        #   NN = Subject serial (01, 02, …)
        #   VV = Variant  (00=Core, 01=Open Elective, 02=Program Elective)
        #
        # Format: (name, code, sem, credits, lec_hrs, lab_hrs, batch_size)
        #

        # ── Common first-year subjects (sem 1 & 2) — BB=00 ──
        # Shared code across all departments
        common_subjects = [
            # Semester 1
            ("Mathematics-I",                    "00010100", 1, 4, 3, 0, 60),
            ("Physics",                          "00010200", 1, 4, 3, 2, 60),
            ("Chemistry",                        "00010300", 1, 4, 3, 2, 60),
            ("Engineering Graphics",             "00010400", 1, 3, 1, 2, 60),
            ("Basic Electrical Engineering",     "00010500", 1, 4, 3, 2, 60),
            ("English Communication",            "00010600", 1, 2, 2, 0, 60),
            ("Workshop Practice",                "00010700", 1, 2, 0, 2, 60),
            # Semester 2
            ("Mathematics-II",                        "00020100", 2, 4, 3, 0, 60),
            ("Environmental Science",                 "00020200", 2, 3, 3, 0, 60),
            ("Programming for Problem Solving (C)",   "00020300", 2, 4, 3, 2, 60),
            ("Basic Electronics",                     "00020400", 2, 4, 3, 2, 60),
            ("Basic Mechanical Engineering",          "00020500", 2, 4, 3, 2, 60),
            ("Professional Communication & Ethics",   "00020600", 2, 2, 2, 0, 60),
        ]

        # ── Department-specific subjects (sem 3–8) ──
        dept_subjects = {
            "CP": [  # BB=01
                # ── Semester 3 ──
                ("Data Structures",                         "01030100",  3, 4, 3, 2, 60),
                ("Digital Logic Design",                    "01030200",  3, 4, 3, 2, 60),
                ("Object Oriented Programming (Java)",      "01030300",  3, 4, 3, 2, 60),
                ("Discrete Mathematics",                    "01030400",  3, 4, 3, 0, 60),
                ("Computer Organization & Architecture",    "01030500",  3, 3, 3, 0, 60),
                ("Effective Technical Communication",       "01030600",  3, 2, 2, 0, 60),
                # ── Semester 4 ──
                ("Analysis & Design of Algorithms",         "01040100",  4, 4, 3, 0, 60),
                ("Operating Systems",                       "01040200",  4, 4, 3, 2, 60),
                ("Microprocessor & Interfacing",            "01040300",  4, 4, 3, 2, 60),
                (".NET Framework",                          "01040400",  4, 4, 3, 2, 60),
                ("Probability & Statistics",                "01040500",  4, 3, 3, 0, 60),
                ("Open Elective-I: Environmental Engg.",    "01040601",  4, 2, 2, 0, 60),
                # ── Semester 5 ──
                ("Computer Networks",                       "01050100",  5, 4, 3, 2, 60),
                ("Database Management Systems",             "01050200",  5, 4, 3, 2, 60),
                ("Software Engineering",                    "01050300",  5, 3, 3, 0, 60),
                ("Theory of Computation",                   "01050400",  5, 3, 3, 0, 60),
                ("Web Technology",                          "01050500",  5, 3, 2, 2, 60),
                ("Program Elective-I: Data Mining",         "01050602",  5, 3, 3, 0, 60),
                # ── Semester 6 ──
                ("Compiler Design",                         "01060100",  6, 4, 3, 2, 60),
                ("Machine Learning",                        "01060200",  6, 4, 3, 2, 60),
                ("Information Security",                    "01060300",  6, 3, 3, 0, 60),
                ("Cloud Computing",                         "01060400",  6, 4, 3, 2, 60),
                ("Program Elective-II: Image Processing",   "01060502",  6, 3, 3, 0, 60),
                ("Open Elective-II: Cyber Security",        "01060601",  6, 3, 3, 0, 60),
                # ── Semester 7 ──
                ("Artificial Intelligence",                 "01070100",  7, 4, 3, 2, 60),
                ("Big Data Analytics",                      "01070200",  7, 4, 3, 2, 60),
                ("Internet of Things",                      "01070300",  7, 4, 3, 2, 60),
                ("Program Elective-III: NLP",               "01070402",  7, 3, 3, 0, 60),
                ("Open Elective-III: Entrepreneurship",     "01070501",  7, 3, 3, 0, 60),
                ("Project-I",                               "01070600",  7, 4, 0, 4, 60),
                # ── Semester 8 ──
                ("Blockchain Technology",                   "01080100",  8, 3, 3, 0, 60),
                ("Program Elective-IV: Quantum Computing",  "01080202",  8, 3, 3, 0, 60),
                ("Open Elective-IV: Indian Constitution",   "01080301",  8, 2, 2, 0, 60),
                ("Project-II & Seminar",                    "01080400",  8, 8, 0, 4, 60),
            ],
            "CSD": [  # BB=02
                # ── Semester 3 ──
                ("Data Structures & Algorithms",            "02030100",  3, 4, 3, 2, 60),
                ("Digital System Design",                   "02030200",  3, 4, 3, 2, 60),
                ("Object Oriented Programming",             "02030300",  3, 4, 3, 2, 60),
                ("Discrete Mathematics",                    "02030400",  3, 4, 3, 0, 60),
                ("Design Thinking & Innovation",            "02030500",  3, 3, 3, 0, 60),
                ("UI/UX Design Fundamentals",               "02030600",  3, 3, 2, 2, 60),
                # ── Semester 4 ──
                ("Database Management Systems",             "02040100",  4, 4, 3, 2, 60),
                ("Operating Systems",                       "02040200",  4, 4, 3, 2, 60),
                ("Computer Graphics & Visualization",       "02040300",  4, 4, 3, 2, 60),
                ("Probability & Statistics",                "02040400",  4, 3, 3, 0, 60),
                ("Human Computer Interaction",              "02040500",  4, 3, 3, 0, 60),
                ("Open Elective-I: Environmental Studies",  "02040601",  4, 2, 2, 0, 60),
                # ── Semester 5 ──
                ("Computer Networks",                       "02050100",  5, 4, 3, 2, 60),
                ("Software Engineering & Project Mgmt.",    "02050200",  5, 3, 3, 0, 60),
                ("Web Application Development",             "02050300",  5, 4, 3, 2, 60),
                ("Interactive Media Design",                "02050400",  5, 3, 2, 2, 60),
                ("Theory of Computation",                   "02050500",  5, 3, 3, 0, 60),
                ("Program Elective-I: Mobile App Dev.",     "02050602",  5, 3, 3, 0, 60),
                # ── Semester 6 ──
                ("Artificial Intelligence",                 "02060100",  6, 4, 3, 2, 60),
                ("Information Security",                    "02060200",  6, 3, 3, 0, 60),
                ("Game Design & Development",               "02060300",  6, 4, 3, 2, 60),
                ("Data Visualization",                      "02060400",  6, 3, 2, 2, 60),
                ("Program Elective-II: AR/VR Design",       "02060502",  6, 3, 3, 0, 60),
                ("Open Elective-II: Social Innovation",     "02060601",  6, 3, 3, 0, 60),
                # ── Semester 7 ──
                ("Machine Learning",                        "02070100",  7, 4, 3, 2, 60),
                ("Cloud Computing & DevOps",                "02070200",  7, 4, 3, 2, 60),
                ("Product Design & Management",             "02070300",  7, 3, 3, 0, 60),
                ("Program Elective-III: Deep Learning",     "02070402",  7, 3, 3, 0, 60),
                ("Open Elective-III: Entrepreneurship",     "02070501",  7, 3, 3, 0, 60),
                ("Project-I",                               "02070600",  7, 4, 0, 4, 60),
                # ── Semester 8 ──
                ("Interaction Design Studio",               "02080100",  8, 3, 2, 2, 60),
                ("Program Elective-IV: Ethical AI",         "02080202",  8, 3, 3, 0, 60),
                ("Open Elective-IV: Indian Constitution",   "02080301",  8, 2, 2, 0, 60),
                ("Project-II & Seminar",                    "02080400",  8, 8, 0, 4, 60),
            ],
            "EC": [  # BB=03
                # ── Semester 3 ──
                ("Network Analysis",                        "03030100",  3, 4, 3, 2, 60),
                ("Electronic Devices & Circuits",           "03030200",  3, 4, 3, 2, 60),
                ("Digital Electronics",                     "03030300",  3, 4, 3, 2, 60),
                ("Signals & Systems",                       "03030400",  3, 4, 3, 0, 60),
                ("Electromagnetic Theory",                  "03030500",  3, 3, 3, 0, 60),
                ("Engineering Mathematics-III",             "03030600",  3, 3, 3, 0, 60),
                # ── Semester 4 ──
                ("Analog Communication",                    "03040100",  4, 4, 3, 2, 60),
                ("Microprocessor & Microcontroller",        "03040200",  4, 4, 3, 2, 60),
                ("Linear Integrated Circuits",              "03040300",  4, 4, 3, 2, 60),
                ("Control Systems",                         "03040400",  4, 4, 3, 2, 60),
                ("Probability & Random Processes",          "03040500",  4, 3, 3, 0, 60),
                ("Open Elective-I: Environmental Studies",  "03040601",  4, 2, 2, 0, 60),
                # ── Semester 5 ──
                ("Digital Communication",                   "03050100",  5, 4, 3, 2, 60),
                ("VLSI Design",                             "03050200",  5, 4, 3, 2, 60),
                ("Antenna & Wave Propagation",              "03050300",  5, 3, 3, 0, 60),
                ("Embedded Systems",                        "03050400",  5, 4, 3, 2, 60),
                ("Data Communication & Networking",         "03050500",  5, 3, 3, 0, 60),
                ("Program Elective-I: Biomedical Elect.",   "03050602",  5, 3, 3, 0, 60),
                # ── Semester 6 ──
                ("Wireless Communication",                  "03060100",  6, 4, 3, 2, 60),
                ("Digital Signal Processing",               "03060200",  6, 4, 3, 2, 60),
                ("Optical Communication",                   "03060300",  6, 3, 3, 0, 60),
                ("Microwave Engineering",                   "03060400",  6, 4, 3, 2, 60),
                ("Program Elective-II: Satellite Comm.",    "03060502",  6, 3, 3, 0, 60),
                ("Open Elective-II: IoT Basics",            "03060601",  6, 3, 3, 0, 60),
                # ── Semester 7 ──
                ("Mobile Communication",                    "03070100",  7, 4, 3, 2, 60),
                ("Image Processing",                        "03070200",  7, 4, 3, 2, 60),
                ("Radar Engineering",                       "03070300",  7, 3, 3, 0, 60),
                ("Program Elective-III: Robotics",          "03070402",  7, 3, 3, 0, 60),
                ("Open Elective-III: Entrepreneurship",     "03070501",  7, 3, 3, 0, 60),
                ("Project-I",                               "03070600",  7, 4, 0, 4, 60),
                # ── Semester 8 ──
                ("Fiber Optic Networks",                    "03080100",  8, 3, 3, 0, 60),
                ("Program Elective-IV: 5G Technology",      "03080202",  8, 3, 3, 0, 60),
                ("Open Elective-IV: Indian Constitution",   "03080301",  8, 2, 2, 0, 60),
                ("Project-II & Seminar",                    "03080400",  8, 8, 0, 4, 60),
            ],
            "ME": [  # BB=04
                # ── Semester 3 ──
                ("Engineering Thermodynamics",              "04030100",  3, 4, 3, 0, 60),
                ("Strength of Materials",                   "04030200",  3, 4, 3, 2, 60),
                ("Manufacturing Processes",                 "04030300",  3, 4, 3, 2, 60),
                ("Engineering Graphics & CAD",              "04030400",  3, 3, 2, 2, 60),
                ("Material Science & Metallurgy",           "04030500",  3, 3, 3, 0, 60),
                ("Engineering Mathematics-III",             "04030600",  3, 3, 3, 0, 60),
                # ── Semester 4 ──
                ("Fluid Mechanics",                         "04040100",  4, 4, 3, 2, 60),
                ("Kinematics of Machines",                  "04040200",  4, 4, 3, 0, 60),
                ("Machine Drawing",                         "04040300",  4, 3, 1, 2, 60),
                ("Applied Thermodynamics",                  "04040400",  4, 4, 3, 2, 60),
                ("Metrology & Quality Control",             "04040500",  4, 3, 3, 2, 60),
                ("Open Elective-I: Environmental Studies",  "04040601",  4, 2, 2, 0, 60),
                # ── Semester 5 ──
                ("Theory of Machines",                      "04050100",  5, 4, 3, 2, 60),
                ("Heat Transfer",                           "04050200",  5, 4, 3, 2, 60),
                ("Machine Design-I",                        "04050300",  5, 4, 3, 0, 60),
                ("Hydraulic Machines",                      "04050400",  5, 4, 3, 2, 60),
                ("Industrial Engineering",                  "04050500",  5, 3, 3, 0, 60),
                ("Program Elective-I: Renewable Energy",    "04050602",  5, 3, 3, 0, 60),
                # ── Semester 6 ──
                ("Dynamics of Machines",                    "04060100",  6, 4, 3, 2, 60),
                ("Machine Design-II",                       "04060200",  6, 4, 3, 0, 60),
                ("Refrigeration & Air Conditioning",        "04060300",  6, 4, 3, 2, 60),
                ("CAD/CAM",                                 "04060400",  6, 4, 2, 2, 60),
                ("Program Elective-II: Automobile Engg.",   "04060502",  6, 3, 3, 0, 60),
                ("Open Elective-II: Operations Research",   "04060601",  6, 3, 3, 0, 60),
                # ── Semester 7 ──
                ("IC Engines & Gas Turbines",               "04070100",  7, 4, 3, 2, 60),
                ("Finite Element Analysis",                 "04070200",  7, 4, 3, 2, 60),
                ("Power Plant Engineering",                 "04070300",  7, 3, 3, 0, 60),
                ("Program Elective-III: Robotics & Auto.",  "04070402",  7, 3, 3, 0, 60),
                ("Open Elective-III: Entrepreneurship",     "04070501",  7, 3, 3, 0, 60),
                ("Project-I",                               "04070600",  7, 4, 0, 4, 60),
                # ── Semester 8 ──
                ("Advanced Manufacturing",                  "04080100",  8, 3, 3, 0, 60),
                ("Program Elective-IV: Mechatronics",       "04080202",  8, 3, 3, 0, 60),
                ("Open Elective-IV: Indian Constitution",   "04080301",  8, 2, 2, 0, 60),
                ("Project-II & Seminar",                    "04080400",  8, 8, 0, 4, 60),
            ],
            "CH": [  # BB=05
                # ── Semester 3 ──
                ("Chemical Process Calculations",           "05030100",  3, 4, 3, 0, 60),
                ("Chemical Engg. Thermodynamics-I",         "05030200",  3, 4, 3, 0, 60),
                ("Fluid Mechanics for Chem. Engineers",     "05030300",  3, 4, 3, 2, 60),
                ("Organic Chemistry",                       "05030400",  3, 4, 3, 2, 60),
                ("Material Science",                        "05030500",  3, 3, 3, 0, 60),
                ("Engineering Mathematics-III",             "05030600",  3, 3, 3, 0, 60),
                # ── Semester 4 ──
                ("Chemical Engg. Thermodynamics-II",        "05040100",  4, 4, 3, 0, 60),
                ("Heat Transfer Operations",                "05040200",  4, 4, 3, 2, 60),
                ("Mechanical Operations",                   "05040300",  4, 4, 3, 2, 60),
                ("Physical Chemistry",                      "05040400",  4, 4, 3, 2, 60),
                ("Instrumentation & Process Control",       "05040500",  4, 3, 3, 2, 60),
                ("Open Elective-I: Environmental Studies",  "05040601",  4, 2, 2, 0, 60),
                # ── Semester 5 ──
                ("Mass Transfer Operations-I",              "05050100",  5, 4, 3, 2, 60),
                ("Chemical Reaction Engineering-I",         "05050200",  5, 4, 3, 0, 60),
                ("Process Equipment Design",                "05050300",  5, 4, 3, 0, 60),
                ("Petroleum Refinery Engineering",          "05050400",  5, 3, 3, 0, 60),
                ("Biochemical Engineering",                 "05050500",  5, 3, 3, 2, 60),
                ("Program Elective-I: Polymer Technology",  "05050602",  5, 3, 3, 0, 60),
                # ── Semester 6 ──
                ("Mass Transfer Operations-II",             "05060100",  6, 4, 3, 2, 60),
                ("Chemical Reaction Engineering-II",        "05060200",  6, 4, 3, 2, 60),
                ("Process Dynamics & Control",              "05060300",  6, 3, 3, 0, 60),
                ("Transport Phenomena",                     "05060400",  6, 4, 3, 0, 60),
                ("Program Elective-II: Nanotechnology",     "05060502",  6, 3, 3, 0, 60),
                ("Open Elective-II: Environmental Engg.",   "05060601",  6, 3, 3, 0, 60),
                # ── Semester 7 ──
                ("Chemical Process Industries",             "05070100",  7, 4, 3, 0, 60),
                ("Plant Design & Economics",                "05070200",  7, 4, 3, 2, 60),
                ("Process Simulation & Optimization",       "05070300",  7, 4, 3, 2, 60),
                ("Program Elective-III: Green Chemistry",   "05070402",  7, 3, 3, 0, 60),
                ("Open Elective-III: Entrepreneurship",     "05070501",  7, 3, 3, 0, 60),
                ("Project-I",                               "05070600",  7, 4, 0, 4, 60),
                # ── Semester 8 ──
                ("Safety & Hazard Analysis",                "05080100",  8, 3, 3, 0, 60),
                ("Program Elective-IV: Food Technology",    "05080202",  8, 3, 3, 0, 60),
                ("Open Elective-IV: Indian Constitution",   "05080301",  8, 2, 2, 0, 60),
                ("Project-II & Seminar",                    "05080400",  8, 8, 0, 4, 60),
            ],
        }

        # Insert common (sem 1-2) + department-specific (sem 3-8) subjects
        total_subjects = 0
        all_subject_info = []
        for dept_code in departments:
            dept_id = departments[dept_code][1]
            # Common sem 1 & 2 (same code for all departments)
            for name, code, sem, credits, lh, lab_h, bs in common_subjects:
                db.add(Subject(
                    subject_id=_id(), dept_id=dept_id, name=name,
                    subject_code=code, semester=sem, credits=credits,
                    weekly_periods=lh + lab_h, lecture_hours=lh, lab_hours=lab_h,
                    needs_lab=lab_h > 0, batch_size=bs,
                ))
                total_subjects += 1
                all_subject_info.append((dept_code, code, name, sem, lh, lab_h))

            # Department-specific sem 3-8
            if dept_code in dept_subjects:
                for name, code, sem, credits, lh, lab_h, bs in dept_subjects[dept_code]:
                    db.add(Subject(
                        subject_id=_id(), dept_id=dept_id, name=name,
                        subject_code=code, semester=sem, credits=credits,
                        weekly_periods=lh + lab_h, lecture_hours=lh, lab_hours=lab_h,
                        needs_lab=lab_h > 0, batch_size=bs,
                    ))
                    total_subjects += 1
                    all_subject_info.append((dept_code, code, name, sem, lh, lab_h))

        # ════════════════════════════════════════════════════════
        # ROOMS — 35 Classrooms (7 per dept) + 3 Seminar Halls
        # ════════════════════════════════════════════════════════
        classroom_data = []
        for dept_code in departments:
            for i in range(1, 8):
                name = f"{dept_code}-{i:02d}"
                cap = 80 if i <= 2 else 60
                ac = i <= 3
                classroom_data.append((name, cap, RoomType.CLASSROOM, True, False, ac))

        seminar_data = [
            ("Seminar Hall 1",  120, RoomType.SEMINAR, True, False, True),
            ("Seminar Hall 2",  150, RoomType.SEMINAR, True, False, True),
            ("Auditorium",      300, RoomType.SEMINAR, True, False, True),
        ]

        all_room_data = classroom_data + seminar_data
        for name, cap, rtype, proj, comp, ac in all_room_data:
            db.add(Room(
                room_id=_id(), college_id=college_id, name=name,
                capacity=cap, room_type=rtype,
                has_projector=proj, has_computers=comp, has_ac=ac,
            ))

        # ════════════════════════════════════════════════════════
        # LABS — 50 total (classified by naming convention)
        # ════════════════════════════════════════════════════════
        lab_data = [
            # ── Computer Labs (18) — highest count ──
            ("Computer Lab 1",       40, True, True, True),
            ("Computer Lab 2",       40, True, True, True),
            ("Computer Lab 3",       40, True, True, True),
            ("Computer Lab 4",       40, True, True, True),
            ("Computer Lab 5",       40, True, True, True),
            ("Computer Lab 6",       40, True, True, True),
            ("Computer Lab 7",       30, True, True, True),
            ("Computer Lab 8",       30, True, True, True),
            ("Computer Lab 9",       30, True, True, True),
            ("Computer Lab 10",      30, True, True, True),
            ("Computer Lab 11",      30, True, True, True),
            ("Computer Lab 12",      30, True, True, True),
            ("Computer Lab 13",      30, True, True, True),
            ("Computer Lab 14",      30, True, True, True),
            ("Computer Lab 15",      30, True, True, True),
            ("Computer Lab 16",      30, True, True, True),
            ("Computer Lab 17",      30, True, True, True),
            ("Computer Lab 18",      30, True, True, True),
            # ── Electronics Labs (5) ──
            ("Electronics Lab 1",    30, True, False, True),
            ("Electronics Lab 2",    30, True, False, True),
            ("Electronics Lab 3",    30, True, False, True),
            ("Electronics Lab 4",    30, True, False, True),
            ("Electronics Lab 5",    30, True, False, True),
            # ── Electrical Labs (3) ──
            ("Electrical Machines Lab",       30, True, False, True),
            ("Electrical Measurements Lab",   30, True, False, True),
            ("Power Systems Lab",             30, True, False, True),
            # ── Networking Labs (2) ──
            ("Networking Lab 1",     30, True, True, True),
            ("Networking Lab 2",     30, True, True, True),
            # ── AI/ML Labs (2) ──
            ("AI/ML Lab 1",          30, True, True, True),
            ("AI/ML Lab 2",          30, True, True, True),
            # ── Robotics Labs (2) ──
            ("Robotics Lab 1",       25, True, False, True),
            ("Robotics Lab 2",       25, True, False, True),
            # ── IoT Labs (2) ──
            ("IoT Lab 1",            25, True, True, True),
            ("IoT Lab 2",            25, True, True, True),
            # ── Chemical Engineering Labs (4) ──
            ("Chemical Process Lab",          30, False, False, True),
            ("Chemical Analysis Lab",         30, False, False, True),
            ("Chemical Reaction Lab",         30, False, False, True),
            ("Petroleum & Polymer Lab",       30, False, False, True),
            # ── Mechanical Workshops (4) ──
            ("Mechanical Workshop 1 (Fitting)", 30, False, False, False),
            ("Mechanical Workshop 2 (Welding)", 30, False, False, False),
            ("Mechanical Workshop 3 (Machine Shop)", 30, False, False, False),
            ("Mechanical Workshop 4 (Smithy)",  30, False, False, False),
            # ── Physics Labs (2) ──
            ("Physics Lab 1",        30, False, False, True),
            ("Physics Lab 2",        30, False, False, True),
            # ── Chemistry Labs (2) ──
            ("Chemistry Lab 1",      30, False, False, True),
            ("Chemistry Lab 2",      30, False, False, True),
            # ── Design Studios (2) ──
            ("Design Studio 1",      25, True, True, True),
            ("Design Studio 2",      25, True, True, True),
            # ── Simulation Lab (1) ──
            ("Simulation & CAD Lab", 30, True, True, True),
            # ── 3D Printing Lab (1) ──
            ("3D Printing & Prototyping Lab", 20, True, True, True),
        ]
        for name, cap, proj, comp, ac in lab_data:
            db.add(Room(
                room_id=_id(), college_id=college_id, name=name,
                capacity=cap, room_type=RoomType.LAB,
                has_projector=proj, has_computers=comp, has_ac=ac,
            ))

        # ════════════════════════════════════════════════════════
        # EXAM VENUES
        # ════════════════════════════════════════════════════════
        venue_data = [
            ("Main Examination Hall",   250, VenueType.HALL),
            ("Exam Hall A",             120, VenueType.HALL),
            ("Exam Hall B",             120, VenueType.HALL),
            ("Exam Hall C",              80, VenueType.HALL),
        ]
        for name, cap, vtype in venue_data:
            db.add(Venue(
                venue_id=_id(), college_id=college_id,
                name=name, capacity=cap, venue_type=vtype,
            ))

        # ════════════════════════════════════════════════════════
        # TIME SLOTS  (7 lectures + 5-min breaks between + lunch)
        # ════════════════════════════════════════════════════════
        slot_data = [
            (1,  "Period 1",  "09:00", "10:00", SlotType.LECTURE),
            (2,  "Break",     "10:00", "10:05", SlotType.BREAK),
            (3,  "Period 2",  "10:05", "11:05", SlotType.LECTURE),
            (4,  "Break",     "11:05", "11:10", SlotType.BREAK),
            (5,  "Period 3",  "11:10", "12:10", SlotType.LECTURE),
            (6,  "Break",     "12:10", "12:15", SlotType.BREAK),
            (7,  "Period 4",  "12:15", "13:15", SlotType.LECTURE),
            (8,  "Lunch",     "13:15", "14:00", SlotType.BREAK),
            (9,  "Period 5",  "14:00", "15:00", SlotType.LECTURE),
            (10, "Break",     "15:00", "15:05", SlotType.BREAK),
            (11, "Period 6",  "15:05", "16:05", SlotType.LECTURE),
            (12, "Break",     "16:05", "16:10", SlotType.BREAK),
            (13, "Period 7",  "16:10", "17:10", SlotType.LECTURE),
        ]
        for order, label, start, end, stype in slot_data:
            db.add(TimeSlotConfig(
                slot_id=_id(), college_id=college_id,
                slot_order=order, label=label,
                start_time=start, end_time=end, slot_type=stype,
            ))

        # ════════════════════════════════════════════════════════
        # BATCHES  (A, B, C per dept per semester — 20 students each)
        # ════════════════════════════════════════════════════════
        total_batches = 0
        for dept_code, (_, dept_id) in departments.items():
            for sem in range(1, 9):
                for batch_name in ["A", "B", "C"]:
                    db.add(Batch(
                        batch_id=_id(), dept_id=dept_id,
                        semester=sem, name=batch_name, size=20,
                    ))
                    total_batches += 1

        # ── Commit ──
        await db.commit()

        # ════════════════════════════════════════════════════════
        # SUMMARY
        # ════════════════════════════════════════════════════════
        print("=" * 70)
        print("  CVM University — Seed Data Created Successfully!")
        print("=" * 70)
        print()
        print("  College: CVM University, Anand (GTU Affiliated)")
        print()
        print("  Departments:")
        for code, (name, _) in departments.items():
            print(f"    {code:4s} — {name}")
        print()
        print("  Users & Credentials:")
        print(f"    Super Admin : admin@cvmu.edu.in / admin123")
        for code, (name, email, *_) in hod_data.items():
            print(f"    HOD {code:4s}    : {email} / hod123")
        print(f"    All Faculty : <email> / faculty123")
        print()

        # Faculty summary
        print(f"  Faculty: {total_faculty} members + {len(hod_data)} HODs = {total_faculty + len(hod_data)} total")
        for dept_code in departments:
            members = [f for f in all_faculty_info if f[0] == dept_code]
            hod_name = hod_data[dept_code][0]
            hod_empid = hod_data[dept_code][3]
            print(f"    {dept_code} ({len(members) + 1} incl. HOD):")
            print(f"      {hod_empid} — {hod_name} (HOD)")
            for _, emp_id, name in members:
                print(f"      {emp_id} — {name}")
        print()

        # Subject summary
        print(f"  Subjects: {total_subjects}")
        for dept_code in departments:
            dept_subs = [s for s in all_subject_info if s[0] == dept_code]
            print(f"    {dept_code}: {len(dept_subs)} subjects (Sem 1–8)")
            for sem in range(1, 9):
                sem_subs = [s for s in dept_subs if s[3] == sem]
                if sem_subs:
                    print(f"      Sem {sem}: {len(sem_subs)} subjects")
        print()

        # Room summary
        n_classrooms = len(classroom_data)
        n_seminars = len(seminar_data)
        n_labs = len(lab_data)
        print(f"  Rooms: {n_classrooms + n_seminars + n_labs}")
        print(f"    Classrooms:    {n_classrooms} (7 per department)")
        print(f"    Seminar Halls: {n_seminars}")
        print(f"    Labs:          {n_labs}")

        # Lab breakdown by category
        categories = {}
        for name, *_ in lab_data:
            if "Computer Lab" in name:
                cat = "Computer Labs"
            elif "Electronics" in name:
                cat = "Electronics Labs"
            elif "Electrical" in name or "Power Systems" in name:
                cat = "Electrical Labs"
            elif "Networking" in name:
                cat = "Networking Labs"
            elif "AI/ML" in name:
                cat = "AI/ML Labs"
            elif "Robotics" in name:
                cat = "Robotics Labs"
            elif "IoT" in name:
                cat = "IoT Labs"
            elif "Chemical" in name or "Petroleum" in name:
                cat = "Chemical Engg. Labs"
            elif "Workshop" in name or "Smithy" in name:
                cat = "Mechanical Workshops"
            elif "Physics" in name:
                cat = "Physics Labs"
            elif "Chemistry" in name:
                cat = "Chemistry Labs"
            elif "Design Studio" in name:
                cat = "Design Studios"
            elif "Simulation" in name:
                cat = "Simulation Lab"
            elif "3D Printing" in name:
                cat = "3D Printing Lab"
            else:
                cat = "Other"
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in categories.items():
            print(f"      {cat}: {count}")
        print()

        print(f"  Exam Venues: {len(venue_data)}")
        for name, cap, vtype in venue_data:
            print(f"    {name} ({vtype.value}, cap={cap})")
        print()
        print(f"  Batches: {total_batches} (A–C × {len(departments)} depts × Sem 1–8, 20 students each)")
        print(f"  Time Slots: {len(slot_data)} ({sum(1 for s in slot_data if s[4] == SlotType.LECTURE)} lectures + breaks)")
        print()
        print("=" * 70)


if __name__ == "__main__":
    import models  # noqa: F401
    asyncio.run(seed())
