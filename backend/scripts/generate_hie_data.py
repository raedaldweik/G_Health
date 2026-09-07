"""
Nabd — synthetic Health Information Exchange (HIE) generator.

Produces a relational, longitudinal, FHIR-shaped synthetic dataset for a
Qatar-flavoured cardiometabolic (diabetes-led) population:

    facilities.csv.gz        18 facilities (hospitals + primary health centres)
    patients.csv.gz          4,000 patients with demographics + consent
    conditions.csv.gz        problem list (ICD-10 + SNOMED CT codes, onset dates)
    observations.csv.gz      ~200k longitudinal labs & vitals (LOINC-coded, 36 months)
    medications.csv.gz       active/stopped medication orders (ATC-coded)
    encounters.csv.gz        ~50k outpatient / ED / inpatient / telehealth visits
    care_gaps.csv.gz         open, guideline-derived care gaps
    patient_summary.csv.gz   wide per-patient feature table (latest labs, flags, cost, outcome label)
    data_dictionary.json     table/column documentation used by the agent

All data is synthetic and deterministic (seeded). Correlations are engineered to be
clinically plausible so downstream ML models learn sensible drivers:
age/HbA1c/SBP/LDL/eGFR/established CVD/smoking/prior admissions raise the risk of a
cardiometabolic event; statins, SGLT2/GLP-1 and anticoagulation are protective.

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

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "hie"
FHIR_OUT = HERE / "data" / "fhir_sample"


# ────────────────────────────── reference data ──────────────────────────────

FACILITIES = [
    # (id, name, type, region, quality_factor)  quality<1 → better control, >1 → worse
    ("F001", "Hamad General Hospital",          "Hospital",       "Doha",         1.00),
    ("F002", "Heart Hospital",                  "Hospital",       "Doha",         0.94),
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
    "ef":     ("10230-1", "Left ventricular ejection fraction", "%"),
}

CONDITION_CODES = {
    "t2dm":         ("E11.9",  "44054006",  "Type 2 diabetes mellitus"),
    "t1dm":         ("E10.9",  "46635009",  "Type 1 diabetes mellitus"),
    "htn":          ("I10",    "38341003",  "Essential hypertension"),
    "dyslipidemia": ("E78.5",  "55822004",  "Dyslipidaemia"),
    "cad":          ("I25.10", "53741008",  "Coronary artery disease"),
    "hf":           ("I50.9",  "84114007",  "Heart failure"),
    "stroke":       ("I63.9",  "230690007", "Prior stroke / TIA"),
    "pad":          ("I73.9",  "400047006", "Peripheral arterial disease"),
    "af":           ("I48.91", "49436004",  "Atrial fibrillation"),
    "ckd":          ("N18.30", "709044004", "Chronic kidney disease"),
    "obesity":      ("E66.9",  "414916001", "Obesity"),
    "retinopathy":  ("E11.319","4855003",   "Diabetic retinopathy"),
    "neuropathy":   ("E11.40", "230572002", "Diabetic neuropathy"),
}

# (name, atc, class, annual_cost_qar)
MEDS = {
    "metformin":     ("Metformin",     "A10BA02", "biguanide", 420),
    "sglt2":         ("Empagliflozin", "A10BK03", "sglt2_inhibitor", 3600),
    "glp1":          ("Semaglutide",   "A10BJ06", "glp1_agonist", 9200),
    "sulfonylurea":  ("Gliclazide",    "A10BB09", "sulfonylurea", 380),
    "dpp4":          ("Sitagliptin",   "A10BH01", "dpp4_inhibitor", 1450),
    "insulin_basal": ("Insulin glargine", "A10AE04", "insulin", 4200),
    "statin_high":   ("Atorvastatin 40mg", "C10AA05", "statin_high_intensity", 520),
    "statin_mod":    ("Rosuvastatin 10mg", "C10AA07", "statin_moderate_intensity", 610),
    "acei":          ("Perindopril",   "C09AA04", "raas_inhibitor", 460),
    "arb":           ("Valsartan",     "C09CA03", "raas_inhibitor", 520),
    "bblocker":      ("Bisoprolol",    "C07AB07", "beta_blocker", 340),
    "mra":           ("Spironolactone","C03DA01", "mra", 280),
    "arni":          ("Sacubitril/Valsartan", "C09DX04", "arni", 7100),
    "antiplatelet":  ("Aspirin 81mg",  "B01AC06", "antiplatelet", 120),
    "doac":          ("Apixaban",      "B01AF02", "anticoagulant", 4900),
    "ccb":           ("Amlodipine",    "C08CA01", "ccb", 310),
}

ADMISSION_REASONS = [
    ("Acute coronary syndrome", 0.20), ("Heart failure decompensation", 0.18),
    ("Stroke / TIA", 0.10), ("Hypoglycaemia", 0.12), ("DKA / HHS", 0.08),
    ("Acute kidney injury", 0.10), ("Diabetic foot infection", 0.10),
    ("Uncontrolled hyperglycaemia", 0.07), ("Elective procedure", 0.05)]


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
        age = int(np.clip(RNG.normal(nat_age[nat], 11), 24, 88))
        birth = TODAY - timedelta(days=age * 365 + int(RNG.integers(0, 365)))
        facility = str(RNG.choice(fac_ids, p=[0.10, 0.05, 0.06, 0.04, 0.05] + [0.70 / 13] * 13))
        diabetes_type = "none"
        r = RNG.random()
        if r < 0.86:
            diabetes_type = "type2"
        elif r < 0.91:
            diabetes_type = "type1"
        # 9% are cardiovascular-only patients (no diabetes) — the HIE covers the
        # whole cardiometabolic programme, not a diabetes registry alone.
        years_dx = float(np.clip(RNG.gamma(3.2, 3.0), 0.3, min(age - 20, 40))) if diabetes_type != "none" else 0.0
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
    sev = (0.45 * age_z + 0.50 * dur_z + 0.90 * (pat["access_factor"] - 1) * 3
           + RNG.normal(0, 0.8, n))
    pat["severity"] = sev

    pat["smoker"] = ((pat["gender"] == "male") & (RNG.random(n) <
                     np.where(pat["nationality"].isin(["Bangladeshi", "Nepali", "Egyptian"]), 0.38, 0.22))).astype(int)
    pat["bmi_base"] = np.clip(RNG.normal(30.5 + sev * 1.2, 4.2), 19, 52).round(1)
    has_dm = pat["diabetes_type"] != "none"
    # access_factor > 1 (worse healthcare access) directly worsens control — the equity story
    pat["hba1c_base"] = np.where(
        has_dm,
        np.clip(RNG.normal(7.30 + sev * 0.55 + (pat["access_factor"] - 1) * 1.6, 0.9), 5.6, 13.5),
        np.clip(RNG.normal(5.8, 0.4), 5.0, 6.9)).round(2)
    pat["sbp_base"] = np.clip(RNG.normal(133 + sev * 5.5, 12), 102, 205).round(0)
    pat["ldl_base"] = np.clip(RNG.normal(2.9 + sev * 0.28, 0.75), 1.0, 6.4).round(2)
    pat["egfr_base"] = np.clip(RNG.normal(88 - pat["age"] * 0.55 - sev * 6, 14) + 30, 8, 125).round(0)

    p = 1 / (1 + np.exp(-(sev * 0.9 + age_z * 0.7 - 0.4)))
    pat["htn"] = (RNG.random(n) < np.clip(p + 0.25, 0, 0.95)).astype(int)
    pat["dyslipidemia"] = (RNG.random(n) < np.clip(p + 0.30, 0, 0.95)).astype(int)
    pat["cad"] = (RNG.random(n) < np.clip(p * 0.42, 0, 0.9)).astype(int)
    pat["hf"] = (RNG.random(n) < np.clip(p * 0.20 + pat["cad"] * 0.10, 0, 0.7)).astype(int)
    pat["stroke"] = (RNG.random(n) < np.clip(p * 0.14, 0, 0.5)).astype(int)
    pat["pad"] = (RNG.random(n) < np.clip(p * 0.10, 0, 0.4)).astype(int)
    pat["af"] = (RNG.random(n) < np.clip(0.02 + age_z.clip(0) * 0.045 + pat["hf"] * 0.10, 0, 0.5)).astype(int)
    pat["retinopathy"] = (has_dm & (RNG.random(n) < np.clip(0.06 + dur_z * 0.16, 0, 0.6))).astype(int)
    pat["neuropathy"] = (has_dm & (RNG.random(n) < np.clip(0.05 + dur_z * 0.13, 0, 0.5))).astype(int)
    pat["established_cvd"] = ((pat["cad"] | pat["hf"] | pat["stroke"] | pat["pad"]) == 1).astype(int)
    pat["ef"] = np.where(pat["hf"] == 1,
                         np.clip(RNG.normal(42, 11, n), 15, 65).round(0), np.nan)

    # Simplified 10-year ASCVD-style risk (%) for banding
    risk10 = (3 + (pat["age"] - 40).clip(0) * 0.45 + pat["smoker"] * 6
              + (pat["sbp_base"] - 120).clip(0) * 0.18 + (pat["ldl_base"] - 2.0).clip(0) * 3.2
              + has_dm.astype(int) * 7 + pat["established_cvd"] * 18
              + (60 - pat["egfr_base"]).clip(0) * 0.15 + RNG.normal(0, 2.5, n))
    pat["ascvd_10yr_pct"] = np.clip(risk10, 0.5, 75).round(1)
    pat["cv_risk_band"] = pd.cut(pat["ascvd_10yr_pct"], [0, 12, 27, 40, 100],
                                 labels=["Low", "Moderate", "High", "Very High"]).astype(str)
    return pat


def build_medications(pat: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(pat)
    has_dm = (pat["diabetes_type"] != "none").to_numpy()
    t1 = (pat["diabetes_type"] == "type1").to_numpy()
    sev = pat["severity"].to_numpy()
    high_risk = pat["cv_risk_band"].isin(["High", "Very High"]).to_numpy()

    def add(mask, key, adherence=0.9):
        name, atc, cls, cost = MEDS[key]
        for idx in np.where(mask)[0]:
            start = rand_date(OBS_START - timedelta(days=900), TODAY - timedelta(days=120))
            active = RNG.random() < adherence
            rows.append({
                "patient_id": pat.at[idx, "patient_id"], "medication": name, "atc_code": atc,
                "drug_class": cls, "start_date": start.isoformat(),
                "status": "active" if active else "stopped",
                "annual_cost_qar": cost if active else 0,
            })

    add(has_dm & ~t1 & (RNG.random(n) < 0.90), "metformin")
    # Deliberate GLP-1/SGLT2 under-use in the sickest segment → the "GLP-1 gap" story
    add(has_dm & ~t1 & (RNG.random(n) < np.clip(0.34 - (sev > 1.2) * 0.12, 0.05, 1)), "sglt2")
    add(has_dm & ~t1 & (RNG.random(n) < np.clip(0.20 - (sev > 1.2) * 0.08, 0.03, 1)), "glp1")
    add(has_dm & ~t1 & (RNG.random(n) < 0.30), "sulfonylurea")
    add(has_dm & ~t1 & (RNG.random(n) < 0.22), "dpp4")
    add((t1 | (has_dm & (sev > 1.0))) & (RNG.random(n) < 0.85), "insulin_basal")

    # Statins: ~78% of established CVD treated → leaves the secondary-prevention gap
    est = pat["established_cvd"].to_numpy() == 1
    statin_p = np.where(est, 0.78, np.where(high_risk, 0.55, 0.38))
    statin_mask = RNG.random(n) < statin_p
    hi_int = statin_mask & (est | (RNG.random(n) < 0.4))
    add(hi_int, "statin_high", 0.95)
    add(statin_mask & ~hi_int, "statin_mod", 0.95)

    htn = pat["htn"].to_numpy() == 1
    add(htn & (RNG.random(n) < 0.55), "acei")
    add(htn & (RNG.random(n) < 0.30), "arb")
    add(htn & (RNG.random(n) < 0.40), "ccb")
    hf = pat["hf"].to_numpy() == 1
    hfr = hf & (pat["ef"].to_numpy() < 40)
    add(hf & (RNG.random(n) < 0.80), "bblocker")
    add(hfr & (RNG.random(n) < 0.45), "mra")        # GDMT gap: MRA + ARNI under-used
    add(hfr & (RNG.random(n) < 0.30), "arni")
    add(est & (RNG.random(n) < 0.85), "antiplatelet")
    add((pat["af"].to_numpy() == 1) & (RNG.random(n) < 0.72), "doac")   # AF anticoagulation gap
    return pd.DataFrame(rows)


def build_conditions(pat: pd.DataFrame) -> pd.DataFrame:
    rows = []
    flag_cols = ["htn", "dyslipidemia", "cad", "hf", "stroke", "pad", "af", "retinopathy", "neuropathy"]
    for idx, p in pat.iterrows():
        conds = []
        if p["diabetes_type"] == "type2":
            conds.append("t2dm")
        elif p["diabetes_type"] == "type1":
            conds.append("t1dm")
        conds += [c for c in flag_cols if p[c] == 1]
        if p["egfr_base"] < 60:
            conds.append("ckd")
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
        on_statin = any("statin" in c for c in classes)
        has_dm = p["diabetes_type"] != "none"

        # Per-patient annual drift: newer agents improve control; untreated severe worsens
        hba1c_drift = (-0.35 if on_new_dm else (0.12 if p["severity"] > 1.0 else -0.05))
        ldl_eff = -1.1 if on_statin else 0.0
        egfr_drift = -1.2 - max(p["severity"], 0) * 1.1

        def jitter(base, sd):
            return float(RNG.normal(base, sd))

        # HbA1c ~ every 3-5 months (some overdue patients stop testing → care gap)
        if has_dm:
            t = 0.0
            stop_testing = RNG.random() < 0.16       # ~16% become overdue
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
            ldl = np.clip(jitter(p["ldl_base"] + ldl_eff, 0.25), 0.7, 7.0)
            rows.append((pid, "ldl", d.isoformat(), round(ldl, 2)))
            rows.append((pid, "hdl", d.isoformat(), round(np.clip(RNG.normal(1.1, 0.22), 0.5, 2.4), 2)))
            rows.append((pid, "tg", d.isoformat(), round(np.clip(RNG.normal(1.9 + p["severity"] * 0.2, 0.6), 0.5, 8), 2)))

        # Renal ~ annual; ACR only for ~70% of diabetics (screening gap)
        for k in range(3):
            d = OBS_START + timedelta(days=int((k * 12 + RNG.uniform(1, 4)) * 30.4))
            if d > TODAY:
                break
            rows.append((pid, "egfr", d.isoformat(),
                         round(np.clip(p["egfr_base"] + egfr_drift * k + RNG.normal(0, 4), 5, 130), 0)))
            if has_dm and RNG.random() < 0.70:
                rows.append((pid, "acr", d.isoformat(),
                             round(float(np.clip(RNG.lognormal(1.0 + max(p["severity"], 0) * 0.5, 0.9), 0.3, 300)), 1)))

        # BMI ~ annual
        for k in range(3):
            d = OBS_START + timedelta(days=int((k * 12 + RNG.uniform(2, 6)) * 30.4))
            if d > TODAY:
                break
            rows.append((pid, "bmi", d.isoformat(),
                         round(np.clip(p["bmi_base"] + RNG.normal(0, 0.8) - (0.6 * k if on_new_dm else 0), 17, 55), 1)))

        # EF for HF patients ~ annual
        if p["hf"] == 1 and not np.isnan(p["ef"]):
            for k in range(2):
                d = OBS_START + timedelta(days=int((k * 14 + RNG.uniform(2, 8)) * 30.4))
                if d > TODAY:
                    break
                rows.append((pid, "ef", d.isoformat(), round(np.clip(p["ef"] + RNG.normal(0, 3), 12, 70), 0)))

    df = pd.DataFrame(rows, columns=["patient_id", "obs_key", "effective_date", "value"])
    df["loinc_code"] = df["obs_key"].map(lambda k: LOINC[k][0])
    df["display"] = df["obs_key"].map(lambda k: LOINC[k][1])
    df["unit"] = df["obs_key"].map(lambda k: LOINC[k][2])
    return df.sort_values(["patient_id", "effective_date"]).reset_index(drop=True)


def build_encounters(pat: pd.DataFrame) -> pd.DataFrame:
    reasons = [r for r, _ in ADMISSION_REASONS]
    reason_w = np.array([w for _, w in ADMISSION_REASONS]); reason_w = reason_w / reason_w.sum()
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
                             "reason": "Chronic disease follow-up"})
            month = (month.replace(day=1) + timedelta(days=32)).replace(day=1)

        # ED visits & admissions driven by risk
        risk_lift = 1 / (1 + np.exp(-sev))
        n_ed = int(RNG.poisson(0.55 * risk_lift * 3))
        for _ in range(n_ed):
            eid += 1
            rows.append({"encounter_id": f"E{eid:07d}", "patient_id": p["patient_id"],
                         "facility_id": "F001" if RNG.random() < 0.6 else p["primary_facility_id"],
                         "encounter_type": "emergency",
                         "start_date": rand_date(OBS_START, TODAY).isoformat(),
                         "length_of_stay_days": 0, "reason": "Emergency presentation"})
        n_adm = int(RNG.poisson(0.30 * risk_lift * 3 + p["hf"] * 0.35 + p["established_cvd"] * 0.2))
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
    med_count = active.groupby("patient_id").size().to_dict()

    latest = (obs.sort_values("effective_date").groupby(["patient_id", "obs_key"])
              .tail(1).pivot(index="patient_id", columns="obs_key", values="value"))
    last_date = (obs.sort_values("effective_date").groupby(["patient_id", "obs_key"])
                 ["effective_date"].last().unstack())

    enc12 = enc[enc["start_date"] >= (TODAY - timedelta(days=365)).isoformat()]
    adm12 = enc12[enc12["encounter_type"] == "inpatient"].groupby("patient_id").size().to_dict()
    ed12 = enc12[enc12["encounter_type"] == "emergency"].groupby("patient_id").size().to_dict()
    out12 = enc12[enc12["encounter_type"].isin(["outpatient", "telehealth"])].groupby("patient_id").size().to_dict()
    last_visit = enc.groupby("patient_id")["start_date"].max().to_dict()

    rows = []
    for _, p in pat.iterrows():
        pid = p["patient_id"]
        cls = classes.get(pid, set())
        lv = latest.loc[pid] if pid in latest.index else pd.Series(dtype=float)
        ld = last_date.loc[pid] if pid in last_date.index else pd.Series(dtype=object)
        has_dm = p["diabetes_type"] != "none"

        hba1c = float(lv.get("hba1c", np.nan))
        sbp = float(lv.get("sbp", np.nan)); dbp = float(lv.get("dbp", np.nan))
        ldl = float(lv.get("ldl", np.nan)); egfr = float(lv.get("egfr", np.nan))
        bmi = float(lv.get("bmi", p["bmi_base"]))
        acr = float(lv.get("acr", np.nan))

        on_statin = any("statin" in c for c in cls)
        on_new_dm = bool({"sglt2_inhibitor", "glp1_agonist"} & cls)
        on_raas = "raas_inhibitor" in cls
        on_anticoag = "anticoagulant" in cls
        on_bb = "beta_blocker" in cls
        on_mra = "mra" in cls
        on_arni = "arni" in cls
        hfr = p["hf"] == 1 and (not np.isnan(p["ef"])) and p["ef"] < 40

        days = lambda iso: (TODAY - date.fromisoformat(iso)).days if isinstance(iso, str) else 99999
        hba1c_days = days(ld.get("hba1c"))
        control = ("well_controlled" if hba1c < 7 else
                   "moderate" if hba1c < 8 else "uncontrolled") if has_dm and not np.isnan(hba1c) else "n/a"
        ckd_stage = ("G1" if egfr >= 90 else "G2" if egfr >= 60 else "G3a" if egfr >= 45
                     else "G3b" if egfr >= 30 else "G4" if egfr >= 15 else "G5") if not np.isnan(egfr) else "n/a"
        high_risk = p["cv_risk_band"] in ("High", "Very High")

        gaps = []
        if has_dm and hba1c_days > 183: gaps.append("hba1c_overdue")
        if has_dm and RNG.random() < 0.28: gaps.append("retinal_screening_overdue")
        if has_dm and RNG.random() < 0.22: gaps.append("foot_exam_overdue")
        if has_dm and np.isnan(acr): gaps.append("acr_screening_missing")
        if high_risk and not on_statin: gaps.append("statin_gap")
        if not np.isnan(sbp) and (sbp >= 140 or dbp >= 90) and p["htn"] == 1: gaps.append("bp_uncontrolled")
        if (has_dm and p["diabetes_type"] == "type2" and not on_new_dm
                and not np.isnan(hba1c) and hba1c >= 8 and (bmi >= 30 or p["established_cvd"] == 1)):
            gaps.append("glp1_sglt2_gap")
        if hfr and not (on_bb and on_raas and on_mra and (on_arni or on_raas)): gaps.append("hf_gdmt_gap")
        if p["af"] == 1 and not on_anticoag: gaps.append("af_anticoagulation_gap")

        prior_adm = int(adm12.get(pid, 0))
        # ── Outcome label: cardiometabolic event (admission/ACS/HF/stroke) next 12 months.
        # Ground-truth logistic model — the ML task is to recover these drivers.
        drivers = (0.28 * max(p["age"] - 50, 0) / 10
                   + (0.28 * max(hba1c - 7, 0) if not np.isnan(hba1c) else 0)
                   + (0.15 * max(sbp - 130, 0) / 10 if not np.isnan(sbp) else 0)
                   + (0.40 * max(ldl - 2.6, 0) if not np.isnan(ldl) else 0)
                   + (0.65 * max(60 - egfr, 0) / 15 if not np.isnan(egfr) else 0)
                   + 0.65 * p["established_cvd"] + 0.70 * p["hf"] + 0.55 * p["af"]
                   + 0.65 * p["smoker"] + 0.35 * min(prior_adm, 3)
                   + 0.10 * max(bmi - 30, 0) / 5
                   - (0.60 if (on_statin and high_risk) else 0)
                   - (0.45 if on_new_dm else 0)
                   - (0.50 if (on_anticoag and p["af"] == 1) else 0))
        z = -4.55 + 1.85 * drivers
        p_event = 1 / (1 + np.exp(-z))
        event = int(RNG.random() < p_event)

        cost = (2800 + out12.get(pid, 0) * 450 + ed12.get(pid, 0) * 1900
                + prior_adm * 22000 + med_cost.get(pid, 0)
                + p["established_cvd"] * 2600 + (p["retinopathy"] + p["neuropathy"]) * 1500)
        cost *= float(RNG.lognormal(0, 0.18))

        # Legacy rules-based registry score (what the ML model replaces): crude point
        # buckets, blind to renal function, lipids, smoking, AF and treatment status —
        # deliberately the kind of score national registries actually run today.
        legacy = (20 * (p["age"] >= 60)
                  + 20 * (not np.isnan(hba1c) and hba1c >= 9)
                  + 10 * (not np.isnan(hba1c) and 8 <= hba1c < 9)
                  + 25 * (prior_adm > 0)
                  + 25 * p["established_cvd"]
                  + 10 * (not np.isnan(sbp) and sbp >= 160))
        rows.append({
            "patient_id": pid, "full_name": p["full_name"], "gender": p["gender"], "age": p["age"],
            "nationality": p["nationality"], "residency_status": p["residency_status"],
            "district": p["district"], "insurance": p["insurance"],
            "primary_facility_id": p["primary_facility_id"],
            "diabetes_type": p["diabetes_type"], "years_since_diagnosis": p["years_since_diagnosis"],
            "consent_status": p["consent_status"], "smoker": p["smoker"],
            "bmi": round(bmi, 1),
            "hba1c_latest": None if np.isnan(hba1c) else round(hba1c, 1),
            "hba1c_days_since_test": None if hba1c_days > 9000 else hba1c_days,
            "glycaemic_control": control,
            "sbp_latest": None if np.isnan(sbp) else sbp, "dbp_latest": None if np.isnan(dbp) else dbp,
            "bp_controlled": None if np.isnan(sbp) else int(sbp < 140 and dbp < 90),
            "ldl_latest": None if np.isnan(ldl) else ldl,
            "ldl_at_target": None if np.isnan(ldl) else int(ldl <= (1.8 if p["established_cvd"] else 2.6)),
            "egfr_latest": None if np.isnan(egfr) else egfr, "ckd_stage": ckd_stage,
            "acr_latest": None if np.isnan(acr) else acr,
            "htn": p["htn"], "dyslipidemia": p["dyslipidemia"], "cad": p["cad"], "hf": p["hf"],
            "stroke": p["stroke"], "pad": p["pad"], "af": p["af"],
            "retinopathy": p["retinopathy"], "neuropathy": p["neuropathy"],
            "established_cvd": p["established_cvd"],
            "ef_latest": None if np.isnan(p["ef"]) else p["ef"],
            "ascvd_10yr_pct": p["ascvd_10yr_pct"], "cv_risk_band": p["cv_risk_band"],
            "on_statin": int(on_statin), "on_sglt2_glp1": int(on_new_dm),
            "on_raas_inhibitor": int(on_raas), "on_beta_blocker": int(on_bb),
            "on_mra": int(on_mra), "on_arni": int(on_arni),
            "on_antiplatelet": int("antiplatelet" in cls), "on_anticoagulant": int(on_anticoag),
            "on_insulin": int("insulin" in cls),
            "medication_count": int(med_count.get(pid, 0)),
            "open_care_gaps": ";".join(gaps), "care_gap_count": len(gaps),
            "outpatient_visits_12mo": int(out12.get(pid, 0)),
            "ed_visits_12mo": int(ed12.get(pid, 0)), "admissions_12mo": prior_adm,
            "last_visit_date": last_visit.get(pid),
            "annual_cost_qar": round(cost, 0),
            "legacy_risk_score": round(legacy, 1),
            "event_probability_true": round(float(p_event), 4),   # hidden ground truth (kept for eval)
            "event_next_12m": event,
        })
    return pd.DataFrame(rows)


def build_care_gaps(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    labels = {
        "hba1c_overdue": "HbA1c test overdue (>6 months)",
        "retinal_screening_overdue": "Retinal screening overdue (>12 months)",
        "foot_exam_overdue": "Diabetic foot exam overdue (>12 months)",
        "acr_screening_missing": "Urine ACR screening missing (12 months)",
        "statin_gap": "High CV risk with no statin therapy",
        "bp_uncontrolled": "Hypertension uncontrolled (≥140/90)",
        "glp1_sglt2_gap": "T2DM with obesity/CVD not on SGLT2i/GLP-1 RA",
        "hf_gdmt_gap": "HFrEF missing guideline-directed medical therapy pillar(s)",
        "af_anticoagulation_gap": "Atrial fibrillation without anticoagulation",
    }
    for _, r in summary.iterrows():
        if not r["open_care_gaps"]:
            continue
        for g in r["open_care_gaps"].split(";"):
            rows.append({"patient_id": r["patient_id"], "gap_key": g, "gap_label": labels[g],
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
    "patients": "Registry of 4,000 cardiometabolic patients: demographics, nationality, district, insurance, primary facility, diabetes type, consent status.",
    "conditions": "Active problem list per patient with ICD-10-CM and SNOMED CT codes and onset dates (diabetes, hypertension, dyslipidaemia, CAD, heart failure, stroke, PAD, AF, CKD, obesity, retinopathy, neuropathy).",
    "observations": "Longitudinal LOINC-coded labs and vitals over 36 months: HbA1c, fasting glucose, SBP/DBP, LDL/HDL/TG, eGFR, ACR, BMI, ejection fraction. Columns: patient_id, obs_key, loinc_code, effective_date, value, unit.",
    "medications": "ATC-coded medication orders with drug class, start date, status (active/stopped) and annual cost: metformin, SGLT2i, GLP-1 RA, insulin, statins, RAAS inhibitors, beta blockers, MRA, ARNI, antiplatelets, anticoagulants.",
    "encounters": "All visits over 36 months: outpatient, telehealth, emergency, inpatient (with length of stay and admission reason), facility, date.",
    "care_gaps": "Open guideline-derived care gaps per patient: HbA1c overdue, retinal/foot/ACR screening, statin gap, BP uncontrolled, GLP-1/SGLT2 gap, HF GDMT gap, AF anticoagulation gap.",
    "patient_summary": "Wide per-patient analytical table: latest labs, therapy flags (on_statin, on_sglt2_glp1, on_anticoagulant, ...), CV risk band, ASCVD 10-yr %, care gaps, 12-month utilisation, annual cost (QAR), and the event_next_12m outcome label used to train the risk model.",
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
    enc = build_encounters(pat)
    print("Deriving patient summary + outcome labels…")
    summary = build_summary(pat, meds, obs, enc)
    gaps = build_care_gaps(summary)

    fac = pd.DataFrame(FACILITIES, columns=["facility_id", "facility_name", "facility_type",
                                            "region", "quality_factor"])
    patients_out = pat.drop(columns=["access_factor", "severity", "bmi_base", "hba1c_base",
                                     "sbp_base", "ldl_base", "egfr_base", "ef",
                                     "htn", "dyslipidemia", "cad", "hf", "stroke", "pad", "af",
                                     "retinopathy", "neuropathy", "established_cvd",
                                     "smoker", "ascvd_10yr_pct", "cv_risk_band"])

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

    # Sanity print
    s = summary
    print("\n── Cohort sanity check ──")
    print(f"patients: {len(s):,} | mean HbA1c: {s['hba1c_latest'].mean():.2f}"
          f" | well-controlled: {(s['glycaemic_control']=='well_controlled').mean()*100:.1f}%")
    print(f"established CVD: {s['established_cvd'].mean()*100:.1f}% | "
          f"statin gap: {s['open_care_gaps'].str.contains('statin_gap').sum()} | "
          f"AF anticoag gap: {s['open_care_gaps'].str.contains('af_anticoagulation_gap').sum()}")
    print(f"event rate (12m label): {s['event_next_12m'].mean()*100:.1f}% | "
          f"total annual cost: QAR {s['annual_cost_qar'].sum()/1e6:.1f}M")
    print(f"BP uncontrolled: {s['open_care_gaps'].str.contains('bp_uncontrolled').sum()} | "
          f"GLP-1/SGLT2 gap: {s['open_care_gaps'].str.contains('glp1_sglt2_gap').sum()} | "
          f"HF GDMT gap: {s['open_care_gaps'].str.contains('hf_gdmt_gap').sum()}")


if __name__ == "__main__":
    main()
