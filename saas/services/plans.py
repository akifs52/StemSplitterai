from sqlalchemy.orm import Session

from saas.models import Plan


DEFAULT_PLANS = [
    {"id": "free", "name": "Free", "monthly_job_limit": 20, "max_upload_mb": 500},
    {"id": "pro", "name": "Pro", "monthly_job_limit": 500, "max_upload_mb": 2048},
]


def ensure_default_plans(db: Session) -> None:
    for item in DEFAULT_PLANS:
        plan = db.get(Plan, item["id"])
        if plan is None:
            db.add(Plan(**item))
    db.commit()


def get_free_plan(db: Session) -> Plan:
    plan = db.get(Plan, "free")
    if plan is None:
        ensure_default_plans(db)
        plan = db.get(Plan, "free")
    return plan

