"""Validate output against schemas/output_schema.json."""
import json

import jsonschema


def load_schema(schema_path: str) -> dict:
    with open(schema_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_output(output: dict, schema_path: str) -> None:
    schema = load_schema(schema_path)
    jsonschema.validate(instance=output, schema=schema)
