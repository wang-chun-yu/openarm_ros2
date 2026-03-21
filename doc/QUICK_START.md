# OpenArm ROS2 快速开始指南

**版本：** 1.0  
**日期：** 2026-02-09  
**预计时间：** 10 分钟

---

## 🎯 目标

本指南将帮助你在 10 分钟内：
1. 安装 OpenArm ROS2 包
2. 启动机械臂
3. 使用 RViz 可视化
4. 执行简单的运动控制

---

## ✅ 前置条件

### 系统要求
- Ubuntu 22.04 LTS
- ROS2 Humble 已安装
- 至少 8GB RAM

### 硬件要求（可选）
- OpenArm 机械臂（用于真实硬件控制）
- CAN 接口（如 Peak PCAN-USB）

---

## 📦 步骤 1：安装依赖

### 1.1 安装 ROS2 Humble

如果尚未安装，请参考：https://docs.ros.org/en/humble/Installation.html

### 1.2 创建工作空间

```bash
# 创建工作空间
mkdir -p ~/openarm_ros2_ws/src
cd ~/openarm_ros2_ws/src

# 克隆 OpenArm 相关包
# 注意：根据实际情况调整克隆命令
```

### 1.3 安装依赖包

```bash
cd ~/openarm_ros2_ws

# 使用 rosdep 安装依赖
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 1.4 编译工作空间

```bash
cd ~/openarm_ros2_ws

# 编译所有包
colcon build --symlink-install

# 源配置
source install/setup.bash
```

---

## 🚀 步骤 2：启动机械臂（仿真模式）

### 2.1 单臂仿真

```bash
# 源 ROS2 环境
source ~/openarm_ros2_ws/install/setup.bash

# 启动单臂（使用假硬件）
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true
```

**预期结果：**
- RViz 窗口打开
- 显示 OpenArm 机械臂模型
- 可以看到 Joint State Publisher GUI（可拖动关节）

### 2.2 双臂仿真

```bash
# 启动双臂（使用假硬件）
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true
```

**预期结果：**
- RViz 显示双臂机器人
- 机身 + 左右两个机械臂

---

## 🎮 步骤 3：控制机械臂

### 3.1 查看控制器状态

**打开新终端：**

```bash
source ~/openarm_ros2_ws/install/setup.bash

# 列出所有控制器
ros2 control list_controllers
```

**预期输出：**
```
joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
joint_trajectory_controller[joint_trajectory_controller/JointTrajectoryController] active
```

### 3.2 手动发送关节命令

```bash
# 发布一个简单的关节轨迹
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory \
    trajectory_msgs/msg/JointTrajectory \
    "{
        joint_names: ['openarm_joint1', 'openarm_joint2', 'openarm_joint3', 
                      'openarm_joint4', 'openarm_joint5', 'openarm_joint6', 'openarm_joint7'],
        points: [
            {positions: [0.5, 0.3, 0.0, 0.8, 0.0, 0.0, 0.0], time_from_start: {sec: 2}}
        ]
    }"
```

**预期结果：**
- 机械臂在 RViz 中运动到指定位置
- 2 秒内完成运动

### 3.3 使用 rqt 控制

```bash
# 打开 rqt joint trajectory controller
ros2 run rqt_joint_trajectory_controller rqt_joint_trajectory_controller
```

**操作：**
1. 选择 `joint_trajectory_controller`
2. 拖动滑块控制各关节
3. 点击 "Send" 发送命令

---

## 📊 步骤 4：查看话题和状态

### 4.1 查看关节状态

```bash
# 实时查看关节状态
ros2 topic echo /joint_states
```

**输出示例：**
```yaml
header:
  stamp: {sec: 123, nanosec: 456}
  frame_id: ''
name:
- openarm_joint1
- openarm_joint2
- ...
position: [0.0, 0.0, 0.0, ...]
velocity: [0.0, 0.0, 0.0, ...]
effort: [0.0, 0.0, 0.0, ...]
```

### 4.2 查看 TF 树

```bash
# 生成 TF 树图
ros2 run tf2_tools view_frames

# 查看生成的 PDF
evince frames.pdf
```

### 4.3 监控系统状态

```bash
# 打开 rqt 仪表板
rqt
```

**推荐插件：**
- **Plugins > Topics > Topic Monitor**：监控话题
- **Plugins > Robot Tools > Controller Manager**：管理控制器
- **Plugins > Visualization > TF Tree**：查看 TF 树

---

## 🤖 步骤 5：使用 MoveIt（可选）

### 5.1 启动 MoveIt 演示

```bash
# 启动 MoveIt 演示（双臂）
ros2 launch openarm_bimanual_moveit_config demo.launch.py
```

**预期结果：**
- RViz 打开，带 MoveIt 插件
- 可以拖动交互式标记进行运动规划

### 5.2 运动规划

**在 RViz 中：**

1. **选择规划组**：
   - 在 "Motion Planning" 面板
   - Planning Group 选择 `left_arm` 或 `right_arm`

2. **设置目标位置**：
   - 拖动橙色球体（交互式标记）
   - 或在 "Goal State" 中设置关节值

3. **规划路径**：
   - 点击 "Plan" 按钮
   - 查看规划的轨迹（橙色线条）

4. **执行运动**：
   - 点击 "Execute" 按钮
   - 机械臂运动到目标位置

---

## 🔧 步骤 6：真实硬件控制（可选）

### 6.1 配置 CAN 接口

```bash
# 设置 CAN 接口
sudo ip link set can0 type can bitrate 1000000
sudo ip link set up can0

# 验证 CAN 接口
ip link show can0
```

### 6.2 启动真实硬件

```bash
# 单臂（真实硬件）
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    can_interface:=can0 \
    launch_rviz:=true
```

**⚠️ 警告：**
- 确保机械臂周围无障碍物
- 手握急停按钮
- 阅读安全操作指南

### 6.3 双臂真实硬件

```bash
# 双臂（真实硬件）
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    left_can_interface:=can1 \
    right_can_interface:=can0 \
    launch_rviz:=true
```

---

## 🐛 常见问题

### Q1：RViz 不显示机器人

**检查：**
```bash
# 检查 robot_description 话题
ros2 topic echo /robot_description --once

# 检查 TF
ros2 run tf2_ros tf2_echo world openarm_link7
```

**解决：**
- 确认 robot_state_publisher 节点运行
- 检查 Fixed Frame 设置为 `world`

---

### Q2：控制器未激活

**检查：**
```bash
ros2 control list_controllers
```

**解决：**
```bash
# 手动激活控制器
ros2 control set_controller_state joint_trajectory_controller start
```

---

### Q3：CAN 接口错误

**检查：**
```bash
# 验证 CAN 接口状态
ip link show can0

# 查看 CAN 消息
candump can0
```

**解决：**
- 确认 CAN 接口已启用
- 检查波特率设置（1 Mbps）
- 验证物理连接

---

## 📚 下一步

恭喜！你已经完成快速开始。接下来可以：

1. **深入学习**：
   - 阅读 [架构文档](ARCHITECTURE.md)
   - 学习 [开发指南](DEVELOPMENT_GUIDE.md)

2. **尝试高级功能**：
   - Python API 控制
   - 自定义轨迹规划
   - 多机器人协同

3. **开发自己的应用**：
   - 创建自定义节点
   - 集成传感器
   - 实现复杂任务

---

## 🔗 有用的命令速查

```bash
# 启动单臂仿真
ros2 launch openarm_bringup openarm.launch.py arm_type:=v10 use_fake_hardware:=true

# 启动双臂仿真
ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v10 use_fake_hardware:=true

# 列出控制器
ros2 control list_controllers

# 查看关节状态
ros2 topic echo /joint_states

# 查看可用话题
ros2 topic list

# 查看可用服务
ros2 service list

# 启动 MoveIt
ros2 launch openarm_bimanual_moveit_config demo.launch.py

# 查看 TF 树
ros2 run tf2_tools view_frames

# 打开 rqt
rqt
```

---

## 📞 获取帮助

- **文档**：https://docs.openarm.dev/
- **Discord**：https://discord.gg/FsZaZ4z3We
- **邮件**：openarm@enactic.ai
- **GitHub Issues**：报告 bug 和请求功能

---

**祝使用愉快！** 🎉
