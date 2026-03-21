# OpenArm ROS2 - ROS2 集成包

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-green.svg)](https://docs.ros.org/en/humble/)

OpenArm 机械臂的 ROS2 (Robot Operating System 2) 集成包，提供完整的机器人控制、运动规划和可视化功能。

> ROS2 是用于构建机器人软件的现代化开源框架：https://www.ros.org/

---

## 📋 目录

- [功能概述](#功能概述)
- [包说明](#包说明)
- [快速开始](#快速开始)
- [使用示例](#使用示例)
- [文档导航](#文档导航)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

---

## 功能概述

### ✨ 核心功能

- 🤖 **ROS2 Control 集成**：标准化的硬件接口和控制器管理
- 📡 **实时状态发布**：关节状态、TF 变换、传感器数据
- 🎯 **MoveIt2 运动规划**：路径规划、避障、逆运动学
- 🎨 **可视化工具**：RViz2 集成和调试界面
- 🔄 **单臂/双臂支持**：灵活配置单机械臂或双臂协同
- 🔌 **硬件抽象**：统一接口支持真实硬件和仿真

### 🎯 应用场景

- 机器人运动控制和规划
- 轨迹跟踪和执行
- 多机器人协同
- 人机交互应用
- 研究和教育

---

## 包说明

本仓库包含以下 ROS2 包：

### 📦 openarm（元包）
**功能：** 依赖管理，方便安装所有 OpenArm ROS2 包

**用途：**
```bash
sudo apt install ros-humble-openarm
# 或
rosdep install --from-paths src --ignore-src -r -y
```

---

### 🚀 openarm_bringup
**功能：** 机器人启动和控制器配置

**包含：**
- Launch 文件（单臂/双臂启动）
- 控制器配置（位置、速度、力矩控制器）
- RViz 配置文件

**使用：**
```bash
# 单臂启动
ros2 launch openarm_bringup openarm.launch.py

# 双臂启动
ros2 launch openarm_bringup openarm.bimanual.launch.py
```

详见 [openarm_bringup/README.md](openarm_bringup/README.md)

---

### 🔧 openarm_hardware
**功能：** ROS2 Control 硬件接口实现

**核心类：** `OpenArmV10SimpleHardware`

**职责：**
- 实现 `hardware_interface::SystemInterface`
- CAN 总线通信
- 状态读取和命令写入（500Hz）

**支持的接口：**
- 位置命令/状态
- 速度命令/状态
- 力矩命令/状态

详见 [openarm_hardware/README.md](openarm_hardware/README.md)

---

### 🎯 openarm_bimanual_moveit_config
**功能：** MoveIt2 运动规划配置（双臂）

**包含：**
- SRDF（语义机器人描述）
- 运动学配置（IK 求解器）
- 碰撞矩阵
- MoveIt 控制器配置
- 规划参数

**使用：**
```bash
# 启动 MoveIt 演示
ros2 launch openarm_bimanual_moveit_config demo.launch.py
```

详见 [openarm_bimanual_moveit_config/README.md](openarm_bimanual_moveit_config/README.md)

---

## 快速开始

### 5 分钟体验

#### 1. 安装依赖

```bash
cd ~/openarm_ros2_ws
rosdep install --from-paths src --ignore-src -r -y
```

#### 2. 编译

```bash
colcon build --symlink-install
source install/setup.bash
```

#### 3. 启动仿真

```bash
# 单臂仿真
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true
```

#### 4. 控制机械臂

在 RViz 中或使用 rqt 工具控制关节。

**详细步骤见** [快速开始指南](doc/QUICK_START.md)

---

## 使用示例

### 示例 1：单臂 RViz 可视化

```bash
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true
```

### 示例 2：双臂真实硬件控制

```bash
# 配置 CAN 接口
sudo ip link set can0 type can bitrate 1000000 && sudo ip link set up can0
sudo ip link set can1 type can bitrate 1000000 && sudo ip link set up can1

# 启动双臂
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    left_can_interface:=can1 \
    right_can_interface:=can0
```

### 示例 3：MoveIt 运动规划

```bash
# 启动 MoveIt
ros2 launch openarm_bimanual_moveit_config demo.launch.py

# 在 RViz 中拖动交互式标记进行规划
```

### 示例 4：Python API 控制

```python
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class ArmController(Node):
    def __init__(self):
        super().__init__('arm_controller')
        self.publisher = self.create_publisher(
            JointTrajectory, 
            '/joint_trajectory_controller/joint_trajectory', 
            10
        )
    
    def move_to_position(self, positions):
        msg = JointTrajectory()
        msg.joint_names = ['openarm_joint1', 'openarm_joint2', ...]
        
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start.sec = 2
        
        msg.points = [point]
        self.publisher.publish(msg)

# 使用
rclpy.init()
controller = ArmController()
controller.move_to_position([0.5, 0.3, 0.0, 0.8, 0.0, 0.0, 0.0])
```

---

## 文档导航

### 📚 完整文档

- **[架构设计文档](doc/ARCHITECTURE.md)**
  - ROS2 Control 架构
  - MoveIt 集成
  - 数据流和组件关系
  
- **[快速开始指南](doc/QUICK_START.md)** ⏱️ **10分钟**
  - 安装和编译
  - 启动和控制
  - 常用命令
  
- **[开发指南](doc/DEVELOPMENT_GUIDE.md)**
  - 参数配置
  - 自定义控制器
  - 调试技巧

### 📦 子包文档

- [openarm_bringup](openarm_bringup/README.md) - 启动和配置
- [openarm_hardware](openarm_hardware/README.md) - 硬件接口
- [openarm_bimanual_moveit_config](openarm_bimanual_moveit_config/README.md) - MoveIt 配置

---

## 常见问题

### Q1：ros2_control 和 openarm_teleop 有什么区别？

**ros2_control（本包）：**
- 基于 ROS2 标准框架
- 集成 MoveIt 运动规划
- 适合高层应用（轨迹规划、任务执行）
- 通过话题/服务通信

**openarm_teleop：**
- 底层 C++ 直接控制
- 实时遥操作和重力补偿
- 适合低层控制（力控、遥操作）
- 直接 CAN 通信

**选择建议：**
- 需要运动规划 → 使用 ros2_control + MoveIt
- 需要力控/遥操作 → 使用 openarm_teleop

### Q2：如何切换控制器？

```bash
# 停止当前控制器
ros2 control set_controller_state joint_trajectory_controller stop

# 启动另一个控制器
ros2 control set_controller_state velocity_controller start
```

### Q3：如何调试硬件通信？

```bash
# 查看硬件接口日志
ros2 run rqt_console rqt_console

# 监控 CAN 消息
candump can0

# 测试 CAN 通信
cansend can0 001#1122334455667788
```

---

## 依赖包

**ROS2 核心包：**
- `ros2_control`
- `ros2_controllers`
- `moveit2`
- `robot_state_publisher`
- `joint_state_publisher`

**OpenArm 特定包：**
- `openarm_description`：机器人 URDF 模型
- `openarm_can`：CAN 通信库

**安装：**
```bash
rosdep install --from-paths src --ignore-src -r -y
```

---

## 贡献指南

我们欢迎社区贡献！请参考：

1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 相关资源

- 📚 [OpenArm 官方文档](https://docs.openarm.dev/software/ros2/install)
- 💬 [Discord 社区](https://discord.gg/FsZaZ4z3We)
- 📬 [联系我们](mailto:openarm@enactic.ai)
- 🐛 [报告问题](https://github.com/openarm/openarm_ros2/issues)

---

## 许可证

[Apache License 2.0](LICENSE)

Copyright 2025 Enactic, Inc.

---

## 行为准则

All participation in the OpenArm project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

**祝使用愉快！** 如有问题，请查阅 [文档](doc/) 或联系我们。
