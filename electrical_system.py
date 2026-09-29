"""Build electrical system summaries and graphs and send them to Slack."""

from io import BytesIO

import matplotlib.pyplot as plt


def electrical_report_messages(df):
    """Summarize recorded fault transitions and numeric diagnostic codes."""
    faults = df["ETC Fault"].dropna()
    if faults.empty:
        fault_count = "No data"
    else:
        fault_count = str(int((faults.ne(0) & faults.shift().eq(0)).sum()))

    codes = df["Gear Shift Diagnostic"].dropna().unique()
    diagnostics = ", ".join(f"{code:g}" for code in codes)
    return [
        f"Electrical System Vitals for {df.attrs.get('log_date', 'Unknown date')}",
        f"ETC Faults: {fault_count}",
        (
            f"Gear Shift Diagnostic: codes {diagnostics}"
            if diagnostics
            else "Gear Shift Diagnostic: No data"
        ),
    ]


def create_ecu_battery_voltage_graph(df):
    """Render the voltage graph in memory for Slack upload."""
    fig, ax = plt.subplots(figsize=(12, 6))
    try:
        ax.plot(df["Time"], df["ECU Battery Voltage"])
        ax.set_title("ECU Battery Voltage vs Time")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("ECU Battery Voltage (V)")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        image = BytesIO()
        fig.savefig(image, format="png")
        image.seek(0)
        return image
    finally:
        plt.close(fig)


def send_electrical_report(df, client, channel):
    """Send electrical summaries and the voltage graph to a Slack channel."""
    messages = electrical_report_messages(df)
    with create_ecu_battery_voltage_graph(df) as image:
        for message in messages:
            client.chat_postMessage(channel=channel, text=message)
        client.files_upload_v2(
            channel=channel,
            file=image,
            filename="ecu_battery_voltage.png",
            title="ECU Battery Voltage vs Time",
        )
    print("Electrical system report uploaded to Slack.")
