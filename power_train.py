"""Powertrain telemetry reports."""

from report_graphs import create_graph, send_graph, send_report_message


def send_power_train_report(df, client, channel):
    """Send the powertrain summary and all available graphs."""
    graphs = [
        ('coolant_temperatures.png', 'Coolant Temperatures vs Time',
         ['Coolant Temperature', 'Coolant Post Rad Temperature'], False),
        ('oil_temperature.png', 'Engine Oil Temperature vs Time',
         ['Oil Temperature' if 'Oil Temperature' in df else 'Engine Oil Temperature'], False),
        ('engine_rpm.png', 'Engine RPM vs Time',
         ['Engine Speed'], False),
        ('gear_shifts.png', 'Gear Position / Shifts vs Time',
         ['Gear'], True),
        ('fuel_pressure.png', 'Fuel Pressure vs Time',
         ['Fuel Pressure'], False),
        ('oil_pressure.png', 'Engine Oil Pressure vs Time',
         ['Engine Oil Pressure'], False),
    ]
    columns = [column for _, _, channels, _ in graphs for column in channels]
    send_report_message(df, client, channel, 'Powertrain', columns)
    for filename, title, columns, step in graphs:
        image = create_graph(df, title, columns, step=step)
        send_graph(image, client, channel, filename, title)
    print("Powertrain report uploaded to Slack.")
