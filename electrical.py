"""Build electrical system summaries and graphs and send them to Slack."""

from report_graphs import create_graph, send_graph

GEAR_SHIFT_DIAGNOSTICS = {
    -13: "Input Hardware Failure",
    -12: "Minimum Gear",
    -11: "Maximum Gear",
    -10: "Engine Speed Above Threshold",
    -9: "Engine Speed Below Minimum",
    -8: "Debounce Lockout",
    -7: "Shift Engine Speed Above Limit",
    -6: "Shift Failed",
    -5: "Shift Requested Result Unknown",
    -4: "No Manual Request Allowed",
    -3: "Default Gear",
    -2: "Reverse Lockout",
    -1: "Clutch Not Disengaged",
    0: "Not in Use",
    1: "OK",
}


def electrical_report_messages(df):
    """Summarize recorded fault transitions and diagnostic meanings."""
    faults = df["ETC Fault"].dropna()
    if faults.empty:
        fault_count = "No data"
    else:
        fault_count = str(int((faults.ne(0) & faults.shift().eq(0)).sum()))

    codes = df["Gear Shift Diagnostic"].dropna().unique()
    diagnostics = ", ".join(
        f"{GEAR_SHIFT_DIAGNOSTICS.get(code, 'Unknown diagnostic')} ({code:g})"
        for code in codes
    )
    return [
        f"Electrical Report for {df.attrs.get('log_date', 'Unknown date')}",
        f"ETC Faults: {fault_count}",
        (
            f"Gear Shift Diagnostic: {diagnostics}"
            if diagnostics
            else "Gear Shift Diagnostic: No data"
        ),
    ]


def send_electrical_report(df, client, channel):
    """Send all electrical summaries and the battery voltage graph to Slack."""
    for message in electrical_report_messages(df):
        client.chat_postMessage(channel=channel, text=message)
    title = "ECU Battery Voltage vs Time"
    image = create_graph(df, title, ["ECU Battery Voltage"])
    send_graph(image, client, channel, "ecu_battery_voltage.png", title)
    print("Electrical report uploaded to Slack.")
