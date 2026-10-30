"""DC telemetry reports."""

from report_graphs import create_graph, send_graph, send_report_message


def send_dc_report(df, client, channel):
    """Send the dc summary and all available graphs."""
    graphs = [
        ('brake_pressure_front.png', 'Brake Pressure Front vs Time',
         ['Brake Pressure Front'], False),
        ('brake_pressure_rear.png', 'Brake Pressure Rear vs Time',
         ['Brake Pressure Rear'], False),
        ('brake_temperature_front.png', 'Brake Temperature Front vs Time',
         ['Brake Temperature Front'], False),
        ('brake_temperature_rear.png', 'Brake Temperature Rear vs Time',
         ['Brake Temperature Rear'], False),
    ]
    columns = [column for _, _, channels, _ in graphs for column in channels]
    send_report_message(df, client, channel, 'DC', columns)
    for filename, title, columns, step in graphs:
        image = create_graph(df, title, columns, step=step)
        send_graph(image, client, channel, filename, title)
    print("DC report uploaded to Slack.")
