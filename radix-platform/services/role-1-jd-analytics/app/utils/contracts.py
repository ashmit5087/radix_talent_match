"""Export the shared JSON contracts from the Pydantic models (single source of truth).

    python -m app.utils.contracts          # (re)write contracts/*.json

A test fails if the committed files differ from what the models generate, so they cannot drift.
"""
import json

from app.config import PROJECT_ROOT
from app.schemas import JDAnalysisResponse, Skill

CONTRACTS_DIR = PROJECT_ROOT / "contracts"


def build_contracts() -> dict[str, str]:
    return {
        "skill.schema.json": Skill.model_json_schema(),
        "jd-analysis.schema.json": JDAnalysisResponse.model_json_schema(),
    }


def render(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_contracts() -> None:
    CONTRACTS_DIR.mkdir(exist_ok=True)
    for name, schema in build_contracts().items():
        (CONTRACTS_DIR / name).write_text(render(schema), encoding="utf-8")
        print(f"wrote contracts/{name}")


if __name__ == "__main__":
    write_contracts()
