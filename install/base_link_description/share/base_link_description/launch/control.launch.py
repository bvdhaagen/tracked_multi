#
# Bring up the tank with FAKE (mock) ros2_control hardware.
#
# No physics, no real motors: the robot is driven via /cmd_vel and the wheels +
# odometry update in RViz. Perfect for testing the control pipeline.
#
#   ros2 launch base_link_description control.launch.py
#   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.4}}" -r 20
#
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg = 'base_link_description'
    share_dir = get_package_share_directory(pkg)

    declared_args = [
        DeclareLaunchArgument('gui', default_value='true', description='Launch RViz.'),
    ]
    gui = LaunchConfiguration('gui')

    # robot_description: plain XML string (mock hardware).
    xacro_file = os.path.join(share_dir, 'urdf', 'base_link.xacro')
    robot_description_xml = xacro.process_file(
        xacro_file, mappings={'use_mock_hardware': 'true'}
    ).toxml()
    robot_description = {'robot_description': robot_description_xml}

    controllers = os.path.join(share_dir, 'config', 'controllers.yaml')
    # gazebo.rviz has Fixed Frame: odom + RobotModel from /robot_description,
    # so the tank is seen driving across the grid.
    rviz_config = os.path.join(share_dir, 'config', 'gazebo.rviz')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )

    # Controller manager hosts the mock hardware. Remap the diff-drive's
    # command topic to the conventional /cmd_vel.
    control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_description, controllers],
        remappings=[
            ('/diff_drive_base_controller/cmd_vel_unstamped', '/cmd_vel'),
        ],
        output='both',
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
    )

    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_base_controller', '--controller-manager', '/controller_manager'],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen',
        condition=IfCondition(gui),
    )

    delay_diff_drive = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[diff_drive_spawner],
        )
    )

    return LaunchDescription(
        declared_args + [
            robot_state_publisher,
            control_node,
            joint_state_broadcaster_spawner,
            delay_diff_drive,
            rviz_node,
        ]
    )
