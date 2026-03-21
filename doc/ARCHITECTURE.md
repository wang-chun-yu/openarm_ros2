# OpenArm ROS2 架构设计文档

**文档版本：** 1.0  
**创建日期：** 2026-02-09  
**维护者：** OpenArm 开发团队

---

## 1. 概述

`openarm_ros2` 是 OpenArm 机械臂的 ROS2 (Robot Operating System 2) 集成包，提供完整的 ROS2 生态系统支持，包括机器人状态发布、控制器管理、运动规划和可视化。

### 1.1 核心功能

- **ROS2 Control 集成**：基于 ros2_control 框架的硬件接口
- **MoveIt 运动规划**：集成 MoveIt2 进行路径规划和运动执行
- **状态发布**：实时发布机器人状态和 TF 变换
- **控制器管理**：支持多种控制器（位置、速度、力矩）
- **可视化支持**：RViz2 集成和调试工具

### 1.2 技术栈

- **ROS2 版本**：Humble Hawksbill / Iron Irwini
- **中间件**：DDS (FastDDS / CycloneDDS)
- **控制框架**：ros2_control
- **规划框架**：MoveIt2
- **通信协议**：CAN / CAN-FD

---

## 2. 包组织结构

```
openarm_ros2/
├── openarm/                        # 元包（meta package）
│   └── package.xml                 # 依赖所有子包
│
├── openarm_bringup/                # 启动和配置包
│   ├── launch/                     # Launch 文件
│   │   ├── openarm.launch.py       # 单臂启动
│   │   └── openarm.bimanual.launch.py  # 双臂启动
│   ├── config/                     # 控制器配置
│   │   └── v10_controllers/
│   │       ├── openarm_v10_controllers.yaml
│   │       └── openarm_v10_bimanual_controllers.yaml
│   └── rviz/                       # RViz 配置文件
│
├── openarm_hardware/               # 硬件接口实现
│   ├── include/
│   │   └── openarm_hardware/
│   │       └── v10_simple_hardware.hpp
│   └── src/
│       └── v10_simple_hardware.cpp
│
├── openarm_bimanual_moveit_config/ # MoveIt 配置包
│   ├── config/                     # MoveIt 配置
│   │   ├── moveit_controllers.yaml
│   │   ├── kinematics.yaml
│   │   ├── joint_limits.yaml
│   │   └── openarm_bimanual.srdf
│   └── launch/                     # MoveIt Launch 文件
│       ├── demo.launch.py
│       ├── move_group.launch.py
│       └── moveit_rviz.launch.py
│
└── doc/                            # 文档目录
    ├── ARCHITECTURE.md             # 本文档
    ├── DEVELOPMENT_GUIDE.md        # 开发指南
    └── QUICK_START.md              # 快速开始
```

---

## 3. ROS2 Control 架构

### 3.1 ROS2 Control 概述

ROS2 Control 是一个统一的机器人控制框架，提供：
- 硬件抽象层（Hardware Interface）
- 控制器管理（Controller Manager）
- 控制器插件（Controller Plugins）

### 3.2 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    ROS2 应用层                           │
│  (MoveIt, Teleop, Custom Nodes)                         │
└──────────────────┬──────────────────────────────────────┘
                   │ ROS2 话题/服务
                   ▼
┌─────────────────────────────────────────────────────────┐
│              Controller Manager                          │
│  (ros2_control_node)                                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Joint        │  │ Velocity     │  │ Effort       │ │
│  │ Trajectory   │  │ Controller   │  │ Controller   │ │
│  │ Controller   │  │              │  │              │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────────┐
          │     Hardware Interface              │
          │  (v10_simple_hardware)              │
          │                                     │
          │  • read()  - 读取硬件状态           │
          │  • write() - 写入控制命令           │
          └──────────────┬──────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────┐
          │      OpenArm CAN 通信层              │
          │  (openarm_can)                      │
          └──────────────┬──────────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────────┐
          │          硬件电机                     │
          │  (DM8009, DM4340, DM4310)           │
          └─────────────────────────────────────┘
```

### 3.3 硬件接口实现

**类：** `OpenArmV10SimpleHardware`

**继承自：** `hardware_interface::SystemInterface`

**核心方法：**

#### `on_init()`
初始化硬件接口。

**功能：**
- 解析 URDF 参数
- 初始化 CAN 接口
- 注册命令和状态接口

#### `on_activate()`
激活硬件。

**功能：**
- 打开 CAN 通信
- 使能电机
- 设置初始位置

#### `read()`
读取硬件状态（500Hz 调用）。

**功能：**
- 从 CAN 总线读取电机状态
- 更新位置、速度、力矩反馈

#### `write()`
写入控制命令（500Hz 调用）。

**功能：**
- 将控制器命令发送到电机
- 支持位置、速度、力矩控制

---

## 4. 控制器配置

### 4.1 支持的控制器类型

#### Joint Trajectory Controller
**用途：** 轨迹跟踪控制（MoveIt 使用）

**配置：**
```yaml
left_arm_joint_trajectory_controller:
  type: joint_trajectory_controller/JointTrajectoryController
  joints:
    - openarm_left_joint1
    - openarm_left_joint2
    - ...
  command_interfaces:
    - position
  state_interfaces:
    - position
    - velocity
```

#### Joint State Broadcaster
**用途：** 发布关节状态到 `/joint_states`

**配置：**
```yaml
joint_state_broadcaster:
  type: joint_state_broadcaster/JointStateBroadcaster
```

#### Velocity Controller
**用途：** 速度控制

**配置：**
```yaml
velocity_controller:
  type: velocity_controllers/JointGroupVelocityController
  joints: [...]
```

#### Effort Controller
**用途：** 力矩控制

**配置：**
```yaml
effort_controller:
  type: effort_controllers/JointGroupEffortController
  joints: [...]
```

### 4.2 控制器生命周期

```
┌──────────┐
│ Unconfigured │
└──────┬───────┘
       │ configure()
       ▼
┌──────────┐
│ Inactive │
└──────┬───────┘
       │ activate()
       ▼
┌──────────┐
│  Active  │ ← 正常工作状态
└──────┬───────┘
       │ deactivate()
       ▼
┌──────────┐
│ Inactive │
└──────────┘
```

**管理命令：**
```bash
# 列出所有控制器
ros2 control list_controllers

# 加载控制器
ros2 control load_controller <controller_name>

# 配置控制器
ros2 control set_controller_state <controller_name> configure

# 激活控制器
ros2 control set_controller_state <controller_name> start

# 停止控制器
ros2 control set_controller_state <controller_name> stop
```

---

## 5. MoveIt 集成

### 5.1 MoveIt2 概述

MoveIt2 是 ROS2 的运动规划框架，提供：
- 运动规划（OMPL, Pilz Industrial）
- 逆运动学求解
- 碰撞检测
- 轨迹执行

### 5.2 MoveIt 架构

```
┌─────────────────────────────────────────┐
│          MoveIt API / Rviz              │
│  (用户界面、Python/C++ API)              │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│         Move Group Node                 │
│  (核心规划节点)                           │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Motion       │  │ Collision    │   │
│  │ Planning     │  │ Detection    │   │
│  │ (OMPL)       │  │              │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Kinematics   │  │ Trajectory   │   │
│  │ Solver (KDL) │  │ Execution    │   │
│  └──────────────┘  └──────────────┘   │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│   Joint Trajectory Controller           │
│   (ros2_control)                        │
└─────────────────────────────────────────┘
```

### 5.3 关键配置文件

#### SRDF (Semantic Robot Description Format)
**文件：** `openarm_bimanual.srdf`

**内容：**
- 规划组（Planning Groups）
- 自碰撞禁用对
- 末端执行器定义
- 虚拟关节

**示例：**
```xml
<group name="left_arm">
  <chain base_link="openarm_body_link0" tip_link="openarm_left_link7"/>
</group>

<group name="right_arm">
  <chain base_link="openarm_body_link0" tip_link="openarm_right_link7"/>
</group>
```

#### 运动学配置
**文件：** `kinematics.yaml`

**内容：**
```yaml
left_arm:
  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin
  kinematics_solver_search_resolution: 0.005
  kinematics_solver_timeout: 0.05
```

#### 关节限位
**文件：** `joint_limits.yaml`

**内容：** 覆盖 URDF 中的限位（更保守）

---

## 6. 启动流程

### 6.1 单臂启动流程

```
openarm.launch.py
    │
    ├─→ robot_state_publisher
    │   └─ 发布 /robot_description
    │   └─ 发布 TF 变换
    │
    ├─→ ros2_control_node
    │   └─ 加载硬件接口
    │   └─ 初始化 CAN 通信
    │
    ├─→ spawn controllers
    │   └─ joint_state_broadcaster (立即启动)
    │   └─ joint_trajectory_controller (延迟启动)
    │
    └─→ rviz2 (可选)
        └─ 可视化机器人状态
```

### 6.2 双臂启动流程

```
openarm.bimanual.launch.py
    │
    ├─→ robot_state_publisher
    │   └─ 发布双臂 URDF
    │
    ├─→ ros2_control_node
    │   └─ 左臂硬件接口 (can1)
    │   └─ 右臂硬件接口 (can0)
    │
    ├─→ spawn controllers
    │   └─ joint_state_broadcaster
    │   └─ left_arm_joint_trajectory_controller
    │   └─ right_arm_joint_trajectory_controller
    │
    └─→ rviz2
```

---

## 7. 话题和服务

### 7.1 核心话题

| 话题名 | 消息类型 | 方向 | 说明 |
|--------|----------|------|------|
| `/joint_states` | `sensor_msgs/JointState` | 发布 | 关节状态 |
| `/tf` | `tf2_msgs/TFMessage` | 发布 | 动态坐标变换 |
| `/tf_static` | `tf2_msgs/TFMessage` | 发布 | 静态坐标变换 |
| `/<controller>/joint_trajectory` | `trajectory_msgs/JointTrajectory` | 订阅 | 轨迹命令 |

### 7.2 控制器服务

| 服务名 | 服务类型 | 说明 |
|--------|----------|------|
| `/controller_manager/list_controllers` | `controller_manager_msgs/ListControllers` | 列出控制器 |
| `/controller_manager/load_controller` | `controller_manager_msgs/LoadController` | 加载控制器 |
| `/controller_manager/switch_controller` | `controller_manager_msgs/SwitchController` | 切换控制器 |

### 7.3 MoveIt 服务

| 服务名 | 服务类型 | 说明 |
|--------|----------|------|
| `/plan_kinematic_path` | `moveit_msgs/GetMotionPlan` | 规划路径 |
| `/execute_trajectory` | `moveit_msgs/ExecuteKnownTrajectory` | 执行轨迹 |

---

## 8. 命名空间管理

### 8.1 命名空间策略

支持两种模式：

#### 无命名空间（默认）
```
/joint_states
/controller_manager
/left_arm_joint_trajectory_controller
```

#### 带命名空间
```
/<namespace>/joint_states
/<namespace>/controller_manager
/<namespace>/left_arm_joint_trajectory_controller
```

**用途：** 多机器人系统，避免话题冲突

### 8.2 命名空间配置

```python
# Launch 文件中
arm_prefix = LaunchConfiguration("arm_prefix")

Node(
    package="robot_state_publisher",
    namespace=arm_prefix,  # 应用命名空间
    ...
)
```

---

## 9. 数据流

### 9.1 控制循环数据流

```
用户命令 (MoveIt / Teleop)
    │
    ▼
轨迹规划 (MoveIt)
    │
    ▼
轨迹消息 → Joint Trajectory Controller
    │
    ▼
插值和 PID 控制
    │
    ▼
命令接口 (position / velocity / effort)
    │
    ▼
Hardware Interface write()
    │
    ▼
CAN 消息 → 电机
    │
    ▼
电机执行
    │
    ▼
CAN 反馈 ← 电机
    │
    ▼
Hardware Interface read()
    │
    ▼
状态接口 (position / velocity / effort)
    │
    ▼
Joint State Broadcaster
    │
    ▼
/joint_states 话题
    │
    ▼
应用层 (RViz / MoveIt / 监控)
```

### 9.2 TF 树结构

**单臂：**
```
world
  └─ openarm_link0
      ├─ openarm_link1
      │   └─ openarm_link2
      │       └─ openarm_link3
      │           └─ openarm_link4
      │               └─ openarm_link5
      │                   └─ openarm_link6
      │                       └─ openarm_link7
      │                           └─ openarm_hand (可选)
```

**双臂：**
```
world
  └─ openarm_body_link0
      ├─ openarm_left_link0
      │   └─ openarm_left_link1
      │       └─ ... (7个关节)
      │           └─ openarm_left_hand
      │
      └─ openarm_right_link0
          └─ openarm_right_link1
              └─ ... (7个关节)
                  └─ openarm_right_hand
```

---

## 10. 实时性考虑

### 10.1 控制频率

- **Hardware Interface**：500 Hz (read/write)
- **Controller Update**：500 Hz
- **Joint State Publisher**：100 Hz
- **TF Broadcaster**：50 Hz

### 10.2 实时优化

**建议：**
1. 使用实时内核（RT-PREEMPT）
2. 设置进程优先级
3. 锁定内存（mlockall）
4. 使用 DDS 实时配置

**非必需，但推荐用于生产环境。**

---

## 11. 设计决策

### 11.1 为什么使用 ros2_control？

**优势：**
- 统一的硬件抽象层
- 丰富的控制器生态
- 与 MoveIt2 无缝集成
- 社区支持

### 11.2 为什么分离多个包？

**原因：**
- **模块化**：各包职责清晰
- **可维护性**：独立开发和测试
- **灵活性**：按需加载功能
- **可重用性**：其他项目可复用子包

### 11.3 为什么使用 MoveIt2？

**优势：**
- 成熟的运动规划框架
- 多种规划算法
- 碰撞检测
- ROS2 标准

---

## 12. 扩展性

### 12.1 添加新控制器

1. 选择合适的控制器类型（或开发自定义控制器）
2. 在配置文件中添加控制器定义
3. 在 Launch 文件中spawn控制器

### 12.2 集成新传感器

1. 在 URDF 中添加传感器描述
2. 更新 SRDF（如果影响规划）
3. 添加传感器驱动节点

### 12.3 支持新机械臂型号

1. 创建新的 URDF 模型
2. 实现对应的 Hardware Interface
3. 配置控制器参数
4. 更新 MoveIt 配置

---

## 13. 参考资源

- **ROS2 文档**：https://docs.ros.org/
- **ros2_control**：https://control.ros.org/
- **MoveIt2**：https://moveit.ros.org/
- **OpenArm 官方文档**：https://docs.openarm.dev/

---

**文档维护**：请在修改架构或添加新功能时同步更新本文档。
