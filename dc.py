"""DC telemetry reports."""

from io import BytesIO

import matplotlib.pyplot as plt


def send_dc_report(df, client, channel):
    """Send brake temperatures and a recorded clutch efficiency channel."""
    graphs = [
        ("brake_temperatures.png", "Brake Temperatures vs Time",
         ["Brake Temperature Front", "Brake Temperature Rear"], False),
        ("clutch_efficiency.png", "Clutch Efficiency vs Time",
         ["Clutch Efficiency"], False),
    ]

    if "Time" not in df:
        raise ValueError("Reports require a Time channel.")
    missing = []
    available = []
    for filename, title, columns, step in graphs:
        usable = []
        for column in columns:
            if column not in df or not df[["Time", column]].dropna().shape[0]:
                missing.append(column)
            else:
                usable.append(column)
        if usable:
            available.append((filename, title, usable, step))

    message = f"DC Report for {df.attrs.get('log_date', 'Unknown date')}"
    if missing:
        message += "\nMissing or empty data: " + ", ".join(missing)
    client.chat_postMessage(channel=channel, text=message)

    units = df.attrs.get("units", {})
    for filename, title, columns, step in available:
        fig, ax = plt.subplots(figsize=(12, 6))
        try:
            for column in columns:
                samples = df[["Time", column]].dropna()
                label = column
                unit = units.get(column, "").strip()
                if unit:
                    label += f" ({unit})"
                if step:
                    ax.step(samples["Time"], samples[column], where="post", label=label)
                else:
                    ax.plot(samples["Time"], samples[column], label=label)
            ax.set_title(title)
            ax.set_xlabel(f"Time ({units.get('Time', 's') or 's'})")
            graph_units = {units.get(column, "").strip() for column in columns}
            ax.set_ylabel(graph_units.pop() if len(graph_units) == 1 else "Value")
            ax.legend()
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            with BytesIO() as image:
                fig.savefig(image, format="png")
                image.seek(0)
                client.files_upload_v2(
                    channel=channel, file=image, filename=filename, title=title
                )
        finally:
            plt.close(fig)
    print(f"DC report uploaded to Slack.")
