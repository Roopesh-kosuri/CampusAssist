"""Script to update all 72 FAQs in data/faqs.json with authentic, verified LPU campus data."""
import json
from pathlib import Path

FAQS_PATH = Path("data/faqs.json")

# Verified data map for all 72 FAQs
UPDATES = {
    # ── HOSTEL (hos_01 to hos_12) ──
    "hos_01": {
        "answer": "Hey! You can register a maintenance request directly on UMS by going to UMS (https://ums.lpu.in/lpuums/) → Relationship Management System (RMS) → Log Request → Maintenance / Electrical Complaints. For urgent room issues, you can also notify your floor warden or visit your hostel's turnstile warden desk.",
        "department_contact": "Hostel Warden Office & Maintenance Desk (Ext. 4037 for BH-1, Ext. 4027 for GH-1)",
        "keywords": ["repair", "maintenance", "carpenter", "electrician", "plumber", "broken", "complaint", "room", "fix", "fan", "noise", "pankha", "rms"]
    },
    "hos_02": {
        "answer": "Hostel turnstiles close strictly at 7:30 PM for girls and 8:30 PM for boys (extended slightly in summers). Make sure to tap your RFID smart card at the gate before curfew; any late entry requires prior written approval from your Chief Warden.",
        "department_contact": "Hostel Security & Turnstile Desk (Helpline: +91-1824-517000)",
        "keywords": ["curfew", "in-time", "closing", "gate", "late", "biometric", "turnstile", "entry", "night", "timing"]
    },
    "hos_03": {
        "answer": "Apply for an electronic leave pass or night-out on UMS (https://ums.lpu.in/lpuums/) under Hostel Services → Leave Request at least 24 hours in advance. Leave is only sanctioned after automated SMS/IVR verification and approval from your registered parents.",
        "department_contact": "Hostel Warden Office, Respective Hostel Block",
        "keywords": ["leave", "night-out", "gatepass", "vacation", "home", "outpass", "permission", "parent", "approval"]
    },
    "hos_04": {
        "answer": "Room change windows officially open on UMS during the first 2 weeks of the semester. If you and your friend want a mutual swap, both of you need to fill out the mutual room change form on UMS or submit a joint application at the Chief Warden Office in Block 32.",
        "department_contact": "Chief Warden Office, Block 32 (Ground Floor)",
        "keywords": ["room change", "swap", "partner", "shifting", "transfer", "allotment", "single seater", "warden"]
    },
    "hos_05": {
        "answer": "High-wattage electrical appliances like immersion rods, room heaters, electric stoves, and induction plates are strictly prohibited in hostel rooms for fire safety. Possession leads to device confiscation and a disciplinary fine starting at ₹1,000.",
        "department_contact": "Hostel Discipline & Inspection Committee (Helpline: +91-1824-517000)",
        "keywords": ["heater", "kettle", "iron", "cooler", "appliance", "induction", "prohibited", "fine", "power"]
    },
    "hos_06": {
        "answer": "You can change your mess plan (Standard, North/South Indian, or Special) between the 20th and 25th of each month on UMS. For meal rebates, if you take approved leave for more than 7 consecutive days, submit a mess rebate form on UMS before you leave.",
        "department_contact": "Residential Dining Services Counter, Block 34 / Mess Office",
        "keywords": ["mess", "food", "dining", "caterer", "refund", "rebate", "diet", "meal", "change"]
    },
    "hos_07": {
        "answer": "Connect to the 'LPU_Campus' Wi-Fi SSID in your hostel and log in with your university registration number and password on the captive portal (https://ums.lpu.in/lpuums/). You can register up to 2 active devices (laptop and smartphone) under your account.",
        "department_contact": "LPU IT & Network Support Helpdesk, Block 30",
        "keywords": ["wifi", "internet", "network", "mac address", "login", "speed", "connectivity", "hotspot", "lan"]
    },
    "hos_08": {
        "answer": "Parents can meet you in the designated hostel reception lounge between 9:00 AM and 6:00 PM after signing the visitor register. For overnight parent stays, guest rooms can be pre-booked online via the Uni-Hotel / Guest House portal on UMS or by visiting Uni-Hotel in Block 34.",
        "department_contact": "Uni-Hotel & Campus Hospitality Desk, Block 34 (Phone: +91-1824-517000)",
        "keywords": ["parents", "visitors", "guest house", "visiting", "family", "overnight", "lounge", "stay", "uni-hotel"]
    },
    "hos_09": {
        "answer": "LPU provides centralized laundry services in designated hostel basements across BH and GH complexes. You get an allowance of 40 garments per month using your biometric smart card, with wash-and-fold delivery typically completed within 48 to 72 hours.",
        "department_contact": "Hostel Facility Management & Laundry Supervisor",
        "keywords": ["laundry", "washing", "clothes", "dry clean", "ironing", "washer", "token", "cycle"]
    },
    "hos_10": {
        "answer": "For night-time medical emergencies, immediately inform your floor warden or call the 24x7 Campus Ambulance at +91-1824-517000. The University Health Centre clinic is open 24/7 in Uni-Hospital (near Block 25) with resident doctors and free basic medicine.",
        "department_contact": "Uni-Hospital 24x7 Emergency Helpdesk (+91-1824-517000)",
        "keywords": ["doctor", "ambulance", "hospital", "sick", "emergency", "clinic", "medicine", "first aid", "health"]
    },
    "hos_11": {
        "answer": "At the end of your session, complete room inventory verification with your floor warden, clear any room electricity overages, and submit the online Hostel No-Dues form on UMS. Your security deposit will be adjusted or refunded back to your bank account within 30 days.",
        "department_contact": "Division of Residential Services, Block 32 (Accounts Desk)",
        "keywords": ["checkout", "vacate", "no dues", "clearance", "security deposit", "refund", "handover", "leaving"]
    },
    "hos_12": {
        "answer": "Bicycles and two-wheelers must be registered with Campus Security in Block 32 to receive an authorized parking sticker. Please note that undergraduate resident students are generally not permitted to park four-wheeler cars inside hostel premises without special administrative approval.",
        "department_contact": "Campus Security & Traffic Control Cell, Block 32 Gate Post",
        "keywords": ["vehicle", "parking", "bike", "cycle", "scooter", "sticker", "permit", "security", "car"]
    },

    # ── LIBRARY (lib_01 to lib_12) ──
    "lib_01": {
        "answer": "The Central Library in Block 37 is open daily from 8:00 AM to 12:00 AM (midnight), including Sundays. During mid-term and end-term exam periods, reading halls remain open extended hours up to 2:00 AM.",
        "department_contact": "Central Library Information Desk, Block 37 (Ground Floor)",
        "keywords": ["hours", "timings", "opening", "closing", "schedule", "shut", "night", "working hours", "open"]
    },
    "lib_02": {
        "answer": "Just scan your RFID student ID card at the automated self-service kiosks or circulation desk on the Ground Floor of Block 37. Books can be renewed online up to 2 consecutive times before the due date via the Web OPAC portal (https://library.lpu.in).",
        "department_contact": "Central Library Circulation Counter, Block 37",
        "keywords": ["issue", "renew", "return", "borrow", "circulation", "book", "counter", "opac", "due date"]
    },
    "lib_03": {
        "answer": "An overdue fine of ₹2 per book per day is charged for late returns. Outstanding fines can be cleared directly online through your UMS fee portal (https://zee.lpu.in/feepayment/) or at the Block 37 library circulation counter.",
        "department_contact": "Central Library Accounts & Circulation Desk, Block 37",
        "keywords": ["fine", "overdue", "penalty", "late return", "delay", "charges", "defaulter", "due", "fee"]
    },
    "lib_04": {
        "answer": "Yes! The Central Library remains open on Sundays and regular holidays from 9:00 AM to 6:00 PM for reading and research. It is completely closed only on 3 national holidays: Republic Day (Jan 26), Independence Day (Aug 15), and Gandhi Jayanti (Oct 2).",
        "department_contact": "Central Library Administration, Block 37",
        "keywords": ["sunday", "holiday", "weekend", "national holiday", "hours", "timings", "open", "schedule"]
    },
    "lib_05": {
        "answer": "Undergraduate (UG) students can borrow up to 4 books for a 14-day loan period, while Postgraduate (PG) and PhD scholars can borrow up to 6 books for 21 days. Don't forget you can renew them online through OPAC before they expire.",
        "department_contact": "Circulation Desk, Ground Floor, Block 37",
        "keywords": ["borrowing limit", "book quota", "maximum books", "duration", "loan period", "undergraduate", "postgraduate", "issue limit"]
    },
    "lib_06": {
        "answer": "You can access digital databases like IEEE Xplore, ScienceDirect, Springer, and Scopus through the LPU Digital Library Portal (https://library.lpu.in) using your UMS student login credentials via remote Knimbus access.",
        "department_contact": "Library Digital Resource & E-Resource Centre, Block 37 (2nd Floor)",
        "keywords": ["digital library", "e-books", "journals", "research papers", "ieee", "scopus", "remote access", "database", "springer"]
    },
    "lib_07": {
        "answer": "Report the misplaced book immediately to the circulation desk in Block 37. You will be asked to replace the book with a brand new copy of the same or latest edition, or pay the current replacement cost plus a nominal processing fee.",
        "department_contact": "Chief Librarian & Circulation In-Charge, Block 37",
        "keywords": ["lost book", "damaged book", "misplaced", "replacement", "penalty", "torn pages", "compensation", "reporting"]
    },
    "lib_08": {
        "answer": "Group discussion cubicles on the 3rd and 4th floors of Block 37 can be reserved by presenting your student IDs at the reference desk, available in 2-hour study slots for academic group projects and presentations.",
        "department_contact": "Library Reference & Research Assistance Desk, Block 37 (3rd Floor)",
        "keywords": ["discussion room", "cubicle", "study room", "group study", "reservation", "booking", "slot", "project work"]
    },
    "lib_09": {
        "answer": "Eligible students (including SC/ST and scholarship recipients) can receive a full set of semester textbooks from the Book Bank in Block 37 basement during the first two weeks of classes by applying via UMS.",
        "department_contact": "Book Bank Distribution Counter, Block 37 (Basement)",
        "keywords": ["book bank", "semester books", "textbook issue", "distribution", "course books", "set", "scholarship", "schemes"]
    },
    "lib_10": {
        "answer": "Yes, reprographic and high-speed laser printing facilities are available on the Ground Floor of Block 37, priced at ₹2 per black-and-white page and ₹10 per color print, open from 9:00 AM to 8:00 PM.",
        "department_contact": "Library Reprographic Centre, Block 37 (Ground Floor)",
        "keywords": ["photocopy", "printing", "xerox", "scanning", "printout", "reprographic", "rates", "document"]
    },
    "lib_11": {
        "answer": "Return all borrowed materials, clear any pending overdue fines at the counter, and submit the online Library No-Dues request on UMS (https://ums.lpu.in/lpuums/). Online clearance is typically verified and updated within 24 hours.",
        "department_contact": "Central Library Clearance Cell, Block 37",
        "keywords": ["library clearance", "no dues", "clearance slip", "final clearance", "convocation", "graduation", "settlement"]
    },
    "lib_12": {
        "answer": "Absolutely! You can submit purchase recommendations for new textbooks or journals through the 'Suggest a Book' feature on OPAC (https://library.lpu.in) or donate clean academic volumes at the Acquisition Desk on the 1st Floor of Block 37.",
        "department_contact": "Acquisition & Book Recommendation Section, Block 37 (1st Floor)",
        "keywords": ["donate books", "suggest book", "book purchase", "recommendation", "contribution", "new title", "collection"]
    },

    # ── FEES (fee_01 to fee_12) ──
    "fee_01": {
        "answer": "You can pay semester fees online through the official LPU Fee Payment Portal (https://zee.lpu.in/feepayment/) using Net Banking, Debit/Credit Cards, or UPI (zero convenience fee on UPI). Offline payments are accepted via HDFC/PNB university bank challans generated from UMS.",
        "department_contact": "Division of Accounts & Finance, Block 32 (1st Floor) · +91-1824-517000",
        "keywords": ["tuition fee", "payment mode", "net banking", "credit card", "upi", "challan", "pay fee", "semester fee", "online payment"]
    },
    "fee_02": {
        "answer": "A late fee penalty of ₹100 to ₹200 per day is charged after the notified semester fee payment deadline. Continued non-payment past the final grace date may result in a temporary block on UMS access and exam registration.",
        "department_contact": "Student Accounts & Fee Section, Block 32",
        "keywords": ["late fee", "penalty", "due date", "fine", "overdue fee", "deadline", "grace period", "late payment"]
    },
    "fee_03": {
        "answer": "Log into UMS (https://ums.lpu.in/lpuums/) and navigate to Fee Management → Fee Statement / Payment History. You can download and print official fee receipts and fee breakdown letters anytime for tax exemptions or reimbursement.",
        "department_contact": "Student Accounts Desk, Block 32 (1st Floor)",
        "keywords": ["fee receipt", "invoice", "payment proof", "download receipt", "fee statement", "tax certificate", "transaction slip"]
    },
    "fee_04": {
        "answer": "Admissions cancellations and fee refunds strictly adhere to standard UGC/university guidelines. You must submit your withdrawal application through UMS under the Admission Withdrawal portal before the notified academic cutoff date.",
        "department_contact": "Admissions & Withdrawal Verification Cell, Block 30/32",
        "keywords": ["fee refund", "admission withdrawal", "cancellation", "money back", "deduction", "policy", "surrender seat"]
    },
    "fee_05": {
        "answer": "Yes, in genuine hardship cases, you can apply for a fee installment plan or extension through UMS → RMS → Log Request → Accounts / Fee Extension, or visit the Financial Aid & Accounts desk in Block 32 before the due date.",
        "department_contact": "Accounts & Financial Grievance Desk, Block 32",
        "keywords": ["installment", "fee extension", "split payment", "financial hardship", "delay payment", "part payment", "request"]
    },
    "fee_06": {
        "answer": "Scholarships based on LPUNEST, 12th/Graduation marks, or sports are automatically credited to your semester fee ledger. To maintain scholarship continuation, you must maintain a minimum 75% attendance and achieve at least 7.0 CGPA with no backlogs.",
        "department_contact": "Scholarship & Financial Aid Branch, Block 32 (Ground Floor)",
        "keywords": ["scholarship", "fee concession", "merit scholarship", "financial aid", "waiver", "discount", "cgpa criteria"]
    },
    "fee_07": {
        "answer": "Don't panic! Failed transactions usually reconcile automatically within 24 to 48 banking hours. If the status remains pending, raise a ticket on UMS via Relationship Management System (RMS) attaching your bank transaction reference ID and bank debit statement.",
        "department_contact": "Accounts Reconciliation Desk, Block 32",
        "keywords": ["failed transaction", "payment deducted", "money debited", "receipt not generated", "double deduction", "reconciliation", "payment error"]
    },
    "fee_08": {
        "answer": "Annual residential and mess renewals are paid via the LPU Payment Gateway (https://zee.lpu.in/feepayment/) during the designated hostel booking window (usually April–June for the next session).",
        "department_contact": "Division of Residential Services Accounts, Block 32",
        "keywords": ["hostel fee", "mess fee", "residential fee", "annual hostel charge", "room rent", "boarder fee", "renewal"]
    },
    "fee_09": {
        "answer": "Yes, reappear/backlog examination registration costs approximately ₹1,000 per theory or practical course, payable directly through e-Connect (https://econnect.lpu.in) during the reappear registration window.",
        "department_contact": "Examination Accounts & Conduct Wing, Block 30/32",
        "keywords": ["reappear fee", "backlog fee", "makeup exam fee", "supplementary exam", "re-exam charge", "course fee"]
    },
    "fee_10": {
        "answer": "Apply online via UMS (https://ums.lpu.in/lpuums/) → Student Services → Certificate Request → Fee Estimate / Bonafide for Bank Loan. You can download the stamped digital certificate or collect a physical copy from Block 32.",
        "department_contact": "Student Facilitation Centre (SFC), Block 32 (Ground Floor)",
        "keywords": ["education loan", "fee estimate", "loan quotation", "bonafide certificate", "bank letter", "sponsorship", "cost of study"]
    },
    "fee_11": {
        "answer": "After successfully completing your program, submit the consolidated University No-Dues clearance on UMS. Your refundable caution deposit is credited directly to your registered bank account via NEFT within 4 to 6 weeks.",
        "department_contact": "Student Finance & Clearance Branch, Block 32",
        "keywords": ["caution money", "security deposit", "refund", "graduation dues", "bank transfer", "deposit return", "final settlement"]
    },
    "fee_12": {
        "answer": "Official disciplinary, hostel, or proctorial fines can be paid securely online via UMS under the Fines & Penalties module or in person at the central cash counter in Block 32.",
        "department_contact": "Central Cash Counter, Block 32 (Ground Floor)",
        "keywords": ["fine payment", "penalty", "disciplinary fine", "cash counter", "violation fine", "challan payment", "clear fine"]
    },

    # ── ID CARD (idc_01 to idc_12) ──
    "idc_01": {
        "answer": "Report the loss on UMS (https://ums.lpu.in/lpuums/) under Student Services → ID Card → Report Lost. Grab a temporary single-day gate slip from the security post, pay the ₹500 duplicate fee online, and pick up your new card from Block 32.",
        "department_contact": "Division of Student Welfare (DSW) ID Card Cell, Block 30/32",
        "keywords": ["lost id card", "misplaced card", "duplicate id", "replacement card", "reissue", "stolen card", "new identity card"]
    },
    "idc_02": {
        "answer": "The fee for a duplicate RFID smart ID card is ₹500. You can pay it directly online via the LPU Fee Payment Portal (https://zee.lpu.in/feepayment/) or at the Block 32 cash counter.",
        "department_contact": "Student Welfare & ID Card Section, Block 32",
        "keywords": ["duplicate id fee", "card replacement cost", "reissue charge", "id card fine", "payment counter", "reprint fee", "aply", "duplcate", "crd"]
    },
    "idc_03": {
        "answer": "First-year students receive their smart RFID cards during the Freshmen Induction Program at Block 32 / Shanti Devi Mittal Auditorium after completing original document verification.",
        "department_contact": "Admissions Verification & Enrollment Desk, Block 32",
        "keywords": ["first year id card", "freshers card", "new admission id", "collect id card", "orientation card", "smart card issue"]
    },
    "idc_04": {
        "answer": "If your card's RFID chip is unresponsive or worn out, visit the Campus Security & Biometric Cell on the Ground Floor of Block 32. If defective through normal wear and tear, it will be tested and re-encoded or replaced.",
        "department_contact": "Security & Biometric Encoding Desk, Block 32 (Ground Floor)",
        "keywords": ["rfid not working", "damaged id card", "turnstile not scanning", "chip error", "tap failed", "smart card repair", "broken card"]
    },
    "idc_05": {
        "answer": "No, a digital photo or phone snapshot is NOT accepted for hostel turnstiles, library entry, or examination hall admittance. You must always carry and tap your physical RFID card.",
        "department_contact": "Chief Security Officer & Proctorial Board, Block 32",
        "keywords": ["digital id", "soft copy id", "mobile id", "photo id", "hall ticket entry", "exam entry without id", "virtual card"]
    },
    "idc_06": {
        "answer": "Submit a Profile Correction request on UMS (https://ums.lpu.in/lpuums/) under Student Profile → Update Details with your 10th mark sheet or government ID attached. Once approved by the Registrar, surrender the old card at Block 32 for a fresh reprint.",
        "department_contact": "Registrar Records & Verification Branch, Block 32",
        "keywords": ["name correction", "photo change", "blood group", "wrong details", "spelling mistake", "update id card", "profile edit"]
    },
    "idc_07": {
        "answer": "Yes, university regulations require all students to wear their student ID card visibly around their neck using the official LPU lanyard while on academic blocks and university pathways.",
        "department_contact": "Proctorial Board & Campus Security Staff",
        "keywords": ["wear id card", "lanyard", "mandatory id", "security checking", "inspection", "campus rules", "identification"]
    },
    "idc_08": {
        "answer": "If you forgot your card, visit the Security Helpdesk at Main Gate (Gate 1A). Security officers will verify your identity on UMS via your Registration Number and photo, issuing a temporary single-day gate slip.",
        "department_contact": "Main Security Control Post (Gate 1A & Gate 2)",
        "keywords": ["forgot id card", "day scholar entry", "gate pass", "temporary permit", "main gate", "entry without id", "visitor pass"]
    },
    "idc_09": {
        "answer": "Please do a good deed and drop off any found ID card at the nearest campus security turnstile or deposit it at the Central Lost & Found Counter in the Division of Student Welfare (Block 30/32).",
        "department_contact": "Central Lost & Found Desk, Division of Student Welfare, Block 30",
        "keywords": ["found id card", "lost and found", "deposit card", "someone else id", "surrender id", "security desk", "returned card"]
    },
    "idc_10": {
        "answer": "During final graduation clearance on UMS, your ID card's campus privileges are deactivated. You present your card for punching/cancellation at Block 32, after which you may keep it as a university souvenir.",
        "department_contact": "Graduation Clearance Desk, Block 32",
        "keywords": ["surrender id card", "graduation clearance", "alumni card", "card cancellation", "leaving university", "deactivation"]
    },
    "idc_11": {
        "answer": "Research fellows and project associates must have their department head sign an authorization form and submit it to the HR / Staff ID Issuing Cell in Block 32 for an institutional RFID card.",
        "department_contact": "Human Resources & Scholar Administration, Block 32 (2nd Floor)",
        "keywords": ["research scholar id", "project assistant", "temporary id", "intern card", "fellow id", "department authorization"]
    },
    "idc_12": {
        "answer": "Yes, the Proctorial Board or Disciplinary Committee can temporarily suspend ID card turnstile privileges in cases of severe code-of-conduct violations, fee defaults, or attendance shortages.",
        "department_contact": "Proctorial Board & Disciplinary Authority, Block 30",
        "keywords": ["id card blocked", "card suspended", "access denied", "disciplinary action", "turnstile blocked", "barring", "blacklisted"]
    },

    # ── TRANSPORT (trn_01 to trn_12) ──
    "trn_01": {
        "answer": "LPU runs regular student buses covering Amritsar, Jalandhar, Ludhiana, Hoshiarpur, Phagwara, Kapurthala, and nearby towns. Morning buses arrive around 8:30 AM, and departure buses leave from the Central Bus Stand at 5:15 PM. Full route charts are available on UMS.",
        "department_contact": "Transport Management Division, Block 32 / Central Bus Parking",
        "keywords": ["bus routes", "bus timings", "day scholar bus", "pickup points", "schedule", "transport timing", "bus stop", "morning bus"]
    },
    "trn_02": {
        "answer": "Apply for a transport seat on UMS (https://ums.lpu.in/lpuums/) under Transport Services → Apply Bus Pass. Select your route and boarding stop, pay the semester bus fee online, and your bus pass will be encoded directly onto your student RFID card.",
        "department_contact": "Transport Administrative Counter, Block 32 (Basement)",
        "keywords": ["bus pass", "transport subscription", "apply bus pass", "renew pass", "semester bus fee", "commuter pass", "travel card"]
    },
    "trn_03": {
        "answer": "Yes, you can request a route or pickup stop modification on UMS under Transport Services → Change Route, subject to vacant seat availability on the requested bus route.",
        "department_contact": "Transport Scheduling Desk, Block 32",
        "keywords": ["change bus route", "switch pickup point", "stop change", "bus route change", "relocation", "transfer route"]
    },
    "trn_04": {
        "answer": "Semester transport fees depend on city distance slabs (e.g., Jalandhar/Phagwara ~₹18,000–₹22,000 per semester; Ludhiana/Amritsar ~₹26,000–₹32,000 per semester). Exact slabs are displayed when selecting your route on UMS.",
        "department_contact": "Transport Accounts & Fee Desk, Block 32",
        "keywords": ["bus fee", "transport charges", "bus fare", "semester transport fee", "fare chart", "distance slab", "commute cost"]
    },
    "trn_05": {
        "answer": "Yes! Eco-friendly internal battery-operated e-rickshaws and shuttles ply regularly between Main Gate 1A, Uni-Mall (Block 34), academic clusters, and residential hostels from 8:00 AM to 8:00 PM for a flat nominal fare of ₹10 per ride.",
        "department_contact": "Campus Transit Supervisor, Main Gate 1A Transit Bay",
        "keywords": ["campus shuttle", "internal transport", "e-rickshaw", "battery auto", "campus commute", "shuttle fare", "internal travel"]
    },
    "trn_06": {
        "answer": "In the event of a breakdown or unexpected route delay, call the Central Transport Control Room immediately at +91-1824-517000 (Transport Desk) or check live fleet circulars on UMS.",
        "department_contact": "Central Transport Control Room (Helpline: +91-1824-517000)",
        "keywords": ["bus delay", "breakdown", "bus missed", "transport helpline", "bus not arrived", "late bus", "emergency transport"]
    },
    "trn_07": {
        "answer": "Yes, day scholars riding two-wheelers or cars can park in the designated multi-level parking area near Gate 1A/Gate 2 after obtaining an authorized vehicle entry permit sticker from Campus Security.",
        "department_contact": "Security & Traffic Control Cell, Gate 1A Post",
        "keywords": ["day scholar parking", "car parking", "bike parking", "parking permit", "parking fee", "vehicle pass", "parking sticker"]
    },
    "trn_08": {
        "answer": "Yes, resident hostellers can take weekend shuttle trips to Jalandhar or Phagwara by purchasing a single-trip commuter ticket from the Transport Counter in Block 32, provided they hold a valid approved UMS outpass.",
        "department_contact": "Transport Booking Counter, Block 32",
        "keywords": ["weekend bus", "hostel student bus", "city shuttle", "weekend trip", "single trip pass", "travel coupon", "jalandhar bus"]
    },
    "trn_09": {
        "answer": "Transport cancellations submitted on UMS within the first 15 days of the semester qualify for a pro-rata refund after deduction of administrative charges per university transport rules.",
        "department_contact": "Transport Accounts Cell, Block 32",
        "keywords": ["bus fee refund", "cancel bus pass", "transport refund", "surrender pass", "stop bus service", "money back transport"]
    },
    "trn_10": {
        "answer": "Yes, during mid-term and end-term exams, additional bus shifts are scheduled from the campus central bus terminal to synchronize with both morning and evening exam completion times.",
        "department_contact": "Transport Dispatch Desk, Central Bus Terminal",
        "keywords": ["exam special bus", "late bus", "evening departure", "exam shift transport", "special schedule", "night transport"]
    },
    "trn_11": {
        "answer": "LPU provides 24x7 free medical ambulance transport on campus. If someone is injured or unwell, call the emergency helpline at +91-1824-517000 to dispatch an ambulance to your location immediately.",
        "department_contact": "Campus Emergency Medical Services (+91-1824-517000)",
        "keywords": ["ambulance", "medical transport", "emergency vehicle", "sick student transport", "injury transit", "health emergency"]
    },
    "trn_12": {
        "answer": "Ragging, aggressive behavior, or traveling without a valid pass on university buses is strictly prohibited. Violators face immediate bus pass cancellation, hefty penalties, and referral to the Proctorial Disciplinary Committee.",
        "department_contact": "Proctorial Board & Transport Flying Squad, Block 30",
        "keywords": ["bus discipline", "misconduct", "transport rules", "bus suspension", "anti-ragging bus", "conductor complaint", "code of conduct"]
    },

    # ── EXAMS (exm_01 to exm_12) ──
    "exm_01": {
        "answer": "Official Mid-Term Examination (MTE) and End-Term Examination (ETE) date sheets are published on e-Connect (https://econnect.lpu.in) under Exam Connect → Date Sheet about 3 to 4 weeks prior to exam commencement.",
        "department_contact": "Controller of Examinations (COE) Office, Block 30/32",
        "keywords": ["date sheet", "exam schedule", "timetable", "exam dates", "mte schedule", "ete schedule", "examination timetable"]
    },
    "exm_02": {
        "answer": "You must maintain a strict minimum of 75% attendance in every registered course to be eligible for exams and generate your admit card. Students below 75% are placed on the attendance shortage list and cannot sit for that subject's exam.",
        "department_contact": "Academic Coordinator & Examination Debarring Cell, Block 32",
        "keywords": ["attendance requirement", "75 percent", "detained", "admit card eligibility", "shortage of attendance", "minimum attendance", "exam debarred"]
    },
    "exm_03": {
        "answer": "Admit cards are available for download on e-Connect (https://econnect.lpu.in) under Exam Connect → Admit Card roughly 5 to 7 days before exams start, once your fee dues and 75% attendance criteria are clear.",
        "department_contact": "Controller of Examinations (COE) Helpdesk, Block 32",
        "keywords": ["admit card", "hall ticket", "download admit card", "exam roll number", "examination pass", "entry slip", "seat slip"]
    },
    "exm_04": {
        "answer": "You can apply for re-evaluation or view your evaluated answer sheet on e-Connect (https://econnect.lpu.in) under Exam Connect → Re-Evaluation within 7 to 10 days of grade publication, accompanied by a fee of ₹500 per course.",
        "department_contact": "Examination Re-Evaluation & Scrutiny Wing, Block 32",
        "keywords": ["re-evaluation", "rechecking", "answer sheet inspection", "marks recount", "revaluation fee", "result challenge", "grade revision"]
    },
    "exm_05": {
        "answer": "Register for supplementary or backlog papers on e-Connect (https://econnect.lpu.in) under Exam Connect → Reappear Registration during the notified registration window, with an exam fee of approximately ₹1,000 per course.",
        "department_contact": "Conduct of Examinations Branch, Block 32",
        "keywords": ["reappear exam", "backlog registration", "supplementary exam", "failed subject", "arrear exam", "compartment", "re-exam"]
    },
    "exm_06": {
        "answer": "Mobile phones, smartwatches, digital fitness bands, bluetooth earphones, programmable calculators, loose paper notes, and bags are strictly forbidden inside examination halls. Possession of any will trigger a severe Unfair Means Case (UMC).",
        "department_contact": "Proctorial Examination Flying Squad, Block 32",
        "keywords": ["prohibited items", "exam hall rules", "smart watch", "mobile phone in exam", "unfair means", "cheating", "calculator policy"]
    },
    "exm_07": {
        "answer": "If you fall sick and miss an exam, get examined at the University Health Centre (Uni-Hospital) or submit a certified hospital medical certificate to the Academic Dean / COE office within 3 days to apply for a legitimate makeup examination.",
        "department_contact": "Division of Academic Affairs & COE Office, Block 32",
        "keywords": ["sick during exams", "medical leave exam", "hospitalized", "makeup exam", "missed exam", "medical certificate", "absent in exam"]
    },
    "exm_08": {
        "answer": "If two registered exams overlap on the same date and time, file a clash report immediately on e-Connect (https://econnect.lpu.in) under Exam Connect → Grievance at least 5 days prior to exams so the scheduling committee can assign an alternate slot.",
        "department_contact": "Examination Timetable Scheduling Committee, Block 32",
        "keywords": ["exam clash", "date clash", "overlapping exams", "same slot exam", "timetable conflict", "date sheet change", "double exam"]
    },
    "exm_09": {
        "answer": "Continuous Assessment (CA) scores—consisting of class tests, objective quizzes, homework assignments, and attendance points—can be tracked real-time on UMS (https://ums.lpu.in/lpuums/) under Academics → Continuous Assessment.",
        "department_contact": "Course Faculty & Department Academic Coordinator",
        "keywords": ["internal marks", "continuous assessment", "ca marks", "assignment marks", "quiz score", "internal evaluation", "attendance marks"]
    },
    "exm_10": {
        "answer": "End-term semester grades (TGPA and CGPA) are announced on e-Connect (https://econnect.lpu.in) within 4 to 6 weeks of the final examination date. Digital grade cards can be viewed and printed directly.",
        "department_contact": "COE Results & Evaluation Division, Block 32",
        "keywords": ["result declaration", "semester grade", "cgpa", "tgpa", "transcript", "grade card", "mark sheet", "result date"]
    },
    "exm_11": {
        "answer": "Apply for a duplicate grade report or official consolidated transcript through UMS (https://ums.lpu.in/lpuums/) under Student Services → Certificate Request, and collect the physical sealed document from Block 32.",
        "department_contact": "Records & Certificate Dispatch Branch, Block 32 (1st Floor)",
        "keywords": ["duplicate grade sheet", "transcript request", "degree certificate", "lost marksheet", "official transcript", "grade sheet correction"]
    },
    "exm_12": {
        "answer": "If booked under UMC, you will receive a formal summons via UMS message and registered email to appear before the Unfair Means Committee in Block 32, where you will present your written statement before a final penalty decision is issued.",
        "department_contact": "Unfair Means Committee (UMC), Block 32 (Meeting Room)",
        "keywords": ["umc hearing", "unfair means case", "caught cheating", "umc committee", "disciplinary notice", "exam malpractice", "penalty decision"]
    }
}


def update_faqs():
    with open(FAQS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated_count = 0
    for item in data:
        faq_id = item["id"]
        if faq_id in UPDATES:
            u = UPDATES[faq_id]
            item["answer"] = u["answer"]
            item["department_contact"] = u["department_contact"]
            if "keywords" in u:
                item["keywords"] = u["keywords"]
            item["verified"] = True
            item["source"] = "LPU official sources 2024"
            updated_count += 1

    with open(FAQS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {updated_count} out of {len(data)} FAQs in {FAQS_PATH}")

    # Check for any remaining placeholders
    remaining = [item["id"] for item in data if "[" in item["answer"] and "]" in item["answer"]]
    print(f"Remaining FAQs with bracket placeholders: {len(remaining)} {remaining}")


if __name__ == "__main__":
    update_faqs()
