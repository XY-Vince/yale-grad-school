"""
Export unified JSON schema from Pydantic RootBundle.
Generates references/claim-schema.json natively with unified $defs.
"""

import json
from pathlib import Path
from pydantic import TypeAdapter

from .schemas import RootBundle


def export_schemas():
    adapter = TypeAdapter(RootBundle)
    full_schema = adapter.json_schema()
    full_schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    full_schema["title"] = "VerifyPublicPersonProfileBundleSchema"
    full_schema["description"] = "Unified schema bundle for public person intelligence and verification."

    output_path = Path(__file__).resolve().parent.parent / "references" / "claim-schema.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_schema, f, indent=2, ensure_ascii=False)
    print(f"Exported unified JSON schema to {output_path}")


if __name__ == "__main__":
    export_schemas()
