"""Chassis telemetry reports."""

from io import BytesIO

import matplotlib.pyplot as plt


def send_chassis_report(df, client, channel):
    """Send tire temperatures and lateral/longitudinal acceleration graphs."""
    tire_channels = [c for c in df.columns if
                     ("tire" in c.lower() or "tyre" in c.lower())
                     and "temp" in c.lower()]
    longitudinal = "Vehicle Acceleration IMU Longitudinal Acceleration"
    if longitudinal not in df:
        # This spelling is used in the current MoTeC export.
        longitudinal = "Vehicle Acceleration IMU Longitudonal Acceleration"
    graphs = [
        ("tire_temperatures.png", "Tire Temperatures vs Time",
         tire_channels or ["Tire Temperature"], False),
        ("lateral_gforce.png", "Lateral G-force vs Time",
         ["Vehicle Acceleration IMU Lateral Acceleration"], False),
        ("longitudinal_gforce.png", "Longitudinal G-force vs Time",
         [longitudinal], False),
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

    message = f"Chassis Report for {df.attrs.get('log_date', 'Unknown date')}"
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
    print(f"Chassis report uploaded to Slack.")
