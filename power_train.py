"""Powertrain telemetry reports."""

from io import BytesIO

import matplotlib.pyplot as plt


def send_power_train_report(df, client, channel):
    """Send temperatures, RPM, gear shifts, fuel pressure, and oil pressure."""
    graphs = [
        ("coolant_temperatures.png", "Coolant Temperatures vs Time",
         ["Coolant Temperature", "Coolant Post Rad Temperature"], False),
        ("oil_temperature.png", "Engine Oil Temperature vs Time",
         ["Engine Oil Temperature"], False),
        ("engine_rpm.png", "Engine RPM vs Time", ["Engine Speed"], False),
        ("gear_shifts.png", "Gear Position / Shifts vs Time", ["Gear"], True),
        ("fuel_pressure.png", "Fuel Pressure vs Time", ["Fuel Pressure"], False),
        ("oil_pressure.png", "Engine Oil Pressure vs Time",
         ["Engine Oil Pressure"], False),
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

    message = f"Powertrain Report for {df.attrs.get('log_date', 'Unknown date')}"
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
    print(f"Powertrain report uploaded to Slack.")
