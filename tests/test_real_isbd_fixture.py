from pathlib import Path

from iridiumSBD import IridiumSBD, valid_isbd
from iridiumSBD.processing.postprocess_isbd import process_isbd


FIXTURE = Path(__file__).parent / "fixtures" / "20250408094516842289_192.108.98.11.isbd"


def test_real_isbd_fixture_parses():
    data = FIXTURE.read_bytes()
    msg = IridiumSBD(data)

    assert valid_isbd(data)
    assert msg.attributes["header"]["IMEI"] == "301434060001890"
    assert msg.attributes["header"]["MOMSN"] == 40303
    assert msg.attributes["location"]["latitude"] == 1.9907166666666667
    assert msg.attributes["location"]["longitude"] == -157.524
    assert msg.payload["length"] == 167
    assert msg.payload["data"].decode("utf-8").endswith("KI-KIRITIMATI ")


def test_real_isbd_postprocess_raw_only(tmp_path):
    inbox = tmp_path / "data" / "inbox"
    inbox.mkdir(parents=True)

    input_file = inbox / FIXTURE.name
    input_file.write_bytes(FIXTURE.read_bytes())

    raw_path, csv_path = process_isbd(
        input_file=input_file,
        data_dir=tmp_path / "data",
        year=2025,
        decode=False,
    )

    assert raw_path.exists()
    assert csv_path is None
    assert raw_path.name == "20250408094516-301434060001890.raw"
    assert "KI-KIRITIMATI" in raw_path.read_text()
    assert not input_file.exists()
    assert (tmp_path / "data" / "archive" / "20250408" / FIXTURE.name).exists()


def test_real_isbd_postprocess_decodes_to_csv(tmp_path):
    inbox = tmp_path / "data" / "inbox"
    inbox.mkdir(parents=True)

    input_file = inbox / FIXTURE.name
    input_file.write_bytes(FIXTURE.read_bytes())

    raw_path, csv_path = process_isbd(
        input_file=input_file,
        data_dir=tmp_path / "data",
        year=2025,
    )

    assert raw_path.exists()
    assert csv_path.exists()
    assert csv_path.name == "KI-KIRITIMATI_2025.csv"

    lines = csv_path.read_text().splitlines()
    assert lines[0] == "time,sensor,data"
    assert len(lines) == 29  # header + 28 decoded rows
    assert "2025-04-08 09:40:00+00:00,PRS,9.999" in lines
    assert "2025-04-08 09:40:00+00:00,ATM,1010.2" in lines
