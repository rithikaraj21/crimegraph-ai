#!/usr/bin/env python3
"""
CrimeGraph AI - synthetic investigation dataset generator (v1)

Everything here is FICTIONAL. Only the Chennai area names/coordinates are real
public places (approximate centroids). People, phones, accounts, IPs and events
are invented. IP addresses come from the RFC 5737 documentation ranges.

Run:  python generate_dataset.py         (same seed -> same dataset every time)

Outputs (in ./crimegraph_dataset):
  csv/            tables to load into Neo4j
  case_reports/   free-text reports (input for the AI extraction step)
  ground_truth/   the correct entities/relations for every report (to score the AI)
  graph.json      nodes + edges for front-end development without Neo4j
"""
import csv, json, os, random, re
from datetime import datetime, timedelta
from collections import defaultdict

SEED = 2026
random.seed(SEED)
R = random.Random(SEED + 1)          # separate RNG for report wording
OUT = "crimegraph_dataset"
TZ = "+05:30"
for sub in ("csv", "case_reports", "ground_truth"):
    os.makedirs(f"{OUT}/{sub}", exist_ok=True)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fdate(iso):
    y, m, d = map(int, iso[:10].split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def inr(n):
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def write_csv(name, header, rows):
    with open(f"{OUT}/csv/{name}", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ----------------------------------------------------------------------------
# 1. MASTER DATA
# ----------------------------------------------------------------------------
LOCATIONS = [
    ("L001", "Chennai Central", 13.0827, 80.2707, "Railway Station"),
    ("L002", "Guindy", 13.0067, 80.2206, "Locality"),
    ("L003", "T. Nagar", 13.0418, 80.2341, "Shopping Area"),
    ("L004", "Marina Beach", 13.0500, 80.2824, "Beach"),
    ("L005", "Egmore", 13.0732, 80.2609, "Railway Station"),
    ("L006", "Adyar", 13.0012, 80.2565, "Locality"),
    ("L007", "Anna Nagar", 13.0850, 80.2101, "Locality"),
    ("L008", "Velachery", 12.9815, 80.2180, "Locality"),
    ("L009", "Tambaram", 12.9249, 80.1000, "Locality"),
    ("L010", "Koyambedu", 13.0694, 80.1948, "Market"),
    ("L011", "Mylapore", 13.0339, 80.2699, "Locality"),
    ("L012", "Nungambakkam", 13.0569, 80.2425, "Locality"),
    ("L013", "Porur", 13.0382, 80.1565, "Locality"),
    ("L014", "Perungudi", 12.9653, 80.2461, "IT Corridor"),
    ("L015", "Besant Nagar", 13.0002, 80.2668, "Locality"),
    ("L016", "Royapettah", 13.0543, 80.2646, "Locality"),
    ("L017", "Ambattur", 13.1143, 80.1548, "Industrial Area"),
    ("L018", "Sholinganallur", 12.9010, 80.2279, "IT Corridor"),
]
LOC = {l[0]: dict(name=l[1], lat=l[2], lon=l[3], type=l[4]) for l in LOCATIONS}

# id, name, role, alias, home location.  Roles are deliberately non-accusatory.
PERSONS = [
    ("P001", "Arun Kumar", "Person of Interest", "AK", "L011"),
    ("P002", "Bala Murugan", "Person of Interest", "Bala", "L016"),
    ("P003", "Karthik Raja", "Person of Interest", "Karthi", "L017"),
    ("P004", "Dinesh Babu", "Associate", "Dinesh", "L012"),
    ("P005", "Selvam Pillai", "Associate", "Selvam", "L016"),
    ("P006", "Ravi Shankar", "Victim", "", "L007"),
    ("P007", "Meena Devi", "Witness", "", "L016"),
    ("P008", "Lakshmi Narayanan", "Victim", "Lakshmi N", "L011"),
    ("P009", "Suresh Iyer", "Victim", "", "L003"),
    ("P010", "Priya Nair", "Witness", "", "L012"),
    ("P011", "Vignesh Anand", "Person of Interest", "Vicky", "L008"),
    ("P012", "Harini Sekar", "Account Holder", "", "L018"),
    ("P013", "Mohan Das", "Account Holder", "", "L013"),
    ("P014", "Kavya Reddy", "Victim", "", "L006"),
    ("P015", "Ismail Khan", "Victim", "", "L007"),
    ("P016", "Deepak Joseph", "Victim", "", "L006"),
    ("P017", "Naveen Chandran", "Person of Interest", "Naveen C", "L014"),
    ("P018", "Sathish Kumar", "Associate", "Sathish K", "L010"),
    ("P019", "Roshan Ali", "Associate", "", "L014"),
    ("P020", "Anitha Balaji", "Victim", "", "L010"),
    ("P021", "Prakash Venkat", "Victim", "", "L014"),
    ("P022", "Gopal Krishnan", "Witness", "", "L009"),
    ("P023", "Thenmozhi Rajan", "Witness", "", "L009"),
    ("P024", "Yusuf Basha", "Victim", "", "L009"),
    ("P025", "Manoj Kannan", "Associate", "", "L017"),
    ("P026", "Rekha Subramani", "Account Holder", "", "L015"),
    ("P027", "Ajay Menon", "Associate", "", "L002"),
    ("P028", "Divya Prakash", "Witness", "", "L013"),
    ("P029", "Senthil Nathan", "Person of Interest", "Senthil", "L009"),
    ("P030", "Farook Ahmed", "Associate", "Farook", "L009"),
    ("P031", "Nithya Raman", "Bank Officer", "", "L012"),
    ("P032", "Rajesh Pandian", "Associate", "", "L018"),
    ("P033", "Swathi Mohan", "Victim", "", "L008"),
    ("P034", "Ganesh Babu", "Witness", "", "L005"),
    ("P035", "Usha Rani", "Witness", "", "L005"),
    ("P036", "Tamilselvan", "Associate", "", "L009"),
    ("P037", "Vimal Raj", "Associate", "", "L003"),
    ("P038", "Pooja Sharma", "Victim", "", "L002"),
    ("P039", "Kishore Kumar", "Associate", "", "L015"),
    ("P040", "Ilakkiya Mohan", "Witness", "", "L001"),
]
PERS = {p[0]: dict(name=p[1], role=p[2], alias=p[3], home=p[4]) for p in PERSONS}

# devices: D001..D040 = phone of P001..P040 ; D041.. extras
DEVICES = []
_kinds = ["Android smartphone", "Android smartphone", "iOS smartphone", "Feature phone"]
for i in range(1, 41):
    DEVICES.append((f"D{i:03d}", "Phone", f"+91-90000-{10000 + i}", f"P{i:03d}", R.choice(_kinds)))
DEVICES += [
    ("D041", "Phone", "+91-90000-10041", "P001", "Secondary handset (second SIM)"),
    ("D042", "Laptop", "LAP-0042", "P017", "Windows laptop"),
    ("D043", "Desktop PC", "PC-SHOP-01", "P020", "Windows desktop PC (shop billing system)"),
]
DEV = {d[0]: dict(type=d[1], identifier=d[2], owner=d[3], desc=d[4]) for d in DEVICES}
DEVTYPE_WORD = {"Phone": "phone", "Laptop": "laptop", "Desktop PC": "computer"}

CASES = [
    ("C001", "Central Chennai Robbery Series", "Open - under investigation", "2026-09-15"),
    ("C002", "Mule Account UPI Fraud Ring", "Open - under investigation", "2026-09-11"),
    ("C003", "Phishing and Malware Campaign", "Open - under investigation", "2026-09-06"),
    ("C004", "Tambaram Vehicle Theft", "Open - under investigation", "2026-08-31"),
]
CASE = {c[0]: dict(title=c[1], status=c[2], opened=c[3]) for c in CASES}

# id, case, type, date, time, location, summary
INCIDENTS = [
    ("I001", "C001", "Robbery", "2026-09-20", "21:15", "L001",
     "Passenger robbed of a bag near the station entrance in the evening."),
    ("I002", "C001", "Chain Snatching", "2026-09-14", "19:40", "L005",
     "Gold chain snatched from a pedestrian by two riders on a motorcycle."),
    ("I003", "C001", "Shop Robbery", "2026-09-25", "20:30", "L003",
     "Cash counter of a textile shop robbed shortly before closing."),
    ("I004", "C002", "UPI Fraud", "2026-09-22", "11:20", "L002",
     "Victim tricked into paying through a fake refund request."),
    ("I005", "C002", "UPI Fraud", "2026-09-10", "15:05", "L006",
     "Two victims paid a fake online seller and never received goods."),
    ("I006", "C002", "Investment Fraud", "2026-09-27", "17:45", "L008",
     "Victim transferred a large sum to a fake trading platform."),
    ("I007", "C003", "Phishing Campaign", "2026-09-05", "10:10", "L007",
     "Victim clicked a fake bank e-mail link and lost money."),
    ("I008", "C003", "Malware Infection", "2026-09-18", "09:30", "L010",
     "Shop billing computer found infected with suspicious software."),
    ("I009", "C003", "Data Theft", "2026-09-26", "14:25", "L014",
     "Complainant's device found sending data to an unknown server."),
    ("I010", "C004", "Vehicle Theft", "2026-08-30", "22:00", "L009",
     "Two-wheeler stolen from a parking area at night."),
]
INC = {i[0]: dict(case=i[1], type=i[2], date=i[3], time=i[4], loc=i[5], summary=i[6]) for i in INCIDENTS}

ACCOUNTS = [  # id, holder, bank
    ("AC001", "P001", "Coastal Bank"), ("AC002", "P002", "Metro Cooperative Bank"),
    ("AC003", "P003", "Sunrise Bank"), ("AC004", "P004", "Coastal Bank"),
    ("AC005", "P011", "Sunrise Bank"), ("AC006", "P012", "Metro Cooperative Bank"),
    ("AC007", "P013", "Coastal Bank"), ("AC008", "P026", "Sunrise Bank"),
    ("AC009", "P027", "Metro Cooperative Bank"), ("AC010", "P017", "Coastal Bank"),
    ("AC011", "P019", "Sunrise Bank"), ("AC012", "P018", "Metro Cooperative Bank"),
    ("AC013", "P014", "Coastal Bank"), ("AC014", "P015", "Sunrise Bank"),
    ("AC015", "P016", "Metro Cooperative Bank"), ("AC016", "P033", "Coastal Bank"),
    ("AC017", "P038", "Sunrise Bank"), ("AC018", "P025", "Metro Cooperative Bank"),
    ("AC019", "P005", "Coastal Bank"),
]
ACC = {}
for n, (aid, holder, bank) in enumerate(ACCOUNTS, 1):
    ACC[aid] = dict(holder=holder, bank=bank, masked=f"XXXXXX{4000 + n}")

IPS = {
    "IP001": dict(address="203.0.113.50", label="Malicious-C&C"),
    "IP002": dict(address="198.51.100.23", label="Malicious-Phishing"),
    "IP003": dict(address="192.0.2.10", label="Benign"),
    "IP004": dict(address="198.51.100.77", label="Benign"),
}

EVIDENCE = [  # id, type, case, description, collected, source report
    ("E001", "CCTV Footage", "C001", "CCTV video from the station entrance", "2026-09-21", "R001"),
    ("E002", "Witness Statement", "C001", "signed statement of a bystander", "2026-09-21", "R001"),
    ("E003", "CCTV Footage", "C001", "CCTV video from a shop near the railway station", "2026-09-15", "R004"),
    ("E004", "Witness Statement", "C001", "statement of a passer-by", "2026-09-15", "R004"),
    ("E005", "CCTV Footage", "C001", "CCTV video from the shopping street", "2026-09-26", "R005"),
    ("E006", "CDR Extract", "C001", "call detail records for the handsets of interest", "2026-09-24", "R003"),
    ("E007", "Bank Statement Extract", "C002", "account statement extract shared by the bank", "2026-09-29", "R010"),
    ("E008", "Complaint Screenshot", "C002", "screenshots of the fraudulent payment request", "2026-09-23", "R007"),
    ("E009", "Complaint Screenshot", "C002", "screenshots of the fake seller chat", "2026-09-11", "R008"),
    ("E010", "Complaint Screenshot", "C002", "screenshots of the fake trading platform", "2026-09-28", "R009"),
    ("E011", "Forensic Image", "C003", "disk image of the shop billing computer", "2026-09-19", "R013"),
    ("E012", "Malware Sample", "C003", "suspicious executable recovered from the shop computer", "2026-09-19", "R013"),
    ("E013", "Phishing Email Sample", "C003", "copy of the phishing e-mail received by the complainant", "2026-09-06", "R012"),
    ("E014", "Network Log Extract", "C003", "network log extract from the complainant's device", "2026-09-27", "R014"),
    ("E015", "CCTV Footage", "C004", "CCTV video from the parking area", "2026-08-31", "R016"),
    ("E016", "Seized Item", "C001", "handwritten notebook with contact details", "2026-09-27", "R019"),
]
EV = {e[0]: dict(type=e[1], case=e[2], desc=e[3], collected=e[4], doc=e[5]) for e in EVIDENCE}

# ----------------------------------------------------------------------------
# 2. CALLS  (device -> device call detail records)
# ----------------------------------------------------------------------------
W0 = datetime(2026, 8, 25)


def dt(iso_date, hhmm):
    return datetime.fromisoformat(f"{iso_date}T{hhmm}:00")


BURSTS = {
    "G1": [("I002",), ("I001",), ("I003",)],
    "G2": [("I005",), ("I004",), ("I006",)],
    "G3": [("I007",), ("I008",), ("I009",)],
    "G4": [("I010",)],
}
# (caller person, callee person, number of calls, group, report that documents the pair)
PAIRS = [
    ("P001", "P002", 12, "G1", "R003"), ("P001", "P003", 9, "G1", "R003"),
    ("P002", "P003", 8, "G1", "R003"), ("P001", "P004", 6, "G1", "R003"),
    ("P002", "P005", 7, "G1", "R003"), ("P003", "P005", 3, "G1", "R003"),
    ("P004", "P005", 4, "G1", "R003"),
    ("P011", "P012", 10, "G2", "R011"), ("P011", "P013", 7, "G2", "R011"),
    ("P011", "P026", 6, "G2", "R011"), ("P011", "P027", 8, "G2", "R011"),
    ("P012", "P013", 3, "G2", "R011"), ("P027", "P026", 4, "G2", "R011"),
    ("P011", "P018", 5, "G2", "R011"),          # bridge: fraud ring <-> cyber ring
    ("P017", "P018", 11, "G3", "R015"), ("P017", "P019", 9, "G3", "R015"),
    ("P018", "P019", 5, "G3", "R015"), ("P017", "P025", 6, "G3", "R015"),
    ("P019", "P025", 4, "G3", "R015"),
    ("P029", "P030", 7, "G4", "R018"), ("P029", "P036", 5, "G4", "R018"),
    ("P030", "P036", 4, "G4", "R018"),
    ("P030", "P004", 2, "G4", "R018"),          # weak link: vehicle case <-> robbery ring
]
phone_of = lambda pid: "D" + pid[1:]

calls = []
for a, b, n, grp, _doc in PAIRS:
    for _ in range(n):
        caller, callee = (a, b) if random.random() < 0.6 else (b, a)
        if BURSTS[grp] and random.random() < 0.45:
            inc = INC[random.choice(BURSTS[grp])[0]]
            base = dt(inc["date"], inc["time"])
            ts = base - timedelta(hours=random.uniform(1, 36))
            loc = inc["loc"] if random.random() < 0.6 else PERS[caller]["home"]
            dur = random.randint(15, 200)
        else:
            day = W0 + timedelta(days=random.randint(0, 34))
            ts = day.replace(hour=random.randint(8, 23), minute=random.randint(0, 59),
                             second=random.randint(0, 59))
            loc = PERS[caller]["home"]
            dur = random.randint(30, 900)
        calls.append((ts, phone_of(caller), phone_of(callee), dur, loc))
calls.sort()
call_rows = [(f"CL{i:04d}", c[1], c[2], c[0].strftime(f"%Y-%m-%dT%H:%M:%S{TZ}"), c[3], c[4])
             for i, c in enumerate(calls, 1)]

# aggregated person-level CONTACTED stats
contact_stats = {}
for a, b, n, grp, doc in PAIRS:
    da, db = phone_of(a), phone_of(b)
    ts = sorted(c[0] for c in calls if {c[1], c[2]} == {da, db})
    contact_stats[(a, b)] = dict(count=len(ts), first=ts[0].strftime("%Y-%m-%d"),
                                 last=ts[-1].strftime("%Y-%m-%d"), doc=doc)
    assert len(ts) == n

# ----------------------------------------------------------------------------
# 3. TRANSACTIONS
# ----------------------------------------------------------------------------
# key, from, to (None = ATM cash withdrawal), amount, date, channel, atm location, report
TXN_DEF = [
    ("t_p14", "AC013", "AC006", 45000, "2026-09-10", "UPI", None, "R008"),
    ("t_p16", "AC015", "AC006", 30000, "2026-09-10", "UPI", None, "R008"),
    ("t_l1", "AC006", "AC005", 40000, "2026-09-11", "IMPS", None, "R010"),
    ("t_atm1", "AC005", None, 20000, "2026-09-12", "ATM", "L002", "R010"),
    ("t_l2", "AC006", "AC005", 28000, "2026-09-13", "IMPS", None, "R010"),
    ("t_p38", "AC017", "AC007", 62000, "2026-09-22", "UPI", None, "R007"),
    ("t_l3", "AC007", "AC005", 55000, "2026-09-23", "IMPS", None, "R010"),
    ("t_atm2", "AC005", None, 25000, "2026-09-24", "ATM", "L006", "R010"),
    ("t_p33", "AC016", "AC008", 120000, "2026-09-27", "UPI", None, "R009"),
    ("t_l4", "AC008", "AC009", 100000, "2026-09-28", "IMPS", None, "R010"),
    ("t_l5", "AC009", "AC005", 90000, "2026-09-28", "IMPS", None, "R010"),
    ("t_atm3", "AC005", None, 50000, "2026-09-28", "ATM", "L008", "R010"),
    ("t_b1", "AC003", "AC006", 25000, "2026-09-21", "UPI", None, "R006"),   # robbery ring -> fraud mule (hidden link)
    ("t_b2", "AC001", "AC004", 10000, "2026-09-21", "UPI", None, "R006"),
    ("t_b3", "AC002", "AC019", 8000, "2026-09-21", "UPI", None, "R006"),
    ("t_c0", "AC014", "AC011", 18500, "2026-09-06", "UPI", None, "R012"),
    ("t_c1", "AC010", "AC011", 15000, "2026-09-20", "UPI", None, "R015"),
    ("t_c2", "AC011", "AC012", 6000, "2026-09-22", "UPI", None, "R015"),
    ("t_c3", "AC018", "AC010", 4000, "2026-09-27", "UPI", None, "R015"),
    ("t_c4", "AC012", "AC005", 9000, "2026-09-24", "UPI", None, "R015"),   # cyber ring -> fraud ring (bridge)
    ("t_n1", "AC001", "AC002", 1200, "2026-08-29", "UPI", None, "BANK-DB-EXTRACT"),
    ("t_n2", "AC002", "AC003", 800, "2026-09-02", "UPI", None, "BANK-DB-EXTRACT"),
    ("t_n3", "AC018", "AC012", 2200, "2026-09-08", "UPI", None, "BANK-DB-EXTRACT"),
    ("t_n4", "AC014", "AC013", 1500, "2026-09-03", "UPI", None, "BANK-DB-EXTRACT"),
]
_tx = []
for key, fa, ta, amt, d, ch, atm, doc in TXN_DEF:
    ts = dt(d, "00:00").replace(hour=random.randint(9, 20), minute=random.randint(0, 59))
    _tx.append((ts, key, fa, ta, amt, ch, atm, doc))
_tx.sort()
TXN = {}
txn_rows = []
for i, (ts, key, fa, ta, amt, ch, atm, doc) in enumerate(_tx, 1):
    tid = f"TX{i:03d}"
    TXN[key] = dict(id=tid, frm=fa, to=ta, amount=amt, date=ts.strftime("%Y-%m-%d"), channel=ch, atm=atm)
    txn_rows.append((tid, fa, ta or "", amt, ts.strftime(f"%Y-%m-%dT%H:%M:%S{TZ}"), ch, atm or "", doc))

# ----------------------------------------------------------------------------
# 4. NETWORK EVENTS  (modelled on CTU-13 / IoT-23 flow records; RFC 5737 IPs)
# ----------------------------------------------------------------------------
net_ev = []


def add_ev(dev, ip, start, n, step_min, label, port, proto="TCP"):
    t = start
    for _ in range(n):
        net_ev.append((t, dev, ip, proto, port, random.randint(300, 90000), label))
        t += timedelta(minutes=step_min + random.randint(-3, 3))


add_ev("D042", "IP002", datetime(2026, 9, 3, 22, 10), 6, 95, "Malicious-Phishing", 443)
add_ev("D042", "IP001", datetime(2026, 9, 17, 23, 5), 6, 30, "Malicious-C&C", 8080)
add_ev("D043", "IP001", datetime(2026, 9, 18, 6, 40), 8, 30, "Malicious-C&C", 8080)
add_ev("D021", "IP001", datetime(2026, 9, 26, 10, 15), 3, 40, "Malicious-C&C", 8080)
add_ev("D042", "IP003", datetime(2026, 9, 2, 11, 0), 3, 240, "Benign", 443)
add_ev("D043", "IP004", datetime(2026, 9, 16, 10, 0), 3, 180, "Benign", 443)
add_ev("D021", "IP004", datetime(2026, 9, 25, 9, 0), 2, 200, "Benign", 443)
add_ev("D017", "IP003", datetime(2026, 9, 12, 14, 0), 3, 300, "Benign", 80)
net_ev.sort()
net_rows = [(f"NE{i:04d}", e[1], e[2], e[0].strftime(f"%Y-%m-%dT%H:%M:%S{TZ}"), e[3], e[4], e[5], e[6])
            for i, e in enumerate(net_ev, 1)]


def first_event(dev, ip):
    return min(e[0] for e in net_ev if e[1] == dev and e[2] == ip).strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# 5. REPORTS: facts -> sentences + ground truth + relationships.csv rows
# ----------------------------------------------------------------------------
def etype(eid):
    if eid.startswith("IP"): return "IPAddress"
    if eid.startswith("AC"): return "Account"
    return {"P": "Person", "D": "Device", "L": "Location", "I": "Incident",
            "C": "Case", "E": "Evidence"}[eid[0]]


G1 = [p for p in PAIRS if p[3] == "G1"]
G2 = [p for p in PAIRS if p[3] == "G2"]
G3 = [p for p in PAIRS if p[3] == "G3"]
G4 = [p for p in PAIRS if p[3] == "G4"]
contacts = lambda grp: [("contacted", a, b) for a, b, *_ in grp]
occ = lambda i: [("occurred", i), ("part_of", i)]

REPORTS = [
    dict(id="R001", type="First Information Report (FIR)", case="C001", date="2026-09-21", slug="FIR_I001",
         intro="This report records a complaint received at the jurisdictional police station.",
         facts=occ("I001") + [("victim", "P006", "I001"), ("witness", "P007", "I001"),
                              ("visited", "P002", "L001", "2026-09-20"),
                              ("supports", "E001", "I001"), ("supports", "E002", "I001"),
                              ("provided", "P007", "E002")]),
    dict(id="R002", type="Witness Statement", case="C001", date="2026-09-21", slug="WITNESS_I001",
         intro="This statement was recorded from persons who were near the location at the time.",
         facts=[("occurred", "I001"), ("witness", "P007", "I001"), ("witness", "P040", "I001"),
                ("visited", "P001", "L001", "2026-09-20")]),
    dict(id="R003", type="Call Records Analysis Note", case="C001", date="2026-09-24", slug="CDR_C001",
         intro="This note summarises call detail records obtained for handsets linked to the case.",
         facts=[("uses", "P001", "D001"), ("uses", "P001", "D041"), ("uses", "P002", "D002"),
                ("uses", "P003", "D003"), ("uses", "P004", "D004"), ("uses", "P005", "D005"),
                ("uses", "P005", "D002")] + contacts(G1) +
               [("derived", "E006", d) for d in ("D001", "D002", "D003", "D004", "D005")]),
    dict(id="R004", type="First Information Report (FIR)", case="C001", date="2026-09-15", slug="FIR_I002",
         intro="This report records a complaint received at the jurisdictional police station.",
         facts=occ("I002") + [("victim", "P008", "I002"), ("witness", "P034", "I002"),
                              ("witness", "P035", "I002"), ("visited", "P003", "L005", "2026-09-14"),
                              ("supports", "E003", "I002"), ("supports", "E004", "I002"),
                              ("provided", "P034", "E004")]),
    dict(id="R005", type="First Information Report (FIR)", case="C001", date="2026-09-26", slug="FIR_I003",
         intro="This report records a complaint received at the jurisdictional police station.",
         facts=occ("I003") + [("victim", "P009", "I003"), ("witness", "P010", "I003"),
                              ("witness", "P028", "I003"), ("visited", "P001", "L003", "2026-09-25"),
                              ("visited", "P004", "L003", "2026-09-25"), ("supports", "E005", "I003")]),
    dict(id="R006", type="Bank Transaction Analysis Note", case="C001", date="2026-09-28", slug="BANK_C001",
         intro="This note summarises bank account records requested for the case.",
         facts=[("owns", "P001", "AC001"), ("owns", "P002", "AC002"), ("owns", "P003", "AC003"),
                ("owns", "P004", "AC004"), ("owns", "P005", "AC019"),
                ("txn", "t_b1"), ("txn", "t_b2"), ("txn", "t_b3")]),
    dict(id="R007", type="First Information Report (FIR)", case="C002", date="2026-09-23", slug="FIR_I004",
         intro="This report records a cyber-fraud complaint received at the cyber crime cell.",
         facts=occ("I004") + [("victim", "P038", "I004"), ("owns", "P038", "AC017"),
                              ("txn", "t_p38"), ("supports", "E008", "I004")]),
    dict(id="R008", type="First Information Report (FIR)", case="C002", date="2026-09-11", slug="FIR_I005",
         intro="This report records a cyber-fraud complaint received at the cyber crime cell.",
         facts=occ("I005") + [("victim", "P014", "I005"), ("victim", "P016", "I005"),
                              ("owns", "P014", "AC013"), ("owns", "P016", "AC015"),
                              ("txn", "t_p14"), ("txn", "t_p16"), ("supports", "E009", "I005")]),
    dict(id="R009", type="First Information Report (FIR)", case="C002", date="2026-09-28", slug="FIR_I006",
         intro="This report records a cyber-fraud complaint received at the cyber crime cell.",
         facts=occ("I006") + [("victim", "P033", "I006"), ("owns", "P033", "AC016"),
                              ("txn", "t_p33"), ("supports", "E010", "I006")]),
    dict(id="R010", type="Bank Transaction Analysis Note", case="C002", date="2026-09-29", slug="BANK_C002",
         intro="This note traces the movement of money out of the complainants' accounts.",
         facts=[("owns", "P011", "AC005"), ("owns", "P012", "AC006"), ("owns", "P013", "AC007"),
                ("owns", "P026", "AC008"), ("owns", "P027", "AC009"),
                ("txn", "t_l1"), ("txn", "t_atm1"), ("txn", "t_l2"), ("txn", "t_l3"),
                ("txn", "t_atm2"), ("txn", "t_l4"), ("txn", "t_l5"), ("txn", "t_atm3"),
                ("provided", "P031", "E007"), ("mentions", "E007", "P011"),
                ("assoc", "P032", "P012"), ("assoc", "P039", "P026")]),
    dict(id="R011", type="Call Records Analysis Note", case="C002", date="2026-09-29", slug="CDR_C002",
         intro="This note summarises call detail records obtained for handsets linked to the case.",
         facts=[("uses", "P011", "D011"), ("uses", "P012", "D012"), ("uses", "P013", "D013"),
                ("uses", "P026", "D026"), ("uses", "P027", "D027"), ("uses", "P018", "D018")] + contacts(G2)),
    dict(id="R012", type="First Information Report (FIR)", case="C003", date="2026-09-06", slug="FIR_I007",
         intro="This report records a cyber-crime complaint received at the cyber crime cell.",
         facts=occ("I007") + [("victim", "P015", "I007"), ("owns", "P015", "AC014"),
                              ("txn", "t_c0"), ("supports", "E013", "I007")]),
    dict(id="R013", type="Cyber Forensic Report", case="C003", date="2026-09-19", slug="FORENSIC_I008",
         intro="This report records the examination of a computer reported as infected.",
         facts=occ("I008") + [("victim", "P020", "I008"), ("uses", "P020", "D043"),
                              ("connected", "D043", "IP001"), ("found_on", "E012", "D043"),
                              ("derived", "E011", "D043"), ("supports", "E011", "I008"),
                              ("supports", "E012", "I008")]),
    dict(id="R014", type="First Information Report (FIR)", case="C003", date="2026-09-27", slug="FIR_I009",
         intro="This report records a cyber-crime complaint received at the cyber crime cell.",
         facts=occ("I009") + [("victim", "P021", "I009"), ("connected", "D021", "IP001"),
                              ("derived", "E014", "D021"), ("supports", "E014", "I009")]),
    dict(id="R015", type="Cyber Analysis Note", case="C003", date="2026-09-28", slug="CYBER_C003",
         intro="This note combines call records, device information and bank records for the case.",
         facts=[("uses", "P017", "D017"), ("uses", "P017", "D042"), ("uses", "P019", "D042"),
                ("uses", "P019", "D019"), ("uses", "P025", "D025"),
                ("owns", "P017", "AC010"), ("owns", "P019", "AC011"), ("owns", "P018", "AC012"),
                ("owns", "P025", "AC018")] + contacts(G3) +
               [("connected", "D042", "IP002"), ("connected", "D042", "IP001"),
                ("txn", "t_c1"), ("txn", "t_c2"), ("txn", "t_c3"), ("txn", "t_c4")]),
    dict(id="R016", type="First Information Report (FIR)", case="C004", date="2026-08-31", slug="FIR_I010",
         intro="This report records a complaint received at the jurisdictional police station.",
         facts=occ("I010") + [("victim", "P024", "I010"), ("witness", "P022", "I010"),
                              ("visited", "P029", "L009", "2026-08-30"), ("supports", "E015", "I010")]),
    dict(id="R017", type="Witness Statement", case="C004", date="2026-09-01", slug="WITNESS_I010",
         intro="This statement was recorded from a person who was near the location at the time.",
         facts=[("occurred", "I010"), ("witness", "P023", "I010"),
                ("visited", "P030", "L009", "2026-08-30")]),
    dict(id="R018", type="Call Records Analysis Note", case="C004", date="2026-09-10", slug="CDR_C004",
         intro="This note summarises call detail records obtained for handsets linked to the case.",
         facts=[("uses", "P029", "D029"), ("uses", "P030", "D030"), ("uses", "P036", "D036")] +
               contacts(G4) + [("assoc", "P030", "P029")]),
    dict(id="R019", type="Seizure Memo", case="C001", date="2026-09-27", slug="SEIZURE_C001",
         intro="This memo lists an item taken into custody during a lawful search.",
         facts=[("mentions", "E016", "P004"), ("mentions", "E016", "P005"),
                ("assoc", "P001", "P002"), ("assoc", "P002", "P003"), ("assoc", "P037", "P001")]),
]
REPORT = {r["id"]: r for r in REPORTS}


class Doc:
    def __init__(self, rid):
        self.rid = rid
        self.ents = {}
        self.seen = set()
        self.rels = []       # ground-truth relations
        self.rows = []       # relationships.csv rows

    def m(self, eid, alias_ok=True):
        t = etype(eid)
        if t == "Person":
            p = PERS[eid]
            text = p["alias"] if (alias_ok and p["alias"] and eid in self.seen and R.random() < 0.3) else p["name"]
            self.seen.add(eid)
        elif t == "Device":
            text = DEV[eid]["identifier"]
        elif t == "Location":
            text = LOC[eid]["name"]
        elif t == "Account":
            text = ACC[eid]["masked"]
        elif t == "IPAddress":
            text = IPS[eid]["address"]
        else:
            text = eid
        self.ents[(text, eid)] = t
        return text

    def rel(self, s, r, t, **kw):
        d = dict(source=s, relation=r, target=t)
        d.update({k: v for k, v in kw.items() if v is not None})
        self.rels.append(d)

    def row(self, s, r, t, **kw):
        self.rows.append(dict(source_id=s, relationship=r, target_id=t, source_doc=self.rid, **kw))

    # ---- sentence builders -------------------------------------------------
    def ch(self, *variants):
        """Pick ONE wording variant lazily so only the chosen variant registers mentions."""
        return R.choice(variants)()

    def sentence(self, f):
        k = f[0]
        m = self.m
        ch = self.ch
        if k == "occurred":
            i = f[1]; x = INC[i]; d = fdate(x["date"])
            s = ch(lambda: f"Incident {m(i)} ({x['type']}) occurred at {m(x['loc'])} on {d}.",
                   lambda: f"The {x['type'].lower()} registered as {m(i)} took place at {m(x['loc'])} on {d}.")
            self.rel(i, "OCCURRED_AT", x["loc"], date=x["date"]); self.row(i, "OCCURRED_AT", x["loc"], date=x["date"])
        elif k == "part_of":
            i = f[1]; c = INC[i]["case"]
            s = ch(lambda: f"Incident {m(i)} is registered under case {m(c)}.",
                   lambda: f"The matter {m(i)} forms part of case {m(c)}.")
            self.rel(i, "PART_OF", c); self.row(i, "PART_OF", c)
        elif k == "victim":
            p, i = f[1], f[2]
            s = ch(lambda: f"{m(p)} reported that they were the victim of incident {m(i)}.",
                   lambda: f"The complainant, {m(p)}, stated that incident {m(i)} caused them a loss.")
            self.rel(p, "VICTIM_OF", i); self.row(p, "VICTIM_OF", i)
        elif k == "witness":
            p, i = f[1], f[2]
            s = ch(lambda: f"{m(p)} told the police that they witnessed incident {m(i)}.",
                   lambda: f"{m(p)} was nearby and gave a statement about incident {m(i)}.")
            self.rel(p, "WITNESSED", i); self.row(p, "WITNESSED", i)
        elif k == "visited":
            p, l, d = f[1], f[2], f[3]
            s = ch(lambda: f"CCTV footage indicates that {m(p)} was present at {m(l)} on {fdate(d)}.",
                   lambda: f"{m(p)} visited {m(l)} on {fdate(d)}, according to the available records.",
                   lambda: f"Location records place {m(p)} at {m(l)} on {fdate(d)}.")
            self.rel(p, "VISITED", l, date=d); self.row(p, "VISITED", l, date=d)
        elif k == "uses":
            p, d = f[1], f[2]; dv = DEV[d]; w = DEVTYPE_WORD[dv["type"]]
            s = ch(lambda: f"{m(p)} was found to be using the {w} {m(d)}.",
                   lambda: f"The {w} {m(d)} is used by {m(p)}.")
            self.rel(p, "USES", d); self.row(p, "USES", d)
        elif k == "contacted":
            a, b = f[1], f[2]; st = contact_stats[(a, b)]
            s = ch(lambda: f"{m(a)} contacted {m(b)} {st['count']} times between {fdate(st['first'])} and {fdate(st['last'])}.",
                   lambda: f"Call records show {st['count']} calls between {m(a)} and {m(b)} from {fdate(st['first'])} to {fdate(st['last'])}.")
            self.rel(a, "CONTACTED", b, call_count=st["count"], first_call=st["first"], last_call=st["last"])
            self.row(a, "CONTACTED", b, call_count=st["count"], first_call=st["first"], last_call=st["last"])
        elif k == "owns":
            p, ac = f[1], f[2]
            s = ch(lambda: f"Account {m(ac)} is held by {m(p)} at {ACC[ac]['bank']}.",
                   lambda: f"{m(p)} is the holder of account {m(ac)} at {ACC[ac]['bank']}.")
            self.rel(p, "OWNS", ac); self.row(p, "OWNS", ac)
        elif k == "txn":
            t = TXN[f[1]]; amt = f"Rs. {inr(t['amount'])}"
            if t["to"]:
                ph, pt = ACC[t["frm"]]["holder"], ACC[t["to"]]["holder"]
                s = ch(lambda: f"On {fdate(t['date'])}, {amt} was transferred from account {m(t['frm'])} (held by {m(ph)}) to account {m(t['to'])} (held by {m(pt)}) through {t['channel']}.",
                       lambda: f"{'An' if t['channel'][0] in 'AEIOU' else 'A'} {t['channel']} transfer of {amt} was made on {fdate(t['date'])} from account {m(t['frm'])} of {m(ph)} to account {m(t['to'])} of {m(pt)}.")
                self.rel(t["frm"], "TRANSFERRED_TO", t["to"], date=t["date"], amount=t["amount"])
            else:
                ph = ACC[t["frm"]]["holder"]
                s = ch(lambda: f"On {fdate(t['date'])}, {amt} was withdrawn in cash from account {m(t['frm'])} (held by {m(ph)}) at an ATM in {m(t['atm'])}.",
                       lambda: f"An ATM withdrawal of {amt} was recorded on {fdate(t['date'])} from account {m(t['frm'])} of {m(ph)} in {m(t['atm'])}.")
                self.rel(t["frm"], "WITHDRAWN_AT", t["atm"], date=t["date"], amount=t["amount"])
        elif k == "supports":
            e, i = f[1], f[2]
            s = ch(lambda: f"Evidence {m(e)} ({EV[e]['desc']}) is relevant to incident {m(i)}.",
                   lambda: f"The investigating officer noted that evidence {m(e)} ({EV[e]['desc']}) supports the record of incident {m(i)}.")
            self.rel(e, "SUPPORTS", i); self.row(e, "SUPPORTS", i)
        elif k == "found_on":
            e, d = f[1], f[2]
            s = f"Evidence {m(e)} ({EV[e]['desc']}) was recovered from the {DEVTYPE_WORD[DEV[d]['type']]} {m(d)}."
            self.rel(e, "FOUND_ON", d); self.row(e, "FOUND_ON", d)
        elif k == "derived":
            e, d = f[1], f[2]
            s = f"Evidence {m(e)} ({EV[e]['desc']}) was extracted from the {DEVTYPE_WORD[DEV[d]['type']]} {m(d)}."
            self.rel(e, "DERIVED_FROM", d); self.row(e, "DERIVED_FROM", d)
        elif k == "mentions":
            e, x = f[1], f[2]
            s = f"Evidence {m(e)} ({EV[e]['desc']}) makes reference to {m(x)}."
            self.rel(e, "MENTIONS", x); self.row(e, "MENTIONS", x)
        elif k == "assoc":
            a, b = f[1], f[2]
            s = ch(lambda: f"{m(a)} is a known associate of {m(b)}.",
                   lambda: f"Earlier records list {m(a)} as an associate of {m(b)}.")
            self.rel(a, "ASSOCIATED_WITH", b); self.row(a, "ASSOCIATED_WITH", b)
        elif k == "provided":
            p, e = f[1], f[2]
            s = f"Evidence {m(e)} ({EV[e]['desc']}) was provided by {m(p)}."
            self.rel(p, "PROVIDED", e); self.row(p, "PROVIDED", e)
        elif k == "connected":
            d, ip = f[1], f[2]; dd = first_event(d, ip)
            s = ch(lambda: f"On {fdate(dd)}, the {DEVTYPE_WORD[DEV[d]['type']]} {m(d)} connected to IP address {m(ip)}, which is flagged as {IPS[ip]['label']}.",
                   lambda: f"Network logs show that {m(d)} first contacted IP address {m(ip)} on {fdate(dd)}; this address is flagged as {IPS[ip]['label']}.")
            self.rel(d, "CONNECTED_TO", ip, date=dd)
        else:
            raise ValueError(k)
        return s


rel_rows, seen_rel = [], set()
report_meta = []
for rep in REPORTS:
    doc = Doc(rep["id"])
    header = [
        "SYNTHETIC CASE REPORT - FICTIONAL DATA FOR PROTOTYPE USE ONLY",
        f"Report ID      : {rep['id']}",
        f"Report Type    : {rep['type']}",
        f"Case           : {doc.m(rep['case'])} - {CASE[rep['case']]['title']}",
        f"Date of report : {fdate(rep['date'])}",
        "Prepared by    : Investigating Officer (fictional)",
        "-" * 64,
    ]
    sents = [doc.sentence(f) for f in rep["facts"]]
    paras, i = [rep["intro"]], 0
    chunk = []
    for s in sents:
        chunk.append(s)
        if len(chunk) == 3:
            paras.append(" ".join(chunk)); chunk = []
    if chunk:
        paras.append(" ".join(chunk))
    paras.append("This document is synthetic. It contains no real persons and does not establish "
                 "responsibility for any offence; it is a working note for investigation support only.")
    text = "\n".join(header) + "\n\n" + "\n\n".join(paras) + "\n"
    fname = f"{rep['id']}_{rep['slug']}.txt"
    with open(f"{OUT}/case_reports/{fname}", "w", encoding="utf-8") as f:
        f.write(text)
    gt = dict(report_id=rep["id"], file=fname, case_id=rep["case"],
              entities=[dict(mention=k[0], id=k[1], type=v) for k, v in sorted(doc.ents.items(), key=lambda kv: kv[0][1])],
              relations=doc.rels)
    with open(f"{OUT}/ground_truth/{rep['id']}.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2, ensure_ascii=False)
    report_meta.append((rep["id"], rep["case"], rep["type"], rep["date"], f"{rep['type']} - {rep['slug']}", fname))
    for r in doc.rows:
        key = (r["source_id"], r["relationship"], r["target_id"])
        if key not in seen_rel:
            seen_rel.add(key); rel_rows.append(r)
    # sanity: every mention is really in the text; every relation endpoint has a mention
    for (mt, eid) in doc.ents:
        assert mt in text, (rep["id"], mt)
    ids = {eid for (_, eid) in doc.ents}
    for r in doc.rels:
        assert r["source"] in ids and r["target"] in ids, (rep["id"], r)

# registry rows: every device has an owner-user relationship even if no report mentions it
for did, d in DEV.items():
    key = (d["owner"], "USES", did)
    if key not in seen_rel:
        seen_rel.add(key)
        rel_rows.append(dict(source_id=d["owner"], relationship="USES", target_id=did,
                             source_doc="SUBSCRIBER-REGISTRY"))

# ----------------------------------------------------------------------------
# 6. WRITE CSVs
# ----------------------------------------------------------------------------
write_csv("persons.csv", ["person_id", "name", "role", "alias", "home_location_id"],
          [(p[0], p[1], p[2], p[3], p[4]) for p in PERSONS])
write_csv("devices.csv", ["device_id", "device_type", "identifier", "owner_person_id", "description"], DEVICES)
write_csv("locations.csv", ["location_id", "name", "latitude", "longitude", "location_type"], LOCATIONS)
write_csv("cases.csv", ["case_id", "title", "status", "opened_date"], CASES)
write_csv("incidents.csv", ["incident_id", "case_id", "type", "date", "time", "datetime", "location_id", "summary"],
          [(i[0], i[1], i[2], i[3], i[4], f"{i[3]}T{i[4]}:00{TZ}", i[5], i[6]) for i in INCIDENTS])
write_csv("accounts.csv", ["account_id", "holder_person_id", "bank", "account_no_masked"],
          [(a, v["holder"], v["bank"], v["masked"]) for a, v in ACC.items()])
write_csv("evidence.csv", ["evidence_id", "evidence_type", "case_id", "description", "collected_date", "source_report"],
          EVIDENCE)
write_csv("ip_addresses.csv", ["ip_id", "address", "label"], [(k, v["address"], v["label"]) for k, v in IPS.items()])
write_csv("reports.csv", ["report_id", "case_id", "report_type", "date", "title", "file"], report_meta)
write_csv("calls.csv", ["call_id", "caller_device_id", "callee_device_id", "timestamp", "duration_sec",
                        "caller_location_id"], call_rows)
write_csv("transactions.csv", ["txn_id", "from_account_id", "to_account_id", "amount_inr", "timestamp", "channel",
                               "atm_location_id", "source_doc"], txn_rows)
write_csv("network_events.csv", ["event_id", "device_id", "ip_id", "timestamp", "protocol", "dst_port", "bytes",
                                 "label"], net_rows)
REL_COLS = ["rel_id", "source_id", "relationship", "target_id", "date", "call_count", "first_call", "last_call",
            "source_doc"]
write_csv("relationships.csv", REL_COLS,
          [(f"REL{i:04d}", r["source_id"], r["relationship"], r["target_id"], r.get("date", ""),
            r.get("call_count", ""), r.get("first_call", ""), r.get("last_call", ""), r["source_doc"])
           for i, r in enumerate(rel_rows, 1)])

# ----------------------------------------------------------------------------
# 7. INTEGRITY CHECKS + graph.json
# ----------------------------------------------------------------------------
nodes = {}
for p in PERSONS: nodes[p[0]] = ("Person", p[1], dict(role=p[2], alias=p[3]))
for d in DEVICES: nodes[d[0]] = ("Device", d[2], dict(device_type=d[1]))
for l in LOCATIONS: nodes[l[0]] = ("Location", l[1], dict(latitude=l[2], longitude=l[3]))
for c in CASES: nodes[c[0]] = ("Case", c[1], dict(status=c[2]))
for i in INCIDENTS: nodes[i[0]] = ("Incident", f"{i[0]} {i[2]}", dict(date=i[3], time=i[4], summary=i[6]))
for a, v in ACC.items(): nodes[a] = ("Account", v["masked"], dict(bank=v["bank"]))
for e in EVIDENCE: nodes[e[0]] = ("Evidence", f"{e[0]} {e[1]}", dict(description=e[3]))
for k, v in IPS.items(): nodes[k] = ("IPAddress", v["address"], dict(threat_label=v["label"]))
for r in report_meta: nodes[r[0]] = ("CaseReport", r[4], dict(file=r[5]))

edges = []
for r in rel_rows:
    edges.append((r["source_id"], r["target_id"], r["relationship"], {k: v for k, v in r.items()
                  if k in ("date", "call_count", "source_doc") and v != ""}))
for c in call_rows: edges.append((c[1], c[2], "CALLED", dict(call_id=c[0], timestamp=c[3], duration_sec=c[4])))
for t in txn_rows:
    if t[2]:
        edges.append((t[1], t[2], "TRANSFERRED_TO", dict(txn_id=t[0], amount_inr=t[3], timestamp=t[4], channel=t[5])))
    else:
        edges.append((t[1], t[6], "WITHDRAWN_AT", dict(txn_id=t[0], amount_inr=t[3], timestamp=t[4])))
for n in net_rows: edges.append((n[1], n[2], "CONNECTED_TO", dict(event_id=n[0], timestamp=n[3], label=n[7])))
for a, v in ACC.items(): pass
for e in EVIDENCE: edges.append((e[0], e[2], "PART_OF", {}))
for r in report_meta: edges.append((r[0], r[1], "ABOUT", {}))
for i in INCIDENTS: pass

missing = [(s, t) for s, t, *_ in edges if s not in nodes or t not in nodes]
assert not missing, missing[:5]

json.dump(dict(nodes=[dict(id=k, label=v[0], name=v[1], **v[2]) for k, v in nodes.items()],
               edges=[dict(source=s, target=t, type=ty, **p) for s, t, ty, p in edges]),
          open(f"{OUT}/graph.json", "w"), indent=1)

# stats for the provenance document
from collections import Counter
stats = dict(persons=len(PERSONS), devices=len(DEVICES), locations=len(LOCATIONS), cases=len(CASES),
             incidents=len(INCIDENTS), accounts=len(ACC), evidence=len(EVIDENCE), ips=len(IPS),
             reports=len(REPORTS), calls=len(call_rows), transactions=len(txn_rows),
             network_events=len(net_rows), relationships=len(rel_rows), nodes=len(nodes), edges=len(edges),
             rel_types=dict(Counter(r["relationship"] for r in rel_rows)),
             gt_relations=sum(len(json.load(open(f"{OUT}/ground_truth/{r['id']}.json"))["relations"]) for r in REPORTS))
json.dump(stats, open("stats.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
