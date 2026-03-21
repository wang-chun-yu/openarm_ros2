from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder(
        "openarm", package_name="openarm_bimanual_moveit_config"
    ).to_moveit_configs()

    hello_moveit_node = Node(
        package="openarm_demo",
        executable="hello_moveit",
        output="screen",
        parameters=[moveit_config.to_dict()],
    )

    return LaunchDescription([hello_moveit_node])
