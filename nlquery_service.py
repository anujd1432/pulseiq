import json
import re
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.grok_client import ask_grok, is_grok_configured
from app.models.admission import Admission
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.department import Department


PARSE_SYSTEM_PROMPT = """You convert a hospital administrator's natural language question into a strict JSON filter spec. Output ONLY valid JSON, no markdown, no explanation, no code fences.

Schema (all keys optional, use null if not mentioned):
{
  "age_min": integer or null,
  "age_max": integer or null,
  "gender": "Male" or "Female" or null,
  "diagnosis_contains": string or null,
  "department_contains": string or null,
  "status": "admitted" or "discharged" or null,
  "date_from": "YYYY-MM-DD" or null,
  "date_to": "YYYY-MM-DD" or null,
  "aggregation": "count" or "avg_length_of_stay" or "list"
}

Rules:
- "aggregation" defaults to "count" unless the question asks for average stay/duration (use "avg_length_of_stay") or asks to list/show records (use "list").
- Only fill fields that are clearly implied by the question. Leave everything else null.
- Do not invent dates; only fill date_from/date_to if a specific time period is mentioned, using today as REPLACE_TODAY_TOKEN.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*|\s*```$", "", text, flags=re.MULTILINE)
    return json.loads(text)


def parse_question_to_spec(question: str) -> dict:
    default_spec = {
        "age_min": None, "age_max": None, "gender": None, "diagnosis_contains": None,
        "department_contains": None, "status": None, "date_from": None, "date_to": None,
        "aggregation": "count"
    }

    if not is_grok_configured():
        return default_spec

    today = datetime.utcnow().strftime("%Y-%m-%d")
    system_prompt = PARSE_SYSTEM_PROMPT.replace("REPLACE_TODAY_TOKEN", today)

    result = ask_grok(system_prompt, question, max_tokens=300)
    if not result["success"]:
        return default_spec

    try:
        spec = _extract_json(result["text"])
        for key in default_spec:
            if key not in spec:
                spec[key] = default_spec[key]
        return spec
    except Exception:
        return default_spec


def execute_spec(db: Session, spec: dict) -> dict:
    query = db.query(Admission).join(Patient, Admission.patient_id == Patient.id)

    if spec.get("age_min") is not None:
        query = query.filter(Patient.age >= spec["age_min"])
    if spec.get("age_max") is not None:
        query = query.filter(Patient.age <= spec["age_max"])
    if spec.get("gender"):
        query = query.filter(Patient.gender == spec["gender"])
    if spec.get("diagnosis_contains"):
        query = query.filter(Admission.diagnosis.ilike(f"%{spec['diagnosis_contains']}%"))
    if spec.get("status"):
        query = query.filter(Admission.status == spec["status"])
    if spec.get("date_from"):
        query = query.filter(Admission.admission_date >= spec["date_from"])
    if spec.get("date_to"):
        query = query.filter(Admission.admission_date <= spec["date_to"])

    if spec.get("department_contains"):
        query = query.join(Doctor, Admission.doctor_id == Doctor.id).join(
            Department, Doctor.department_id == Department.id
        ).filter(Department.name.ilike(f"%{spec['department_contains']}%"))

    aggregation = spec.get("aggregation", "count")

    if aggregation == "avg_length_of_stay":
        records = query.filter(Admission.discharge_date.isnot(None)).all()
        if not records:
            return {"aggregation": "avg_length_of_stay", "value": 0, "matched_records": 0}
        total_days = sum((a.discharge_date - a.admission_date).days for a in records)
        avg_days = round(total_days / len(records), 2)
        return {"aggregation": "avg_length_of_stay", "value": avg_days, "matched_records": len(records)}

    elif aggregation == "list":
        records = query.limit(20).all()
        data = [
            {
                "admission_id": a.id,
                "patient_id": a.patient_id,
                "diagnosis": a.diagnosis,
                "status": a.status,
                "admission_date": str(a.admission_date)
            }
            for a in records
        ]
        total_count = query.count()
        return {"aggregation": "list", "matched_records": total_count, "sample": data}

    else:
        count = query.count()
        return {"aggregation": "count", "value": count, "matched_records": count}


def generate_answer(question: str, spec: dict, computed: dict) -> str:
    if not is_grok_configured():
        return _template_answer(computed)

    system_prompt = (
        "You are a hospital data analyst assistant. Using ONLY the exact numbers provided below "
        "(do not estimate or invent any numbers), answer the administrator's question in 1-3 sentences. "
        "Do not use markdown formatting."
    )
    user_prompt = f"Question: {question}\nFilters applied: {spec}\nComputed result: {computed}"

    result = ask_grok(system_prompt, user_prompt, max_tokens=200)
    if result["success"]:
        return result["text"].strip()
    return _template_answer(computed)


def _template_answer(computed: dict) -> str:
    agg = computed.get("aggregation")
    if agg == "count":
        return f"Found {computed.get('value', 0)} matching record(s)."
    elif agg == "avg_length_of_stay":
        return f"Average length of stay across {computed.get('matched_records', 0)} matching record(s) is {computed.get('value', 0)} days."
    elif agg == "list":
        return f"Found {computed.get('matched_records', 0)} matching record(s). Showing up to 20 in the sample data."
    return "Query executed, but result format was not recognized."


def answer_nl_query(db: Session, question: str) -> dict:
    spec = parse_question_to_spec(question)
    computed = execute_spec(db, spec)
    answer = generate_answer(question, spec, computed)
    return {
        "question": question,
        "parsed_filters": spec,
        "computed_result": computed,
        "answer": answer
    }
