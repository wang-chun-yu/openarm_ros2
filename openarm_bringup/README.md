# OpenArm Bringup - 启动和配置包

**功能：** OpenArm 机械臂的启动配置和控制器管理

---

## 📋 概述

`openarm_bringup` 包提供启动 OpenArm 机械臂所需的 Launch 文件和控制器配置，是使用 OpenArm ROS2 系统的入口。

**主要功能：**
- 启动 robot_state_publisher（发布 URDF 和 TF）
- 启动 ros2_control_node（硬件接口管理）
- 加载和启动控制器
- 配置 RViz 可视化

---

## 📁 文件结构

```
openarm_bringup/
├── launch/                         # Launch 文件
│   ├── openarm.launch.py           # 单臂启动
│   └── openarm.bimanual.launch.py  # 双臂启动
│
├── config/                         # 控制器配置
│   └── v10_controllers/
│       ├── openarm_v10_controllers.yaml          # 单臂控制器
│       ├── openarm_v10_bimanual_controllers.yaml # 双臂控制器
│       └── openarm_v10_bimanual_controllers_namespaced.yaml  # 带命名空间的双臂
│
└── rviz/                           # RViz 配置
    └── bimanual.rviz               # 双臂可视化配置
```

---

## 🚀 Launch 文件

### openarm.launch.py

**功能：** 启动单臂 OpenArm 机器人

**参数列表：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `arm_type` | string | `v10` | 机械臂型号 |
| `description_package` | string | `openarm_description` | URDF 描述包名称 |
| `description_file` | string | `v10.urdf.xacro` | URDF 文件名 |
| `use_fake_hardware` | bool | `false` | 是否使用仿真硬件 |
| `can_interface` | string | `can0` | CAN 接口名称 |
| `controllers_file` | string | `openarm_v10_controllers.yaml` | 控制器配置文件 |
| `launch_rviz` | bool | `false` | 是否启动 RViz |
| `arm_prefix` | string | `''` | 命名空间前缀 |

**使用示例：**

```bash
# 仿真模式 + RViz
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true

# 真实硬件模式
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    can_interface:=can0

# 使用命名空间（多机器人）
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    arm_prefix:=/robot1 \
    use_fake_hardware:=true
```

**启动的节点：**
1. `robot_state_publisher`：发布 URDF 和 TF
2. `ros2_control_node`：硬件接口管理
3. `joint_state_broadcaster`：发布关节状态
4. `joint_trajectory_controller`：轨迹跟踪控制器
5. `rviz2`（可选）：可视化

---

### openarm.bimanual.launch.py

**功能：** 启动双臂 OpenArm 机器人（包含机身基座）

**参数列表：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `arm_type` | string | `v10` | 机械臂型号 |
| `description_package` | string | `openarm_description` | URDF 描述包 |
| `description_file` | string | `v10.urdf.xacro` | URDF 文件名 |
| `use_fake_hardware` | bool | `false` | 是否使用仿真硬件 |
| `left_can_interface` | string | `can1` | 左臂 CAN 接口 |
| `right_can_interface` | string | `can0` | 右臂 CAN 接口 |
| `controllers_file` | string | `openarm_v10_bimanual_controllers.yaml` | 控制器配置 |
| `launch_rviz` | bool | `false` | 是否启动 RViz |
| `arm_prefix` | string | `''` | 命名空间前缀 |

**使用示例：**

```bash
# 仿真模式
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true

# 真实硬件模式
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    left_can_interface:=can1 \
    right_can_interface:=can0

# CAN-FD 模式
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    left_can_interface:=can1 \
    right_can_interface:=can0 \
    can_fd:=true
```

**启动的节点：**
1. `robot_state_publisher`：发布双臂 URDF
2. `ros2_control_node`：管理左右臂硬件接口
3. `joint_state_broadcaster`：发布双臂关节状态
4. `left_arm_joint_trajectory_controller`：左臂轨迹控制器
5. `right_arm_joint_trajectory_controller`：右臂轨迹控制器
6. `rviz2`（可选）：双臂可视化

---

## ⚙️ 控制器配置

### openarm_v10_controllers.yaml

**功能：** 单臂控制器配置

**包含的控制器：**

#### 1. joint_state_broadcaster
**类型：** `joint_state_broadcaster/JointStateBroadcaster`

**功能：** 发布关节状态到 `/joint_states` 话题

**自动启动：** 是

---

#### 2. joint_trajectory_controller
**类型：** `joint_trajectory_controller/JointTrajectoryController`

**功能：** 轨迹跟踪控制器，用于执行规划的轨迹

**控制接口：**
- 命令：position
- 状态：position

**参数：**
```yaml
joints:
  - openarm_joint1
  - openarm_joint2
  - openarm_joint3
  - openarm_joint4
  - openarm_joint5
  - openarm_joint6
  - openarm_joint7

state_publish_rate: 50.0         # 状态发布频率 [Hz]
action_monitor_rate: 50.0        # 动作监控频率 [Hz]
allow_partial_joints_goal: false # 是否允许部分关节目标
```

**使用：**
```bash
# 查看控制器状态
ros2 control list_controllers

# 发送轨迹命令
ros2 action send_goal /joint_trajectory_controller/follow_joint_trajectory \
    control_msgs/action/FollowJointTrajectory "..."
```

---

#### 3. forward_position_controller
**类型：** `forward_command_controller/ForwardCommandController`

**功能：** 直接位置控制（无轨迹插值）

**控制接口：**
- 命令：position
- 状态：position

**使用场景：** 简单的关节位置控制

---

#### 4. forward_velocity_controller
**类型：** `forward_command_controller/ForwardCommandController`

**功能：** 速度控制

**控制接口：**
- 命令：velocity
- 状态：velocity

**使用场景：** 恒速运动控制

---

#### 5. gripper_controller
**类型：** `position_controllers/GripperActionController`

**功能：** 夹爪位置控制

**控制关节：** `openarm_finger_joint1`

**使用：**
```bash
ros2 action send_goal /gripper_controller/gripper_cmd \
    control_msgs/action/GripperCommand "{command: {position: 0.02, max_effort: 5.0}}"
```

---

### openarm_v10_bimanual_controllers.yaml

**功能：** 双臂控制器配置

**差异：**
- 为左右臂分别创建控制器
- 控制器名称带前缀：`left_arm_*` 和 `right_arm_*`
- 独立的关节列表

**示例：**
```yaml
left_arm_joint_trajectory_controller:
  ros__parameters:
    joints:
      - openarm_left_joint1
      - openarm_left_joint2
      - ...

right_arm_joint_trajectory_controller:
  ros__parameters:
    joints:
      - openarm_right_joint1
      - openarm_right_joint2
      - ...
```

---

## 🎮 控制器管理

### 查看控制器

```bash
# 列出所有控制器及状态
ros2 control list_controllers

# 输出示例：
# joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
# joint_trajectory_controller[joint_trajectory_controller/JointTrajectoryController] active
```

### 切换控制器

```bash
# 停止轨迹控制器
ros2 control set_controller_state joint_trajectory_controller stop

# 启动速度控制器
ros2 control set_controller_state forward_velocity_controller start
```

### 加载新控制器

```bash
# 加载控制器（从配置文件）
ros2 control load_controller my_custom_controller

# 配置控制器
ros2 control set_controller_state my_custom_controller configure

# 启动控制器
ros2 control set_controller_state my_custom_controller start
```

---

## 🔍 调试和监控

### 查看硬件接口

```bash
# 列出硬件组件
ros2 control list_hardware_components

# 输出示例：
# openarm_hardware_interface[system] active
```

### 查看命令/状态接口

```bash
# 列出所有接口
ros2 control list_hardware_interfaces

# 输出示例：
# command interfaces:
#   openarm_joint1/position [available] [claimed]
#   openarm_joint1/velocity [available] [unclaimed]
# state interfaces:
#   openarm_joint1/position [available]
#   openarm_joint1/velocity [available]
```

### 监控话题

```bash
# 查看关节状态
ros2 topic echo /joint_states

# 查看控制器命令（调试用）
ros2 topic echo /joint_trajectory_controller/joint_trajectory

# 查看 TF
ros2 run tf2_ros tf2_echo world openarm_link7
```

---

## 🛠️ 自定义配置

### 修改控制频率

编辑控制器配置文件：

```yaml
controller_manager:
  ros__parameters:
    update_rate: 500  # 改为 500 Hz（需要实时内核支持）
```

### 添加自定义控制器

1. 在配置文件中添加控制器定义：

```yaml
my_custom_controller:
  ros__parameters:
    type: my_controller_type
    joints: [...]
    # 其他参数
```

2. 在 Launch 文件中 spawn 控制器：

```python
Node(
    package="controller_manager",
    executable="spawner",
    arguments=["my_custom_controller"],
    output="screen",
)
```

---

## ⚠️ 注意事项

1. **控制器互斥**：同一时刻只能有一个控制器 claim 一个关节的命令接口
2. **启动顺序**：`joint_state_broadcaster` 必须先启动
3. **CAN 接口**：真实硬件模式需正确配置 CAN 接口
4. **实时性**：高频控制需要实时内核支持

---

## 📚 相关文档

- [架构设计文档](../doc/ARCHITECTURE.md)
- [快速开始指南](../doc/QUICK_START.md)
- [OpenArm Hardware](../openarm_hardware/README.md)

---

**维护：** 添加新控制器或修改配置时请更新本文档。
