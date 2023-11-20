from pathlib import Path

machine_id_relative_path = Path("etc") / "machine-id"


def read_machine_id(machine_id_path: Path) -> str:
    with machine_id_path.open("r") as machine_id_file:
        machine_id = machine_id_file.readline().strip()

        return machine_id
