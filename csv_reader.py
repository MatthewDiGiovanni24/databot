"""Parse MoTeC CSV exports into a shared dataframe."""

import csv

import pandas as pd


def read_motec_csv(csv_path):
    """Read MoTeC channel names and numeric samples, skipping metadata and units."""
    log_date = "Unknown date"
    with open(csv_path, newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if len(row) > 1 and row[0].strip() == "Log Date":
                log_date = row[1].strip() or "Unknown date"
            if len(row) > 1 and row[0].strip() == "Time":
                columns = [name.strip() for name in row]
                break
        else:
            raise ValueError(
                "MoTeC CSV channel header beginning with 'Time' was not found."
            )

        units = next(reader, None)
        if units is None or len(units) != len(columns):
            raise ValueError(
                "MoTeC CSV units row is missing or does not match the channels."
            )
        # line_num counts physical lines, including blank metadata lines.
        data_start = reader.line_num

    df = pd.read_csv(
        csv_path,
        skiprows=data_start,
        header=None,
        names=columns,
        encoding="utf-8-sig",
        dtype=float,
    )
    df.attrs["units"] = dict(zip(columns, units))
    df.attrs["log_date"] = log_date
    return df
