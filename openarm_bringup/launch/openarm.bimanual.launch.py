# Copyright 2025 Enactic, Inc.
# Copyright 2024 Stogl Robotics Consulting UG (haftungsbeschränkt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
文件名：openarm.bimanual.launch.py
功能：启动双臂 OpenArm 机器人系统
版本：1.0
日期：2026-02-09

描述：
本 Launch 文件用于启动包含机身基座和左右两个机械臂的完整双臂系统。
它会启动以下核心组件：
1. robot_state_publisher：发布双臂机器人的 URDF 描述和 TF 变换
2. ros2_control_node：管理左右臂的硬件接口（独立的 CAN 总线）
3. joint_state_broadcaster：发布所有关节的状态信息
4. 左右臂的轨迹控制器：用于独立控制每个机械臂
5. rviz2：可视化工具（可选）

主要功能：
- 支持真实硬件和仿真模式切换
- 独立配置左右臂的 CAN 接口
- 支持命名空间（多机器人场景）
- 延迟启动控制器确保硬件就绪
- 集成 RViz 可视化

使用示例：
# 仿真模式
ros2 launch openarm_bringup openarm.bimanual.launch.py \\
    arm_type:=v10 use_fake_hardware:=true launch_rviz:=true

# 真实硬件
ros2 launch openarm_bringup openarm.bimanual.launch.py \\
    arm_type:=v10 use_fake_hardware:=false \\
    left_can_interface:=can1 right_can_interface:=can0

参数：
- arm_type：机械臂型号（必需）
- use_fake_hardware：是否使用仿真硬件（默认 false）
- left_can_interface：左臂 CAN 接口（默认 can1）
- right_can_interface：右臂 CAN 接口（默认 can0）
- launch_rviz：是否启动 RViz（默认 false）
- arm_prefix：命名空间前缀（默认为空）
"""

import os
import xacro

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription, LaunchContext
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, TimerAction, OpaqueFunction
from launch.event_handlers import OnProcessExit
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder

def namespace_from_context(context, arm_prefix):
    """
    从 arm_prefix 提取命名空间
    
    功能：
    处理 arm_prefix 参数，提取命名空间字符串。
    如果 arm_prefix 为空，返回 None（不使用命名空间）。
    
    参数：
        context: Launch 上下文
        arm_prefix: arm_prefix LaunchConfiguration 对象
        
    返回：
        str 或 None: 命名空间字符串（去除前后斜杠）
    """
    arm_prefix_str = context.perform_substitution(arm_prefix)
    if arm_prefix_str:
        return arm_prefix_str.strip('/')
    return None


def generate_robot_description(context: LaunchContext, description_package, description_file,
                               arm_type, use_fake_hardware, right_can_interface, left_can_interface):
    """
    生成机器人 URDF 描述
    
    功能：
    使用 xacro 处理模板文件，生成双臂机器人的完整 URDF 描述。
    该函数会根据参数动态配置机器人模型，包括硬件模式、CAN 接口等。
    
    参数：
        context: Launch 上下文对象
        description_package: URDF 描述包名称
        description_file: Xacro 文件名
        arm_type: 机械臂型号（如 v10）
        use_fake_hardware: 是否使用仿真硬件
        right_can_interface: 右臂 CAN 接口名
        left_can_interface: 左臂 CAN 接口名
        
    返回：
        str: 处理后的 URDF XML 字符串
    """

    # 解析所有 LaunchConfiguration 参数为字符串
    description_package_str = context.perform_substitution(description_package)
    description_file_str = context.perform_substitution(description_file)
    arm_type_str = context.perform_substitution(arm_type)
    use_fake_hardware_str = context.perform_substitution(use_fake_hardware)
    right_can_interface_str = context.perform_substitution(right_can_interface)
    left_can_interface_str = context.perform_substitution(left_can_interface)

    # 构建 Xacro 文件的完整路径
    xacro_path = os.path.join(
        get_package_share_directory(description_package_str),
        "urdf", "robot", description_file_str
    )

    # 使用 xacro 处理模板文件，生成最终 URDF
    # mappings 字典将参数传递给 xacro 宏：
    # - arm_type: 机械臂型号
    # - bimanual: 设置为 true 启用双臂模式
    # - use_fake_hardware: 选择真实硬件或仿真
    # - ros2_control: 启用 ROS2 Control 硬件接口
    # - left/right_can_interface: 左右臂的独立 CAN 接口
    robot_description = xacro.process_file(
        xacro_path,
        mappings={
            "arm_type": arm_type_str,
            "bimanual": "true",  # 强制双臂模式
            "use_fake_hardware": use_fake_hardware_str,
            "ros2_control": "true",  # 必须启用 ros2_control
            "right_can_interface": right_can_interface_str,
            "left_can_interface": left_can_interface_str,
        }
    ).toprettyxml(indent="  ")

    return robot_description


def robot_nodes_spawner(context: LaunchContext, description_package, description_file,
                        arm_type, use_fake_hardware, controllers_file, right_can_interface, left_can_interface, arm_prefix):
    """
    生成机器人核心节点
    
    功能：
    创建并配置以下核心节点：
    1. robot_state_publisher：发布机器人描述和 TF 变换
    2. ros2_control_node：管理硬件接口和控制器
    
    这两个节点共享同一个 robot_description 参数，确保描述一致性。
    
    参数：
        context: Launch 上下文
        description_package: URDF 描述包名
        description_file: Xacro 文件名
        arm_type: 机械臂型号
        use_fake_hardware: 是否仿真
        controllers_file: 控制器配置文件路径
        right_can_interface: 右臂 CAN 接口
        left_can_interface: 左臂 CAN 接口
        arm_prefix: 命名空间前缀
        
    返回：
        List[Node]: 包含 robot_state_publisher 和 ros2_control_node 的列表
    """
    # 提取命名空间（如果使用）
    namespace = namespace_from_context(context, arm_prefix)

    # 生成双臂机器人的 URDF 描述
    robot_description = generate_robot_description(
        context, description_package, description_file, arm_type, use_fake_hardware, right_can_interface, left_can_interface,
    )

    # 解析控制器配置文件路径
    controllers_file_str = context.perform_substitution(controllers_file)
    robot_description_param = {"robot_description": robot_description}

    # 如果使用命名空间，切换到带命名空间的控制器配置
    # 带命名空间的配置会在话题名称中添加前缀
    if namespace:
        controllers_file_str = controllers_file_str.replace(
            "openarm_v10_bimanual_controllers.yaml", "openarm_v10_bimanual_controllers_namespaced.yaml"
        )
    
    # ==================== Robot State Publisher 节点 ====================
    # 功能：
    # 1. 解析 URDF 并发布到 /robot_description 话题
    # 2. 订阅 /joint_states 话题
    # 3. 计算并发布所有链接的 TF 变换到 /tf 和 /tf_static
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        namespace=namespace,
        parameters=[robot_description_param],
    )

    # ==================== ROS2 Control 节点 ====================
    # 功能：
    # 1. 加载硬件接口（OpenArmV10SimpleHardware）
    # 2. 管理所有控制器的生命周期
    # 3. 协调命令接口和状态接口
    # 4. 以 500Hz 频率调用 read() 和 write()
    # 
    # 参数：
    # - robot_description: 包含 <ros2_control> 标签的 URDF
    # - controllers_file: 控制器配置（类型、参数等）
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="both",  # stdout 和 stderr 都输出
        namespace=namespace,
        parameters=[robot_description_param, controllers_file_str],
    )

    return [robot_state_pub_node, control_node]


def controller_spawner(context: LaunchContext, robot_controller, arm_prefix):
    """
    生成控制器加载节点
    
    功能：
    为双臂系统创建控制器 spawner 节点。根据控制器类型，
    自动为左右臂创建对应的控制器实例。
    
    支持的控制器：
    - forward_position_controller: 直接位置控制
    - joint_trajectory_controller: 轨迹跟踪控制
    
    参数：
        context: Launch 上下文
        robot_controller: 控制器基础名称
        arm_prefix: 命名空间前缀
        
    返回：
        List[Node]: 包含控制器 spawner 节点的列表
    """
    # 提取命名空间
    namespace = namespace_from_context(context, arm_prefix)

    # 构建 controller_manager 引用路径
    # 带命名空间时需要完整路径，否则使用默认路径
    controller_manager_ref = f"/{namespace}/controller_manager" if namespace else "/controller_manager"

    # 解析控制器类型
    robot_controller_str = context.perform_substitution(robot_controller)

    # 根据控制器基础名称，生成左右臂的控制器名称
    # 左臂控制器带 left_ 前缀，右臂控制器带 right_ 前缀
    if robot_controller_str == "forward_position_controller":
        robot_controller_left = "left_forward_position_controller"
        robot_controller_right = "right_forward_position_controller"
    elif robot_controller_str == "joint_trajectory_controller":
        robot_controller_left = "left_joint_trajectory_controller"
        robot_controller_right = "right_joint_trajectory_controller"
    else:
        raise ValueError(f"Unknown robot_controller: {robot_controller_str}")

    # 创建 spawner 节点
    # spawner 是 controller_manager 的工具，用于加载和激活控制器
    # 参数说明：
    # - robot_controller_left/right: 要加载的控制器名称
    # - -c controller_manager_ref: 指定 controller_manager 的路径
    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        namespace=namespace,
        arguments=[robot_controller_left,
                   robot_controller_right, "-c", controller_manager_ref],
    )

    return [robot_controller_spawner]


def generate_launch_description():
    """
    生成双臂 OpenArm 的完整 Launch 描述
    
    功能：
    配置并启动双臂 OpenArm 机器人所需的所有节点和参数。
    包括机器人描述发布、硬件接口管理、控制器启动和可视化。
    
    启动顺序：
    1. 声明所有 Launch 参数
    2. 启动 robot_state_publisher 和 ros2_control_node
    3. 启动 joint_state_broadcaster（立即）
    4. 延迟 2 秒后启动主控制器（等待硬件初始化）
    5. 启动 RViz（可选）
    
    返回：
        LaunchDescription: 完整的 Launch 描述对象
    """

    # ==================== Launch 参数声明 ====================
    # 定义所有可配置参数及其默认值和说明
    
    declared_arguments = [
        # URDF 描述包名称
        # 默认使用 openarm_description 包
        DeclareLaunchArgument(
            "description_package",
            default_value="openarm_description",
            description="Description package with robot URDF/xacro files.",
        ),
        
        # URDF 文件名
        # 对应 openarm_description/urdf/robot/ 下的文件
        DeclareLaunchArgument(
            "description_file",
            default_value="v10.urdf.xacro",
            description="URDF/XACRO description file with the robot.",
        ),
        
        # 机械臂型号
        # 决定加载哪个版本的配置文件
        DeclareLaunchArgument(
            "arm_type",
            default_value="v10",
            description="Type of arm (e.g., v10).",
        ),
        
        # 是否使用仿真硬件
        # true: 使用 mock_components/GenericSystem（仿真）
        # false: 使用 openarm_hardware（真实硬件）
        DeclareLaunchArgument(
            "use_fake_hardware",
            default_value="false",
            description="Use fake hardware instead of real hardware.",
        ),
        # 主控制器类型选择
        # forward_position_controller: 直接位置控制（无轨迹插值）
        # joint_trajectory_controller: 轨迹跟踪控制器（推荐，与 MoveIt 兼容）
        DeclareLaunchArgument(
            "robot_controller",
            default_value="joint_trajectory_controller",
            choices=["forward_position_controller",
                     "joint_trajectory_controller"],
            description="Robot controller to start.",
        ),
        
        # 控制器配置文件所在包
        # 通常使用 openarm_bringup 包的 config 目录
        DeclareLaunchArgument(
            "runtime_config_package",
            default_value="openarm_bringup",
            description="Package with the controller's configuration in config folder.",
        ),
        
        # 命名空间前缀
        # 用于多机器人场景，避免话题和服务名称冲突
        # 例如：arm_prefix:=/robot1 会将所有话题加上 /robot1 前缀
        DeclareLaunchArgument(
            "arm_prefix",
            default_value="",
            description="Prefix for the arm for topic namespacing.",
        ),
        
        # 右臂 CAN 接口
        # 通常为 can0，需确保已配置并启用
        # 命令：sudo ip link set can0 type can bitrate 1000000 && sudo ip link set up can0
        DeclareLaunchArgument(
            "right_can_interface",
            default_value="can0",
            description="CAN interface to use for the right arm.",
        ),
        
        # 左臂 CAN 接口
        # 通常为 can1，需独立于右臂接口
        # 命令：sudo ip link set can1 type can bitrate 1000000 && sudo ip link set up can1
        DeclareLaunchArgument(
            "left_can_interface",
            default_value="can1",
            description="CAN interface to use for the left arm.",
        ),
        
        # 控制器配置文件名
        # 默认：openarm_v10_bimanual_controllers.yaml（双臂标准配置）
        # 带命名空间：openarm_v10_bimanual_controllers_namespaced.yaml（自动选择）
        DeclareLaunchArgument(
            "controllers_file",
            default_value="openarm_v10_bimanual_controllers.yaml",
            description="Controllers file(s) to use. Can be a single file or comma-separated list of files.",
        ),
    ]

    # ==================== 初始化 LaunchConfiguration ====================
    # 从命令行参数或默认值中获取配置
    
    description_package = LaunchConfiguration("description_package")
    description_file = LaunchConfiguration("description_file")
    arm_type = LaunchConfiguration("arm_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    robot_controller = LaunchConfiguration("robot_controller")
    runtime_config_package = LaunchConfiguration("runtime_config_package")
    controllers_file = LaunchConfiguration("controllers_file")
    rightcan_interface = LaunchConfiguration("right_can_interface")
    left_can_interface = LaunchConfiguration("left_can_interface")
    arm_prefix = LaunchConfiguration("arm_prefix")

    # 构建控制器配置文件的完整路径
    # 示例：<runtime_config_package>/config/v10_controllers/<controllers_file>
    controllers_file = PathJoinSubstitution(
        [FindPackageShare(runtime_config_package), "config",
         "v10_controllers", controllers_file]
    )

    # ==================== 机器人节点生成器 ====================
    # 使用 OpaqueFunction 包装 robot_nodes_spawner 函数
    # 这样可以在运行时动态解析 LaunchConfiguration 参数
    robot_nodes_spawner_func = OpaqueFunction(
        function=robot_nodes_spawner,
        args=[description_package, description_file, arm_type,
              use_fake_hardware, controllers_file, rightcan_interface, left_can_interface, arm_prefix]
    )

    moveit_config = (
        MoveItConfigsBuilder(
            "openarm", package_name="openarm_bimanual_moveit_config"
        )
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True       
        )
        .to_moveit_configs()
    )

    moveit_params = moveit_config.to_dict()

    run_move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_params],
    )

    # ==================== RViz 配置和节点 ====================
    # RViz 配置文件路径
    # 使用双臂专用的 rviz 配置，包含左右臂的显示设置
    # rviz_config_file = os.path.join(
    #     get_package_share_directory(
    #         "openarm_bimanual_moveit_config"), "config", "moveit.rviz"
    # )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare(description_package), "rviz",
         "bimanual.rviz"]
    )

    # RViz2 节点
    # 功能：
    # 1. 3D 可视化机器人模型
    # 2. 显示 TF 坐标系
    # 3. 显示传感器数据（如果有）
    # 4. 提供 MoveIt 交互式规划界面（如果启用）
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",  # 输出到日志文件，减少终端干扰
        arguments=["-d", rviz_config_file],
        parameters=[moveit_params],
    )

    # ==================== 控制器加载和启动 ====================
    
    # Joint State Broadcaster Spawner
    # 功能：加载和启动 joint_state_broadcaster
    # 该控制器负责发布所有关节的状态到 /joint_states 话题
    # 必须最先启动，因为其他节点（如 robot_state_publisher）依赖它
    joint_state_broadcaster_spawner = OpaqueFunction(
        function=lambda context: [Node(
            package="controller_manager",
            executable="spawner",
            namespace=namespace_from_context(context, arm_prefix),
            arguments=["joint_state_broadcaster",
                       "--controller-manager",
                       f"/{namespace_from_context(context, arm_prefix)}/controller_manager" if namespace_from_context(context, arm_prefix) else "/controller_manager"],
        )]
    )

    # 主控制器 Spawner（左右臂轨迹/位置控制器）
    # 根据 robot_controller 参数选择控制器类型
    # 通过 controller_spawner 函数自动创建左右臂控制器
    controller_spawner_func = OpaqueFunction(
        function=controller_spawner,
        args=[robot_controller, arm_prefix]
    )

    # 夹爪控制器 Spawner
    # 功能：加载左右臂的夹爪控制器
    # 夹爪独立于机械臂关节，使用单独的控制器
    gripper_controller_spawner = OpaqueFunction(
        function=lambda context: [Node(
            package="controller_manager",
            executable="spawner",
            namespace=namespace_from_context(context, arm_prefix),
            arguments=["left_gripper_controller",
                       "right_gripper_controller", "-c",
                       f"/{namespace_from_context(context, arm_prefix)}/controller_manager" if namespace_from_context(context, arm_prefix) else "/controller_manager"],
        )]
    )

    # ==================== 启动时序控制 ====================
    # 为什么需要延迟启动？
    # 1. 硬件接口需要初始化时间（CAN 通信建立、电机使能等）
    # 2. ros2_control_node 需要完全启动后才能接受控制器请求
    # 3. 避免控制器启动失败或发送无效命令
    
    LAUNCH_DELAY_SECONDS = 1.0  # 延迟 1 秒
    
    # 延迟启动 Joint State Broadcaster
    # 虽然延迟较短，但确保 ros2_control_node 已就绪
    delayed_joint_state_broadcaster = TimerAction(
        period=LAUNCH_DELAY_SECONDS,
        actions=[joint_state_broadcaster_spawner],
    )

    # 延迟启动主控制器
    # 在 Joint State Broadcaster 之后启动
    delayed_robot_controller = TimerAction(
        period=LAUNCH_DELAY_SECONDS,
        actions=[controller_spawner_func],
    )
    
    # 延迟启动夹爪控制器
    delayed_gripper_controller = TimerAction(
        period=LAUNCH_DELAY_SECONDS,
        actions=[gripper_controller_spawner],
    )

    # ==================== 返回 Launch 描述 ====================
    # 组合所有 Launch 元素并返回
    # 执行顺序：
    # 1. 参数声明（declared_arguments）
    # 2. 机器人节点（robot_nodes_spawner_func）
    # 3. RViz 节点（rviz_node，立即启动）
    # 4. 延迟 1 秒后启动所有控制器
    return LaunchDescription(
        declared_arguments + [
            robot_nodes_spawner_func,
        ] +
        [
            delayed_joint_state_broadcaster,
            delayed_robot_controller,
            delayed_gripper_controller,
            run_move_group_node,
            rviz_node,
        ]
    )
