"""Shared rendering and delivery helpers for telemetry reports."""

from io import BytesIO

import matplotlib.pyplot as plt


def missing_channels(df, columns):
    if "Time" not in df:
        raise ValueError("Reports require a Time channel.")
    return [column for column in columns
            if column not in df or df[["Time", column]].dropna().empty]


def send_report_message(df, client, channel, system, columns):
    missing = missing_channels(df, columns)
    message = f"{system} Report for {df.attrs.get('log_date', 'Unknown date')}"
    if missing:
        message += "\nMissing or empty data: " + ", ".join(missing)
    return client.chat_postMessage(channel=channel, text=message)


def create_graph(df, title, columns, step=False, x_column="Time"):
    missing = missing_channels(df, columns)
    usable = [column for column in columns if column not in missing]
    if not usable:
        return None
    if x_column not in df:
        return None
    usable = [column for column in usable
              if not df[[x_column, column]].dropna().empty]
    if not usable:
        return None
    units = df.attrs.get("units", {})
    fig, ax = plt.subplots(figsize=(12, 6))
    try:
        for column in usable:
            samples = df[[x_column, column]].dropna()
            unit = units.get(column, "").strip()
            label = f"{column} ({unit})" if unit else column
            if x_column != "Time":
                ax.scatter(samples[x_column], samples[column], s=8, alpha=0.4, label=label)
            elif step:
                ax.step(samples[x_column], samples[column], where="post", label=label)
            else:
                ax.plot(samples[x_column], samples[column], label=label)
        ax.set_title(title)
        x_unit = units.get(x_column, "s" if x_column == "Time" else "").strip()
        ax.set_xlabel(f"{x_column} ({x_unit})" if x_unit else x_column)
        graph_units = {units.get(column, "").strip() for column in usable}
        ax.set_ylabel(graph_units.pop() if len(graph_units) == 1 else "Value")
        ax.legend(fontsize="small")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        image = BytesIO()
        fig.savefig(image, format="png")
        image.seek(0)
        return image
    finally:
        plt.close(fig)


def send_graph(image, client, channel, filename, title):
    if image is None:
        return None
    with image:
        return client.files_upload_v2(
            channel=channel, file=image, filename=filename, title=title
        )
