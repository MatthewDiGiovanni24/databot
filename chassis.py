"""Chassis telemetry reports."""

from report_graphs import create_graph, send_graph, send_report_message


def send_chassis_report(df, client, channel):
    """Send the chassis summary and all available graphs."""
    graphs = [
        ('lateral_gforce.png', 'Lateral G-force vs Time',
         ['Vehicle Acceleration IMU Lateral Acceleration'], False),
        ('longitudinal_gforce.png', 'Longitudinal G-force vs Time',
         ['Vehicle Acceleration IMU Longitudinal Acceleration' if 'Vehicle Acceleration IMU Longitudinal Acceleration' in df else 'Vehicle Acceleration IMU Longitudonal Acceleration'], False),
    ]
    columns = [column for _, _, channels, _ in graphs for column in channels]
    columns.append('Steering Angle')
    send_report_message(df, client, channel, 'Chassis', columns)
    for filename, title, columns, step in graphs:
        image = create_graph(df, title, columns, step=step)
        send_graph(image, client, channel, filename, title)
    title = 'Steering Angle vs Lateral Acceleration'
    image = create_graph(
        df, title, ['Steering Angle'],
        x_column='Vehicle Acceleration IMU Lateral Acceleration',
    )
    send_graph(image, client, channel, 'steering_angle_vs_lateral_acceleration.png', title)
    print("Chassis report uploaded to Slack.")
