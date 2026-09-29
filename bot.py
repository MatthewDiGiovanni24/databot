import os
from pathlib import Path

from dotenv import load_dotenv
from slack_sdk import WebClient

from csv_reader import read_motec_csv
from electrical_system import send_electrical_report


def main():
    base_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=base_dir / ".env")
    csv_path = base_dir / "S1_#11698_20260313_191152.csv"
    electrical_channel = "C0C309QTUCR"

    if not csv_path.exists():
        print(f"Could not find CSV: {csv_path}")
        return

    client = WebClient(token=os.environ["SLACK_TOKEN"])
    print(f"Reading CSV: {csv_path}")
    df = read_motec_csv(csv_path)
    print(f"CSV successfully loaded: {len(df)} rows, {len(df.columns)} columns.")
    send_electrical_report(df, client, electrical_channel)


if __name__ == "__main__":
    main()
