import os
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from slack_sdk import WebClient

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

client = WebClient(token=os.environ["SLACK_TOKEN"])


client.chat_postMessage(channel="#test", text="wassup")


def read_motec_csv(csv_path):
    """
    Reads a MoTeC CSV file

    Row 14 contains the column names
    Row 15 contains the units
    Row 18 onwards is data
    """
    df = pd.read_csv(csv_path, header=14)
    df = df.iloc[1:].reset_index(drop=True)

    return df


def create_engine_speed_graph(df):
    """
    Creates a graph of Engine Speed vs Time.
    """

    plt.figure(figsize=(12, 6))

    plt.plot(df["Time"], df["Engine Speed"])

    plt.title("Engine Speed vs Time")
    plt.xlabel("Time (s)")
    plt.ylabel("Engine Speed (rpm)")

    plt.tight_layout()

    graph_path = "engine_speed.png"

    plt.savefig(graph_path)
    plt.close()

    return graph_path


# Graph Config

GRAPH_CONFIG = {"#engine": ["Engine Speed"]}


def process_csv(csv_path):

    print(f"Reading CSV: {csv_path}")

    df = read_motec_csv(csv_path)

    print("\nCSV successfully loaded!")

    print(f"Number of rows: {len(df)}")
    print(f"Number of columns: {len(df.columns)}")

    print("\nFirst 10 columns:")
    print(df.columns[:10].tolist())

    print("\nFirst 5 rows:")
    print(df.head())


if __name__ == "__main__":

    csv_path = "S1_#11698_20260313_191152.csv"

    if os.path.exists(csv_path):

        process_csv(csv_path)

    else:

        print(f"Could not find CSV: {csv_path}")
