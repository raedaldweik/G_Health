"""
Nabd, synthetic Health Information Exchange (HIE) generator: the national diabetes registry.

Produces a relational, longitudinal, FHIR-shaped synthetic dataset for a Qatar-flavoured
diabetes population (type 2 and type 1), the way a diabetes programme sees it:

    facilities.csv.gz        18 facilities (hospitals + primary health centres)
    patients.csv.gz          4,000 people living with diabetes: demographics + consent
    conditions.csv.gz        problem list (ICD-10 + SNOMED CT codes, onset dates)
    observations.csv.gz      ~190k longitudinal labs & vitals (LOINC-coded, 36 months)
    medications.csv.gz       active/stopped medication orders (ATC-coded, adherence-aware)
    encounters.csv.gz        ~80k outpatient / ED / inpatient / telehealth visits
    care_gaps.csv.gz         open, guideline-derived diabetes care gaps
    patient_summary.csv.gz   wide per-patient feature table (latest labs, flags, cost, outcome label)
    data_dictionary.json     table/column documentation used by the agent

All data is synthetic and deterministic (seeded). Correlations are engineered to be
clinically plausible so downstream ML models learn sensible drivers: age, HbA1c, duration,
renal function, albuminuria, retinopathy/neuropathy, low adherence, missed monitoring and
prior admissions raise the risk of a diabetes deterioration event; SGLT2i/GLP-1 RA therapy,
renal protection and good adherence are protective.

Run from backend/:  python -m scripts.generate_hie_data
"""
from __future__ import annotations

import gzip
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
TODAY = date(2026, 9, 1)
OBS_START = date(2023, 9, 1)          # 36 months of history
N_PATIENTS = 4000
TARGET_EVENT_RATE = 0.105             # 12-month deterioration events (registry-level)

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "hie"
FHIR_OUT = HERE / "data" / "fhir_sample"


# ────────────────────────────── reference data ──────────────────────────────

FACILITIES = [
    # (id, name, type, region, quality_factor)  quality<1 → better control, >1 → worse
    ("F001", "Hamad General Hospital",          "Hospital",       "Doha",         1.00),
    ("F002", "Qatar Diabetes Centre",           "Hospital",       "Doha",         0.90),
    ("F003", "Al Wakra Hospital",               "Hospital",       "Al Wakrah",    1.03),
    ("F004", "Al Khor Hospital",                "Hospital",       "Al Khor",      1.05),
    ("F005", "Hazm Mebaireek General Hospital", "Hospital",       "Al Rayyan",    1.08),
    ("F006", "West Bay Health Center",          "Primary Care",   "Doha",         0.90),
    ("F007", "Al Rayyan Health Center",         "Primary Care",   "Al Rayyan",    0.97),
    ("F008", "Umm Ghuwailina Health Center",    "Primary Care",   "Doha",         1.10),
    ("F009", "Mesaimeer Health Center",         "Primary Care",   "Doha",         0.95),
    ("F010", "Al Wajba Health Center",          "Primary Care",   "Al Rayyan",    0.93),
    ("F011", "Al Thumama Health Center",        "Primary Care",   "Doha",         1.02),
    ("F012", "Rawdat Al Khail Health Center",   "Primary Care",   "Doha",         1.12),
    ("F013", "Al Daayen Health Center",         "Primary Care",   "Al Daayen",    0.98),
    ("F014", "Al Wakrah Health Center",         "Primary Care",   "Al Wakrah",    1.01),
    ("F015", "Qatar University Health Center",  "Primary Care",   "Doha",         0.92),
    ("F016", "Leabaib Health Center",           "Primary Care",   "Umm Salal",    0.96),
    ("F017", "Muaither Health Center",          "Primary Care",   "Al Rayyan",    1.06),
    ("F018", "Al Shamal Health Center",         "Primary Care",   "Al Shamal",    1.09),
]

NATIONALITIES = [
    # (name, weight, age_mean, access_factor)  access>1 → worse access/control (equity story)
    ("Qatari",      0.22, 57, 0.92),
    ("Indian",      0.20, 51, 1.06),
    ("Filipino",    0.10, 49, 1.04),
    ("Egyptian",    0.09, 54, 1.00),
    ("Bangladeshi", 0.08, 47, 1.18),
    ("Nepali",      0.07, 45, 1.20),
    ("Pakistani",   0.06, 52, 1.10),
    ("Sri Lankan",  0.04, 50, 1.08),
    ("Sudanese",    0.04, 53, 1.05),
    ("Jordanian",   0.03, 55, 0.98),
    ("British",     0.02, 58, 0.95),
    ("Other",       0.05, 52, 1.02),
]

NAME_POOLS = {
    "Qatari":      (["Mohammed", "Abdulla", "Hamad", "Khalid", "Jassim", "Fahad", "Nasser", "Saad",
                     "Fatima", "Maryam", "Noora", "Aisha", "Alanoud", "Hessa", "Sara", "Moza"],
                    ["Al-Thani", "Al-Kuwari", "Al-Mohannadi", "Al-Marri", "Al-Sulaiti", "Al-Emadi",
                     "Al-Kaabi", "Al-Naimi", "Al-Hajri", "Al-Ansari"]),
    "Indian":      (["Rajesh", "Suresh", "Anil", "Vijay", "Ramesh", "Santosh", "Manoj", "Arun",
                     "Priya", "Lakshmi", "Deepa", "Anita", "Kavitha", "Sunita"],
                    ["Nair", "Kumar", "Menon", "Pillai", "Sharma", "Patel", "Reddy", "Iyer", "Das"]),
    "Filipino":    (["Jose", "Juan", "Antonio", "Ricardo", "Eduardo", "Maria", "Rosa", "Carmen",
                     "Josefina", "Luzviminda", "Grace", "Angelica"],
                    ["Santos", "Reyes", "Cruz", "Bautista", "Garcia", "Mendoza", "Flores", "Ramos"]),
    "Egyptian":    (["Ahmed", "Mahmoud", "Mostafa", "Tarek", "Hossam", "Amr",
                     "Mona", "Heba", "Dina", "Nour", "Salma"],
                    ["Hassan", "Ibrahim", "El-Sayed", "Abdelrahman", "Farouk", "Mansour", "Shalaby"]),
    "Bangladeshi": (["Mohammad", "Abdul", "Rafiq", "Kamal", "Jahangir", "Shahid",
                     "Rahima", "Nasrin", "Shirin", "Fatema"],
                    ["Rahman", "Islam", "Hossain", "Ahmed", "Uddin", "Miah", "Chowdhury"]),
    "Nepali":      (["Ram", "Krishna", "Hari", "Bishnu", "Gopal", "Dipak",
                     "Sita", "Gita", "Kamala", "Sarita"],
                    ["Thapa", "Gurung", "Rai", "Tamang", "Shrestha", "Magar", "Limbu"]),
    "Pakistani":   (["Muhammad", "Imran", "Asif", "Tariq", "Naveed", "Shahzad",
                     "Ayesha", "Saima", "Nadia", "Farah"],
                    ["Khan", "Malik", "Hussain", "Iqbal", "Butt", "Chaudhry", "Sheikh"]),
    "Sri Lankan":  (["Nimal", "Sunil", "Chaminda", "Ruwan", "Kumari", "Sandya", "Dilani"],
                    ["Perera", "Fernando", "Silva", "Jayawardena", "Gunasekara", "Bandara"]),
    "Sudanese":    (["Omer", "Elfatih", "Mubarak", "Awad", "Amna", "Zeinab", "Ihsan"],
                    ["Osman", "Elamin", "Abdalla", "Babiker", "Elhassan", "Musa"]),
    "Jordanian":   (["Yousef", "Khaled", "Omar", "Samir", "Rania", "Lina", "Hanan"],
                    ["Haddad", "Khoury", "Nabulsi", "Majali", "Awad", "Zoubi"]),
    "British":     (["James", "David", "Michael", "Robert", "Sarah", "Emma", "Claire"],
                    ["Smith", "Jones", "Taylor", "Wilson", "Brown", "Davies"]),
    "Other":       (["Ali", "Hassan", "Ivan", "Pierre", "Chen", "Amina", "Elena", "Fatou"],
                    ["Abdi", "Petrov", "Dubois", "Wang", "Diallo", "Okafor"]),
}

INSURANCE = ["Government", "Employer-Private", "Self-Pay"]

# LOINC codes for observations
LOINC = {
    "hba1c":  ("4548-4",  "Hemoglobin A1c", "%"),
    "fpg":    ("1558-6",  "Fasting glucose", "mg/dL"),
    "sbp":    ("8480-6",  "Systolic blood pressure", "mmHg"),
    "dbp":    ("8462-4",  "Diastolic blood pressure", "mmHg"),
    "ldl":    ("13457-7", "LDL cholesterol", "mmol/L"),
    "hdl":    ("2085-9",  "HDL cholesterol", "mmol/L"),
    "tg":     ("2571-8",  "Triglycerides", "mmol/L"),
    "egfr":   ("62238-1", "eGFR", "mL/min/1.73m2"),
    "acr":    ("9318-7",  "Albumin/creatinine ratio", "mg/mmol"),
    "bmi":    ("39156-5", "Body mass index", "kg/m2"),
}

CONDITION_CODES = {
    "t2dm":         ("E11.9",   "44054006",  "Type 2 diabetes mellitus"),
    "t1dm":         ("E10.9",   "46635009",  "Type 1 diabetes mellitus"),
    "htn":          ("I10",     "38341003",  "Essential hypertension"),
    "dyslipidemia": ("E78.5",   "55822004",  "Dyslipidaemia"),
    "ckd":          ("E11.22",  "421893009", "Diabetic chronic kidney disease"),
    "obesity":      ("E66.9",   "414916001", "Obesity"),
    "retinopathy":  ("E11.319", "4855003",   "Diabetic retinopathy"),
    "neuropathy":   ("E11.40",  "230572002", "Diabetic neuropathy"),
    "foot_ulcer":   ("E11.621", "280137006", "Diabetic foot ulcer (history)"),
}

# (name, atc, class, annual_cost_qar)
MEDS = {
    "metformin":     ("Metformin",         "A10BA02", "biguanide", 420),
    "sglt2":         ("Empagliflozin",     "A10BK03", "sglt2_inhibitor", 3600),
    "glp1":          ("Semaglutide",       "A10BJ06", "glp1_agonist", 9200),
    "sulfonylurea":  ("Gliclazide",        "A10BB09", "sulfonylurea", 380),
    "dpp4":          ("Sitagliptin",       "A10BH01", "dpp4_inhibitor", 1450),
    "insulin_basal": ("Insulin glargine",  "A10AE04", "insulin_basal", 4200),
    "insulin_bolus": ("Insulin aspart",    "A10AB05", "insulin_rapid", 3900),
    "acei":          ("Perindopril",       "C09AA04", "raas_inhibitor", 460),
    "arb":           ("Valsartan",         "C09CA03", "raas_inhibitor", 520),
    "ccb":           ("Amlodipine",        "C08CA01", "ccb", 310),
    "thiazide":      ("Indapamide",        "C03BA11", "thiazide_like", 260),
}
DIABETES_CLASSES = {"biguanide", "sglt2_inhibitor", "glp1_agonist", "sulfonylurea", "dpp4_inhibitor",
                    "insulin_basal", "insulin_rapid"}

ADMISSION_REASONS = [
    ("Severe hypoglycaemia", 0.20), ("Diabetic ketoacidosis / HHS", 0.14),
    ("Uncontrolled hyperglycaemia", 0.16), ("Diabetic foot infection / ulcer", 0.16),
    ("Acute kidney injury", 0.12), ("Infection (sepsis, UTI, pneumonia)", 0.12),
    ("Elective procedure", 0.10)]


def _month_seasonality(d: date) -> float:
    """Outpatient volume seasonality: summer exodus + Ramadan dips, slight annual growth."""
    m = d.month
    f = 1.0
    if m in (7, 8):
        f *= 0.80
    if m == 3:                     # Ramadan falls around March in 2024/2025/2026
        f *= 0.86
    if m == 12:
        f *= 0.93
    years = (d.year - OBS_START.year) + (d.month - OBS_START.month) / 12
    f *= (1.0 + 0.055) ** years    # ~5.5%/yr demand growth
    return f


def rand_date(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=int(RNG.integers(0, max(span, 1))))


def build_patients() -> pd.DataFrame:
    nats = [n for n, *_ in NATIONALITIES]
    nat_w = np.array([w for _, w, *_ in NATIONALITIES]); nat_w = nat_w / nat_w.sum()
    nat_age = {n: a for n, _, a, _ in NATIONALITIES}
    nat_access = {n: f for n, _, _, f in NATIONALITIES}
    fac_ids = [f[0] for f in FACILITIES]
    fac_q = {f[0]: f[4] for f in FACILITIES}
    fac_region = {f[0]: f[3] for f in FACILITIES}

    rows = []
    for i in range(N_PATIENTS):
        pid = f"QH-{100001 + i}"
        nat = str(RNG.choice(nats, p=nat_w))
        gender = "male" if RNG.random() < (0.68 if nat in
                    ("Indian", "Bangladeshi", "Nepali", "Pakistani", "Sri Lankan") else 0.52) else "female"
        firsts, lasts = NAME_POOLS[nat]
        name = f"{RNG.choice(firsts)} {RNG.choice(lasts)}"
        diabetes_type = "type1" if RNG.random() < 0.08 else "type2"
        if diabetes_type == "type1":
            age = int(np.clip(RNG.normal(38, 11), 19, 75))
        else:
            age = int(np.clip(RNG.normal(nat_age[nat], 11), 26, 88))
        birth = TODAY - timedelta(days=age * 365 + int(RNG.integers(0, 365)))
        facility = str(RNG.choice(fac_ids, p=[0.09, 0.07, 0.06, 0.04, 0.05] + [0.69 / 13] * 13))
        years_dx = float(np.clip(RNG.gamma(3.2, 3.0) if diabetes_type == "type2"
                                 else RNG.gamma(4.0, 3.5), 0.3, min(age - 15, 45)))
        insurance = "Government" if nat == "Qatari" else str(
            RNG.choice(INSURANCE, p=[0.25, 0.60, 0.15]))
        rows.append({
            "patient_id": pid, "full_name": name, "gender": gender,
            "birth_date": birth.isoformat(), "age": age, "nationality": nat,
            "residency_status": "Citizen" if nat == "Qatari" else "Resident",
            "district": fac_region[facility], "insurance": insurance,
            "primary_facility_id": facility,
            "diabetes_type": diabetes_type,
            "years_since_diagnosis": round(years_dx, 1),
            "consent_status": "restricted" if RNG.random() < 0.025 else "general",
            "access_factor": nat_access[nat] * fac_q[facility],   # internal, dropped later
        })
    return pd.DataFrame(rows)


def simulate_clinical(pat: pd.DataFrame) -> pd.DataFrame:
    """Attach latent severity + baseline clinical state to each patient."""
    n = len(pat)
    age_z = (pat["age"] - 52) / 12
    dur_z = pat["years_since_diagnosis"] / 10
    t1 = (pat["diabetes_type"] == "type1").to_numpy()
    sev = (0.45 * age_z + 0.50 * dur_z + 0.90 * (pat["access_factor"] - 1) * 3
           + RNG.normal(0, 0.8, n))
    pat["severity"] = sev

    pat["smoker"] = ((pat["gender"] == "male") & (RNG.random(n) <
                     np.where(pat["nationality"].isin(["Bangladeshi", "Nepali", "Egyptian"]), 0.38, 0.22))).astype(int)
    pat["bmi_base"] = np.where(t1, np.clip(RNG.normal(26.5, 3.6, n), 18, 40),
                               np.clip(RNG.normal(31.0 + sev * 1.2, 4.2), 19, 52)).round(1)
    # access_factor > 1 (worse healthcare access) directly worsens control, the equity story
    pat["hba1c_base"] = np.clip(RNG.normal(7.35 + sev * 0.55 + (pat["access_factor"] - 1) * 1.6, 0.9),
                                5.6, 13.5).round(2)
    pat["sbp_base"] = np.clip(RNG.normal(132 + sev * 5.0, 12), 100, 205).round(0)
    pat["ldl_base"] = np.clip(RNG.normal(2.9 + sev * 0.25, 0.75), 1.0, 6.4).round(2)
    pat["egfr_base"] = np.clip(RNG.normal(88 - pat["age"] * 0.55 - sev * 6 - dur_z * 3, 14) + 30, 8, 125).round(0)
    # Adherence (proportion of days covered): worse with severity and poor access
    pat["adherence_pdc"] = np.clip(RNG.normal(0.80 - sev * 0.07 - (pat["access_factor"] - 1) * 0.55, 0.14),
                                   0.20, 1.0).round(2)

    p = 1 / (1 + np.exp(-(sev * 0.9 + age_z * 0.7 - 0.4)))
    pat["htn"] = (RNG.random(n) < np.clip(p + 0.25, 0, 0.95)).astype(int)
    pat["dyslipidemia"] = (RNG.random(n) < np.clip(p + 0.30, 0, 0.95)).astype(int)
    pat["retinopathy"] = (RNG.random(n) < np.clip(0.06 + dur_z * 0.16 + (sev > 1.0) * 0.06, 0, 0.65)).astype(int)
    pat["neuropathy"] = (RNG.random(n) < np.clip(0.05 + dur_z * 0.13 + (sev > 1.0) * 0.05, 0, 0.55)).astype(int)
    pat["foot_ulcer"] = ((pat["neuropathy"] == 1) & (RNG.random(n) < 0.18)).astype(int)
    pat["ckd"] = (pat["egfr_base"] < 60).astype(int)
    return pat


def build_medications(pat: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(pat)
    t1 = (pat["diabetes_type"] == "type1").to_numpy()
    t2 = ~t1
    sev = pat["severity"].to_numpy()
    adh = pat["adherence_pdc"].to_numpy()

    def add(mask, key, base_adherence=0.9):
        name, atc, cls, cost = MEDS[key]
        for idx in np.where(mask)[0]:
            start = rand_date(OBS_START - timedelta(days=900), TODAY - timedelta(days=120))
            active = RNG.random() < (base_adherence * (0.6 + 0.4 * adh[idx]))
            rows.append({
                "patient_id": pat.at[idx, "patient_id"], "medication": name, "atc_code": atc,
                "drug_class": cls, "start_date": start.isoformat(),
                "status": "active" if active else "stopped",
                "annual_cost_qar": cost if active else 0,
            })

    add(t2 & (RNG.random(n) < 0.90), "metformin")
    # Deliberate SGLT2/GLP-1 under-use in the sickest segment → the intensification gap story
    add(t2 & (RNG.random(n) < np.clip(0.34 - (sev > 1.2) * 0.12, 0.05, 1)), "sglt2")
    add(t2 & (RNG.random(n) < np.clip(0.20 - (sev > 1.2) * 0.08, 0.03, 1)), "glp1")
    add(t2 & (RNG.random(n) < 0.30), "sulfonylurea")
    add(t2 & (RNG.random(n) < 0.22), "dpp4")
    add((t1 | (t2 & (sev > 1.0))) & (RNG.random(n) < 0.85), "insulin_basal")
    add((t1 & (RNG.random(n) < 0.95)) | (t2 & (sev > 1.6) & (RNG.random(n) < 0.40)), "insulin_bolus")

    htn = pat["htn"].to_numpy() == 1
    ckd = pat["ckd"].to_numpy() == 1
    # RAAS inhibition: standard in hypertension, under-used for renal protection → renal gap
    add(htn & (RNG.random(n) < 0.55), "acei")
    add(htn & (RNG.random(n) < 0.30), "arb")
    add(ckd & ~htn & (RNG.random(n) < 0.35), "acei")
    add(htn & (RNG.random(n) < 0.40), "ccb")
    add(htn & (RNG.random(n) < 0.25), "thiazide")
    return pd.DataFrame(rows)


def build_conditions(pat: pd.DataFrame) -> pd.DataFrame:
    rows = []
    flag_cols = ["htn", "dyslipidemia", "ckd", "retinopathy", "neuropathy", "foot_ulcer"]
    for idx, p in pat.iterrows():
        conds = ["t2dm" if p["diabetes_type"] == "type2" else "t1dm"]
        conds += [c for c in flag_cols if p[c] == 1]
        if p["bmi_base"] >= 30:
            conds.append("obesity")
        for c in conds:
            icd, snomed, label = CONDITION_CODES[c]
            onset_years = p["years_since_diagnosis"] if c in ("t1dm", "t2dm") else float(RNG.gamma(2.5, 2.2))
            onset = TODAY - timedelta(days=int(onset_years * 365) + int(RNG.integers(0, 200)))
            rows.append({"patient_id": p["patient_id"], "condition": label, "condition_key": c,
                         "icd10_code": icd, "snomed_code": snomed,
                         "onset_date": max(onset, date(1990, 1, 1)).isoformat(),
                         "clinical_status": "active"})
    return pd.DataFrame(rows)


def build_observations(pat: pd.DataFrame, meds: pd.DataFrame) -> pd.DataFrame:
    """36 months of longitudinal labs/vitals with treatment-responsive trends."""
    on_class = meds[meds["status"] == "active"].groupby("patient_id")["drug_class"].agg(set).to_dict()
    rows = []
    months = 36
    for _, p in pat.iterrows():
        pid = p["patient_id"]
        classes = on_class.get(pid, set())
        on_new_dm = bool({"sglt2_inhibitor", "glp1_agonist"} & classes)
        low_adh = p["adherence_pdc"] < 0.6

        # Per-patient annual drift: newer agents improve control; untreated severe / non-adherent worsens
        hba1c_drift = (-0.35 if on_new_dm else (0.12 if p["severity"] > 1.0 else -0.05)) + (0.18 if low_adh else 0)
        egfr_drift = -1.2 - max(p["severity"], 0) * 1.1 - (0.8 if low_adh else 0)

        def jitter(base, sd):
            return float(RNG.normal(base, sd))

        # HbA1c ~ every 3-5 months (some patients stop testing → monitoring gap)
        t = 0.0
        stop_testing = RNG.random() < (0.16 + 0.10 * (p["access_factor"] > 1.1))
        last_frac = RNG.uniform(0.55, 0.82) if stop_testing else 1.0
        while t < months * last_frac:
            d = OBS_START + timedelta(days=int(t * 30.4))
            yrs = t / 12
            v = np.clip(jitter(p["hba1c_base"] + hba1c_drift * yrs, 0.32), 5.0, 14.5)
            rows.append((pid, "hba1c", d.isoformat(), round(v, 1)))
            t += float(RNG.uniform(3.0, 5.0))
        fpg = np.clip((p["hba1c_base"] * 28.7 - 46.7) + RNG.normal(0, 12), 70, 400)
        rows.append((pid, "fpg", rand_date(TODAY - timedelta(days=200), TODAY).isoformat(), round(fpg, 0)))

        # BP at each routine visit ~ 3-5/yr
        t = float(RNG.uniform(0, 2.5))
        while t < months:
            d = OBS_START + timedelta(days=int(t * 30.4))
            sbp = np.clip(jitter(p["sbp_base"], 8), 95, 215)
            rows.append((pid, "sbp", d.isoformat(), round(sbp, 0)))
            rows.append((pid, "dbp", d.isoformat(), round(np.clip(sbp * 0.62 + RNG.normal(0, 5), 55, 130), 0)))
            t += float(RNG.uniform(2.4, 4.5))

        # Lipids ~ annual
        for k in range(3):
            d = OBS_START + timedelta(days=int((k * 12 + RNG.uniform(0, 3)) * 30.4))
            if d > TODAY:
                break
            rows.append((pid, "ldl", d.isoformat(), round(np.clip(jitter(p["ldl_base"], 0.25), 0.7, 7.0), 2)))
            rows.append((pid, "hdl", d.isoformat(), round(np.clip(RNG.normal(1.1, 0.22), 0.5, 2.4), 2)))
            rows.append((pid, "tg", d.isoformat(), round(np.clip(RNG.normal(1.9 + p["severity"] * 0.2, 0.6), 0.5, 8), 2)))

        # Renal ~ annual; ACR only for ~70% (screening gap), less in poor-access groups
        for k in range(3):
            d = OBS_START + timedelta(days=int((k * 12 + RNG.uniform(1, 4)) * 30.4))
            if d > TODAY:
                break
            rows.append((pid, "egfr", d.isoformat(),
                         round(np.clip(p["egfr_base"] + egfr_drift * k + RNG.normal(0, 4), 5, 130), 0)))
            if RNG.random() < (0.72 - 0.15 * (p["access_factor"] > 1.1)):
                rows.append((pid, "acr", d.isoformat(),
                             round(float(np.clip(RNG.lognormal(1.0 + max(p["severity"], 0) * 0.5, 0.9), 0.3, 300)), 1)))

        # BMI ~ annual; weight rises with poor control, falls on GLP-1/SGLT2
        for k in range(3):
            d = OBS_START + timedelta(days=int((k * 12 + RNG.uniform(2, 6)) * 30.4))
            if d > TODAY:
                break
            trend = (-0.6 * k if on_new_dm else (0.35 * k if p["severity"] > 1.0 else 0))
            rows.append((pid, "bmi", d.isoformat(),
                         round(np.clip(p["bmi_base"] + RNG.normal(0, 0.7) + trend, 17, 55), 1)))

    df = pd.DataFrame(rows, columns=["patient_id", "obs_key", "effective_date", "value"])
    df["loinc_code"] = df["obs_key"].map(lambda k: LOINC[k][0])
    df["display"] = df["obs_key"].map(lambda k: LOINC[k][1])
    df["unit"] = df["obs_key"].map(lambda k: LOINC[k][2])
    return df.sort_values(["patient_id", "effective_date"]).reset_index(drop=True)


def build_encounters(pat: pd.DataFrame, meds: pd.DataFrame) -> pd.DataFrame:
    reasons = [r for r, _ in ADMISSION_REASONS]
    reason_w = np.array([w for _, w in ADMISSION_REASONS]); reason_w = reason_w / reason_w.sum()
    on_insulin = set(meds[(meds["status"] == "active") & meds["drug_class"].str.startswith("insulin")]["patient_id"])
    rows = []
    eid = 0
    for _, p in pat.iterrows():
        sev = max(p["severity"], -1)
        # Outpatient: 3-9/yr scaled by severity, with monthly seasonality
        base_rate = 3.2 + np.clip(sev + 1, 0, 3) * 1.8
        month = OBS_START
        while month < TODAY:
            lam = base_rate / 12 * _month_seasonality(month)
            for _ in range(int(RNG.poisson(lam))):
                eid += 1
                d = month + timedelta(days=int(RNG.integers(0, 28)))
                tele = RNG.random() < 0.18
                rows.append({"encounter_id": f"E{eid:07d}", "patient_id": p["patient_id"],
                             "facility_id": p["primary_facility_id"],
                             "encounter_type": "telehealth" if tele else "outpatient",
                             "start_date": d.isoformat(), "length_of_stay_days": 0,
                             "reason": "Diabetes follow-up"})
            month = (month.replace(day=1) + timedelta(days=32)).replace(day=1)

        # ED visits & admissions driven by risk, insulin use, renal function and adherence
        risk_lift = 1 / (1 + np.exp(-sev))
        low_adh = p["adherence_pdc"] < 0.6
        n_ed = int(RNG.poisson(0.55 * risk_lift * 3 + low_adh * 0.5 + (p["patient_id"] in on_insulin) * 0.25))
        for _ in range(n_ed):
            eid += 1
            rows.append({"encounter_id": f"E{eid:07d}", "patient_id": p["patient_id"],
                         "facility_id": "F001" if RNG.random() < 0.6 else p["primary_facility_id"],
                         "encounter_type": "emergency",
                         "start_date": rand_date(OBS_START, TODAY).isoformat(),
                         "length_of_stay_days": 0, "reason": "Emergency presentation"})
        n_adm = int(RNG.poisson(0.30 * risk_lift * 3 + p["foot_ulcer"] * 0.35 + (p["egfr_base"] < 45) * 0.25
                                + (p["patient_id"] in on_insulin) * 0.15 + low_adh * 0.2))
        for _ in range(n_adm):
            eid += 1
            rows.append({"encounter_id": f"E{eid:07d}", "patient_id": p["patient_id"],
                         "facility_id": str(RNG.choice(["F001", "F002", "F003", "F005"])),
                         "encounter_type": "inpatient",
                         "start_date": rand_date(OBS_START, TODAY).isoformat(),
                         "length_of_stay_days": int(np.clip(RNG.gamma(2.2, 2.4), 1, 30)),
                         "reason": str(RNG.choice(reasons, p=reason_w))})
    return pd.DataFrame(rows).sort_values("start_date").reset_index(drop=True)


def build_summary(pat, meds, obs, enc) -> pd.DataFrame:
    """Wide per-patient table: latest labs, therapy flags, utilisation, gaps, outcome label."""
    active = meds[meds["status"] == "active"]
    classes = active.groupby("patient_id")["drug_class"].agg(set).to_dict()
    med_cost = active.groupby("patient_id")["annual_cost_qar"].sum().to_dict()
    dm_med_count = active[active["drug_class"].isin(DIABETES_CLASSES)].groupby("patient_id").size().to_dict()
    med_count = active.groupby("patient_id").size().to_dict()

    obs_s = obs.sort_values("effective_date")
    latest = obs_s.groupby(["patient_id", "obs_key"]).tail(1).pivot(index="patient_id", columns="obs_key", values="value")
    last_date = obs_s.groupby(["patient_id", "obs_key"])["effective_date"].last().unstack()
    cutoff = (TODAY - timedelta(days=365)).isoformat()
    ago = obs_s[obs_s["effective_date"] <= cutoff].groupby(["patient_id", "obs_key"]).tail(1) \
        .pivot(index="patient_id", columns="obs_key", values="value")

    enc12 = enc[enc["start_date"] >= cutoff]
    adm12 = enc12[enc12["encounter_type"] == "inpatient"].groupby("patient_id").size().to_dict()
    ed12 = enc12[enc12["encounter_type"] == "emergency"].groupby("patient_id").size().to_dict()
    out12 = enc12[enc12["encounter_type"].isin(["outpatient", "telehealth"])].groupby("patient_id").size().to_dict()
    last_visit = enc.groupby("patient_id")["start_date"].max().to_dict()

    rows, drivers_all = [], []
    for _, p in pat.iterrows():
        pid = p["patient_id"]
        cls = classes.get(pid, set())
        lv = latest.loc[pid] if pid in latest.index else pd.Series(dtype=float)
        ld = last_date.loc[pid] if pid in last_date.index else pd.Series(dtype=object)
        lag = ago.loc[pid] if pid in ago.index else pd.Series(dtype=float)

        hba1c = float(lv.get("hba1c", np.nan)); hba1c_ago = float(lag.get("hba1c", np.nan))
        sbp = float(lv.get("sbp", np.nan)); dbp = float(lv.get("dbp", np.nan))
        ldl = float(lv.get("ldl", np.nan)); egfr = float(lv.get("egfr", np.nan))
        bmi = float(lv.get("bmi", p["bmi_base"])); bmi_ago = float(lag.get("bmi", np.nan))
        acr = float(lv.get("acr", np.nan))

        on_new_dm = bool({"sglt2_inhibitor", "glp1_agonist"} & cls)
        on_raas = "raas_inhibitor" in cls
        on_insulin = bool({"insulin_basal", "insulin_rapid"} & cls)
        on_metformin = "biguanide" in cls
        adherence = float(p["adherence_pdc"])

        days = lambda iso: (TODAY - date.fromisoformat(iso)).days if isinstance(iso, str) else 99999
        hba1c_days = days(ld.get("hba1c"))
        control = (("well_controlled" if hba1c < 7 else "moderate" if hba1c < 8
                    else "uncontrolled" if hba1c < 9 else "poorly_controlled") if not np.isnan(hba1c) else "n/a")
        ckd_stage = ("G1" if egfr >= 90 else "G2" if egfr >= 60 else "G3a" if egfr >= 45
                     else "G3b" if egfr >= 30 else "G4" if egfr >= 15 else "G5") if not np.isnan(egfr) else "n/a"
        ckd = int(not np.isnan(egfr) and egfr < 60)
        albuminuria = int(not np.isnan(acr) and acr >= 3)
        retinal_overdue = int(RNG.random() < (0.26 + 0.12 * (p["access_factor"] > 1.1)))
        foot_overdue = int(RNG.random() < (0.20 + 0.10 * p["neuropathy"]))
        dm_meds = int(dm_med_count.get(pid, 0))

        gaps = []
        if hba1c_days > 183: gaps.append("hba1c_overdue")
        if retinal_overdue: gaps.append("retinal_screening_overdue")
        if foot_overdue: gaps.append("foot_exam_overdue")
        if np.isnan(acr): gaps.append("acr_screening_missing")
        if p["htn"] == 1 and not np.isnan(sbp) and (sbp >= 140 or dbp >= 90): gaps.append("bp_uncontrolled")
        if (p["diabetes_type"] == "type2" and not on_new_dm and not np.isnan(hba1c) and hba1c >= 8
                and (bmi >= 30 or ckd or albuminuria)):
            gaps.append("glp1_sglt2_gap")
        if not np.isnan(hba1c) and hba1c >= 9 and dm_meds <= 1 and not on_insulin:
            gaps.append("therapy_inertia")
        if adherence < 0.6: gaps.append("low_adherence")
        if (ckd or albuminuria) and not on_raas: gaps.append("renal_protection_gap")

        prior_adm = int(adm12.get(pid, 0)); ed_n = int(ed12.get(pid, 0))
        # ── Outcome: diabetes deterioration event in the next 12 months (admission for
        # hypo/hyperglycaemia, DKA/HHS, foot infection, AKI, or progression to HbA1c ≥ 10).
        # Ground-truth logistic model, the ML task is to recover these drivers.
        drivers = (0.25 * max(p["age"] - 50, 0) / 10
                   + (0.32 * max(hba1c - 7, 0) if not np.isnan(hba1c) else 0.3)
                   + (0.10 * max(sbp - 130, 0) / 10 if not np.isnan(sbp) else 0)
                   + (0.55 * max(60 - egfr, 0) / 15 if not np.isnan(egfr) else 0)
                   + 0.25 * albuminuria + 0.45 * p["retinopathy"] + 0.40 * p["neuropathy"]
                   + 0.35 * p["foot_ulcer"] + 0.30 * p["smoker"]
                   + 0.40 * min(prior_adm, 3) + 0.20 * min(ed_n, 3)
                   + 0.12 * max(bmi - 30, 0) / 5
                   + 0.35 * (hba1c_days > 183)
                   + 0.55 * max(0.75 - adherence, 0) / 0.25
                   + 0.25 * on_insulin + 0.15 * p["years_since_diagnosis"] / 10
                   - 0.45 * on_new_dm - 0.25 * (on_raas and (ckd or albuminuria)))
        drivers_all.append(drivers)

        cost = (2600 + out12.get(pid, 0) * 450 + ed_n * 1900 + prior_adm * 18000 + med_cost.get(pid, 0)
                + (p["retinopathy"] + p["neuropathy"]) * 1500 + p["foot_ulcer"] * 3500
                + (ckd_stage in ("G3b", "G4", "G5")) * 4000)
        cost *= float(RNG.lognormal(0, 0.18))

        # Legacy rules-based registry tier (what the ML model replaces): crude point buckets
        # on age, HbA1c, admissions and BP, blind to complications, renal function,
        # adherence, monitoring gaps and therapy. The kind of tiering registries run today.
        legacy = (20 * (p["age"] >= 60)
                  + 25 * (not np.isnan(hba1c) and hba1c >= 9)
                  + 10 * (not np.isnan(hba1c) and 8 <= hba1c < 9)
                  + 25 * (prior_adm > 0)
                  + 10 * (not np.isnan(sbp) and sbp >= 160))
        tier = "Very High" if legacy >= 60 else "High" if legacy >= 40 else "Moderate" if legacy >= 20 else "Low"
        rows.append({
            "patient_id": pid, "full_name": p["full_name"], "gender": p["gender"], "age": p["age"],
            "nationality": p["nationality"], "residency_status": p["residency_status"],
            "district": p["district"], "insurance": p["insurance"],
            "primary_facility_id": p["primary_facility_id"],
            "diabetes_type": p["diabetes_type"], "years_since_diagnosis": p["years_since_diagnosis"],
            "consent_status": p["consent_status"], "smoker": p["smoker"],
            "bmi": round(bmi, 1),
            "bmi_change_12m": None if np.isnan(bmi_ago) else round(bmi - bmi_ago, 1),
            "hba1c_latest": None if np.isnan(hba1c) else round(hba1c, 1),
            "hba1c_12m_ago": None if np.isnan(hba1c_ago) else round(hba1c_ago, 1),
            "hba1c_days_since_test": None if hba1c_days > 9000 else hba1c_days,
            "glycaemic_control": control,
            "sbp_latest": None if np.isnan(sbp) else sbp, "dbp_latest": None if np.isnan(dbp) else dbp,
            "bp_controlled": None if np.isnan(sbp) else int(sbp < 140 and dbp < 90),
            "ldl_latest": None if np.isnan(ldl) else ldl,
            "egfr_latest": None if np.isnan(egfr) else egfr, "ckd_stage": ckd_stage, "ckd": ckd,
            "acr_latest": None if np.isnan(acr) else acr, "albuminuria": albuminuria,
            "htn": p["htn"], "dyslipidemia": p["dyslipidemia"],
            "retinopathy": p["retinopathy"], "neuropathy": p["neuropathy"], "foot_ulcer_history": p["foot_ulcer"],
            "on_metformin": int(on_metformin), "on_sglt2_glp1": int(on_new_dm),
            "on_insulin": int(on_insulin), "on_raas_inhibitor": int(on_raas),
            "adherence_pdc": adherence,
            "diabetes_medication_count": dm_meds, "medication_count": int(med_count.get(pid, 0)),
            "retinal_screening_overdue": retinal_overdue, "foot_exam_overdue": foot_overdue,
            "open_care_gaps": ";".join(gaps), "care_gap_count": len(gaps),
            "outpatient_visits_12mo": int(out12.get(pid, 0)),
            "ed_visits_12mo": ed_n, "admissions_12mo": prior_adm,
            "last_visit_date": last_visit.get(pid),
            "annual_cost_qar": round(cost, 0),
            "legacy_risk_score": round(legacy, 1), "registry_risk_tier": tier,
        })

    df = pd.DataFrame(rows)
    # Calibrate the intercept so the registry-level 12-month event rate hits the target,
    # then draw the labels, deterministic given the seed.
    d = np.array(drivers_all)
    lo, hi = -10.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        rate = (1 / (1 + np.exp(-(mid + 1.75 * d)))).mean()
        lo, hi = (mid, hi) if rate < TARGET_EVENT_RATE else (lo, mid)
    p_event = 1 / (1 + np.exp(-(lo + 1.75 * d)))
    df["event_probability_true"] = np.round(p_event, 4)      # hidden ground truth (kept for eval)
    df["deterioration_next_12m"] = (RNG.random(len(df)) < p_event).astype(int)
    return df


GAP_LABELS = {
    "hba1c_overdue": "HbA1c test overdue (>6 months)",
    "retinal_screening_overdue": "Retinal screening overdue (>12 months)",
    "foot_exam_overdue": "Diabetic foot exam overdue (>12 months)",
    "acr_screening_missing": "Urine ACR screening missing (12 months)",
    "bp_uncontrolled": "Blood pressure uncontrolled (≥140/90)",
    "glp1_sglt2_gap": "T2DM ≥8% with obesity/CKD not on SGLT2i or GLP-1 RA",
    "therapy_inertia": "HbA1c ≥9% with no treatment intensification",
    "low_adherence": "Medication adherence below 60% (PDC)",
    "renal_protection_gap": "CKD or albuminuria without RAAS inhibitor",
}


def build_care_gaps(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in summary.iterrows():
        if not r["open_care_gaps"]:
            continue
        for g in r["open_care_gaps"].split(";"):
            rows.append({"patient_id": r["patient_id"], "gap_key": g, "gap_label": GAP_LABELS[g],
                         "facility_id": r["primary_facility_id"],
                         "opened_date": rand_date(TODAY - timedelta(days=400), TODAY - timedelta(days=30)).isoformat(),
                         "status": "open"})
    return pd.DataFrame(rows)


# ────────────────────────────── FHIR R4 sample export ──────────────────────────────

def export_fhir_sample(pat, cond, obs, meds, enc, n_patients=25):
    FHIR_OUT.mkdir(parents=True, exist_ok=True)
    ids = list(pat["patient_id"].head(n_patients))
    idset = set(ids)

    def nd(name, resources):
        with open(FHIR_OUT / f"{name}.ndjson", "w") as f:
            for r in resources:
                f.write(json.dumps(r) + "\n")

    prows = pat[pat["patient_id"].isin(idset)]
    nd("Patient", [{
        "resourceType": "Patient", "id": p.patient_id,
        "identifier": [{"system": "https://qhie.gov.qa/mrn", "value": p.patient_id}],
        "name": [{"text": p.full_name}], "gender": p.gender, "birthDate": p.birth_date,
        "extension": [{"url": "https://nabd.health/fhir/nationality", "valueString": p.nationality}],
    } for p in prows.itertuples()])

    nd("Condition", [{
        "resourceType": "Condition", "id": f"{r.patient_id}-{r.condition_key}",
        "subject": {"reference": f"Patient/{r.patient_id}"},
        "code": {"coding": [
            {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": r.icd10_code, "display": r.condition},
            {"system": "http://snomed.info/sct", "code": r.snomed_code, "display": r.condition}]},
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                       "code": "active"}]},
        "onsetDateTime": r.onset_date,
    } for r in cond[cond["patient_id"].isin(idset)].itertuples()])

    o = obs[obs["patient_id"].isin(idset)].groupby(["patient_id", "obs_key"]).tail(3)
    nd("Observation", [{
        "resourceType": "Observation", "id": f"{r.patient_id}-{r.obs_key}-{i}",
        "status": "final", "subject": {"reference": f"Patient/{r.patient_id}"},
        "code": {"coding": [{"system": "http://loinc.org", "code": r.loinc_code, "display": r.display}]},
        "effectiveDateTime": r.effective_date,
        "valueQuantity": {"value": r.value, "unit": r.unit},
    } for i, r in enumerate(o.itertuples())])

    nd("MedicationRequest", [{
        "resourceType": "MedicationRequest", "id": f"{r.patient_id}-med-{i}",
        "status": r.status if r.status == "active" else "stopped", "intent": "order",
        "subject": {"reference": f"Patient/{r.patient_id}"},
        "medicationCodeableConcept": {"coding": [
            {"system": "http://www.whocc.no/atc", "code": r.atc_code, "display": r.medication}]},
        "authoredOn": r.start_date,
    } for i, r in enumerate(meds[meds["patient_id"].isin(idset)].itertuples())])

    e = enc[enc["patient_id"].isin(idset)].groupby("patient_id").tail(5)
    nd("Encounter", [{
        "resourceType": "Encounter", "id": r.encounter_id, "status": "finished",
        "class": {"code": {"outpatient": "AMB", "telehealth": "VR",
                           "emergency": "EMER", "inpatient": "IMP"}[r.encounter_type]},
        "subject": {"reference": f"Patient/{r.patient_id}"},
        "period": {"start": r.start_date},
        "serviceProvider": {"reference": f"Organization/{r.facility_id}"},
        "reasonCode": [{"text": r.reason}],
    } for r in e.itertuples()])


DATA_DICTIONARY = {
    "facilities": "One row per healthcare facility: facility_id, name, type (Hospital/Primary Care), region, quality factor.",
    "patients": "National diabetes registry of 4,000 people living with diabetes: demographics, nationality, district, insurance, primary facility, diabetes type (type1/type2), years since diagnosis, consent status.",
    "conditions": "Active problem list per patient with ICD-10-CM and SNOMED CT codes and onset dates: type 1/2 diabetes, hypertension, dyslipidaemia, diabetic kidney disease, obesity, retinopathy, neuropathy, foot ulcer history.",
    "observations": "Longitudinal LOINC-coded labs and vitals over 36 months: HbA1c, fasting glucose, SBP/DBP, LDL/HDL/TG, eGFR, urine ACR, BMI. Columns: patient_id, obs_key, loinc_code, effective_date, value, unit.",
    "medications": "ATC-coded medication orders with drug class, start date, status (active/stopped) and annual cost: metformin, SGLT2i, GLP-1 RA, sulfonylurea, DPP-4i, basal and rapid insulin, RAAS inhibitors, calcium-channel blockers, thiazide-like diuretics. Stopped orders reflect adherence.",
    "encounters": "All visits over 36 months: outpatient diabetes follow-up, telehealth, emergency, inpatient (with length of stay and admission reason: hypoglycaemia, DKA/HHS, hyperglycaemia, foot infection, AKI, infection, elective).",
    "care_gaps": "Open guideline-derived diabetes care gaps per patient: HbA1c overdue, retinal / foot / ACR screening, BP uncontrolled, SGLT2i/GLP-1 intensification gap, therapy inertia at HbA1c ≥9%, low adherence, renal protection gap.",
    "patient_summary": "Wide per-patient analytical table: latest labs (hba1c_latest, hba1c_12m_ago, sbp_latest, egfr_latest, acr_latest, bmi, bmi_change_12m), complications (retinopathy, neuropathy, foot_ulcer_history, ckd, albuminuria), therapy flags (on_metformin, on_sglt2_glp1, on_insulin, on_raas_inhibitor), adherence_pdc, care gaps, 12-month utilisation, annual cost (QAR), the registry's rule-based legacy_risk_score / registry_risk_tier, and the deterioration_next_12m outcome label used to train the risk model.",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Generating patients…")
    pat = build_patients()
    pat = simulate_clinical(pat)
    print("Generating medications…")
    meds = build_medications(pat)
    print("Generating conditions…")
    cond = build_conditions(pat)
    print("Generating 36 months of observations…")
    obs = build_observations(pat, meds)
    print("Generating encounters…")
    enc = build_encounters(pat, meds)
    print("Deriving patient summary + outcome labels…")
    summary = build_summary(pat, meds, obs, enc)
    gaps = build_care_gaps(summary)

    fac = pd.DataFrame(FACILITIES, columns=["facility_id", "facility_name", "facility_type",
                                            "region", "quality_factor"])
    patients_out = pat.drop(columns=["access_factor", "severity", "bmi_base", "hba1c_base",
                                     "sbp_base", "ldl_base", "egfr_base", "adherence_pdc",
                                     "htn", "dyslipidemia", "retinopathy", "neuropathy",
                                     "foot_ulcer", "ckd", "smoker"])

    for name, df in [("facilities", fac), ("patients", patients_out), ("conditions", cond),
                     ("observations", obs), ("medications", meds), ("encounters", enc),
                     ("care_gaps", gaps), ("patient_summary", summary)]:
        path = OUT / f"{name}.csv.gz"
        df.to_csv(path, index=False, compression="gzip")
        print(f"  wrote {path.name}: {len(df):,} rows")

    with open(OUT / "data_dictionary.json", "w") as f:
        json.dump(DATA_DICTIONARY, f, indent=2)

    print("Exporting FHIR R4 sample bundle…")
    export_fhir_sample(pat, cond, obs, meds, enc)

    s = summary
    gc = lambda k: int(s["open_care_gaps"].str.contains(k, na=False).sum())
    print("\n── Registry sanity check ──")
    print(f"patients: {len(s):,} (type 1: {(s['diabetes_type']=='type1').mean()*100:.1f}%) | mean HbA1c: {s['hba1c_latest'].mean():.2f}"
          f" | well-controlled: {(s['glycaemic_control']=='well_controlled').mean()*100:.1f}%"
          f" | HbA1c ≥9: {(s['hba1c_latest']>=9).mean()*100:.1f}%")
    print(f"retinopathy: {s['retinopathy'].mean()*100:.1f}% | neuropathy: {s['neuropathy'].mean()*100:.1f}% | CKD: {s['ckd'].mean()*100:.1f}%"
          f" | on SGLT2/GLP-1: {s['on_sglt2_glp1'].mean()*100:.1f}% | on insulin: {s['on_insulin'].mean()*100:.1f}%")
    print(f"gaps, HbA1c overdue: {gc('hba1c_overdue')} | retinal: {gc('retinal_screening_overdue')} | foot: {gc('foot_exam_overdue')}"
          f" | ACR: {gc('acr_screening_missing')} | BP: {gc('bp_uncontrolled')} | intensification: {gc('glp1_sglt2_gap')}"
          f" | inertia: {gc('therapy_inertia')} | adherence: {gc('low_adherence')} | renal: {gc('renal_protection_gap')}")
    print(f"deterioration rate (12m label): {s['deterioration_next_12m'].mean()*100:.1f}% | "
          f"total annual cost: QAR {s['annual_cost_qar'].sum()/1e6:.1f}M | tiers: {s['registry_risk_tier'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
