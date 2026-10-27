import os
from pathlib import Path

from dotenv import load_dotenv
from slack_sdk import WebClient

from csv_reader import read_motec_csv
from electrical_system import send_electrical_report
from chassis import send_chassis_report
from power_train import send_power_train_report
from dc import send_dc_report


def main():
    base_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=base_dir / ".env")
    csv_path = base_dir / "S1_#11698_20260313_191152.csv"

    if not csv_path.exists():
        print(f"Could not find CSV: {csv_path}")
        return

    client = WebClient(token=os.environ["SLACK_TOKEN"])
    print(f"Reading CSV: {csv_path}")
    df = read_motec_csv(csv_path)
    print(f"CSV successfully loaded: {len(df)} rows, {len(df.columns)} columns.")
    # Set each report's destination in .env to enable automatic delivery.
    for variable, send_report in (
        ("ELECTRICAL_CHANNEL", send_electrical_report),
        ("CHASSIS_CHANNEL", send_chassis_report),
        ("POWER_TRAIN_CHANNEL", send_power_train_report),
        ("DC_CHANNEL", send_dc_report),
    ):
        channel = os.environ.get(variable)
        if channel:
            send_report(df, client, channel)
        else:
            print(f"Skipping {send_report.__name__}: set {variable} in .env.")


if __name__ == "__main__":
    main()
