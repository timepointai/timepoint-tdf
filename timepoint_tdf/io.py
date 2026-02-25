from .record import TDFRecord


def write_tdf_jsonl(records: list[TDFRecord], path: str) -> None:
    with open(path, "w") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")


def read_tdf_jsonl(path: str) -> list[TDFRecord]:
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(TDFRecord.model_validate_json(line))
    return records
