import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro
from os.path import join


def generate_launch_description():

    # Package Directories
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    pkg_ros_gz_rbot = get_package_share_directory('base_link_description')

    # Parse robot description from xacro. use_mock_hardware:=false selects the
    # Gazebo DiffDrive plugin (defined in base_link.gazebo) instead of mock
    # ros2_control hardware.
    robot_description_file = os.path.join(pkg_ros_gz_rbot, 'urdf', 'base_link.xacro')
    ros_gz_bridge_config = os.path.join(pkg_ros_gz_rbot, 'config', 'ros_gz_bridge_gazebo.yaml')
    rviz_config = os.path.join(pkg_ros_gz_rbot, 'config', 'gazebo.rviz')

    robot_description_config = xacro.process_file(
        robot_description_file,
        mappings={'use_mock_hardware': 'false'},
    )
    robot_description = {
        'robot_description': robot_description_config.toxml(),
        'use_sim_time': True,
    }

    gui_arg = DeclareLaunchArgument('rviz', default_value='true',
                                    description='Open RViz.')
    teleop_arg = DeclareLaunchArgument('teleop', default_value='true',
                                       description='Open a keyboard teleop terminal to drive the tank.')

    # Start Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )

    # Start Gazebo Sim
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")),
        launch_arguments={
            "gz_args": '-r -v 4 empty.sdf'
        }.items()
    )

    # Spawn Robot in Gazebo
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            "-topic", "/robot_description",
            "-name", "base_link",
            "-allow_renaming", "true",
            "-z", "0.32",
            "-x", "0.0",
            "-y", "0.0",
            "-Y", "0.0"
        ],
        output='screen',
    )

    # Bridge ROS topics and Gazebo messages (cmd_vel, odom, tf, joint_states, clock)
    start_gazebo_ros_bridge_cmd = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': ros_gz_bridge_config,
            'use_sim_time': True,
        }],
        output='screen'
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    # Keyboard teleop, opened in its own terminal window so it can read keys.
    # Publishes geometry_msgs/Twist on /cmd_vel. Only linear.x + angular.z are
    # sent by the normal (lowercase) keys -> the tank drives/turns but never
    # strafes sideways. Press 'k' to stop.
    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        prefix='gnome-terminal --',
        output='screen',
        condition=IfCondition(LaunchConfiguration('teleop')),
    )

    return LaunchDescription(
        [
            gui_arg,
            teleop_arg,
            gazebo,
            spawn,
            start_gazebo_ros_bridge_cmd,
            robot_state_publisher,
            rviz,
            teleop,
        ]
    )
