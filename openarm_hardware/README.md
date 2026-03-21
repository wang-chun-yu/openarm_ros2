# OpenArm Hardware - 硬件接口实现

**功能：** OpenArm 机械臂的 ROS2 Control 硬件接口

---

## 📋 概述

`openarm_hardware` 包实现了 OpenArm 机械臂与 ros2_control 框架的硬件接口，负责：
- 与电机的 CAN 总线通信
- 状态读取（位置、速度、力矩）
- 命令写入（位置、速度、力矩控制）
- 硬件生命周期管理

**核心类：** `OpenArm_v10HW`

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│            ROS2 Control Framework                        │
│  (Controller Manager, Controllers)                      │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ command_interfaces / state_interfaces
                  ▼
┌─────────────────────────────────────────────────────────┐
│         OpenArm_v10HW (本包)                            │
│  • on_init()    - 初始化硬件参数                         │
│  • on_configure() - 配置硬件                            │
│  • on_activate()  - 使能电机                            │
│  • read()       - 读取状态 (500Hz)                      │
│  • write()      - 写入命令 (500Hz)                      │
│  • on_deactivate() - 禁用电机                           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ openarm CAN API
                  ▼
┌─────────────────────────────────────────────────────────┐
│         openarm_can (CAN 通信库)                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ SocketCAN
                  ▼
┌─────────────────────────────────────────────────────────┐
│            CAN 硬件总线                                  │
│  (can0, can1, etc.)                                     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│         电机驱动器                                       │
│  (DM8009, DM4340, DM4310)                               │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 文件结构

```
openarm_hardware/
├── include/
│   └── openarm_hardware/
│       ├── v10_simple_hardware.hpp    # 硬件接口头文件
│       └── visibility_control.h       # 符号导出控制
│
├── src/
│   └── v10_simple_hardware.cpp        # 硬件接口实现
│
├── CMakeLists.txt                     # CMake 构建配置
├── package.xml                        # ROS2 包清单
└── openarm_hardware.xml               # pluginlib 插件描述
```

---

## 🔧 核心类：OpenArm_v10HW

### 类定义

```cpp
class OpenArm_v10HW : public hardware_interface::SystemInterface {
public:
  // 生命周期方法
  CallbackReturn on_init(const HardwareInfo& info) override;
  CallbackReturn on_configure(const State& previous_state) override;
  CallbackReturn on_activate(const State& previous_state) override;
  CallbackReturn on_deactivate(const State& previous_state) override;
  
  // 接口导出
  std::vector<StateInterface> export_state_interfaces() override;
  std::vector<CommandInterface> export_command_interfaces() override;
  
  // 实时控制循环
  return_type read(const Time& time, const Duration& period) override;
  return_type write(const Time& time, const Duration& period) override;
};
```

---

### 主要方法说明

#### `on_init(const HardwareInfo& info)`

**功能：** 初始化硬件接口

**执行时机：** 加载插件时

**主要任务：**
1. 解析 URDF 中的硬件参数：
   - `can_interface`：CAN 接口名称（如 can0）
   - `arm_side`：机械臂侧（left/right）
2. 初始化内部数据结构（关节数组）
3. 验证配置有效性

**返回：** `SUCCESS` 或 `ERROR`

---

#### `on_configure(const State& previous_state)`

**功能：** 配置硬件设备

**执行时机：** Controller Manager 配置硬件时

**主要任务：**
1. 初始化 CAN 通信对象
2. 配置电机参数
3. 设置通信参数（波特率等）

**返回：** `SUCCESS` 或 `ERROR`

---

#### `on_activate(const State& previous_state)`

**功能：** 激活硬件（使能电机）

**执行时机：** 控制器启动前

**主要任务：**
1. 使能所有电机
2. 读取当前位置作为初始位置
3. 清零命令缓冲区

**返回：** `SUCCESS` 或 `ERROR`

---

#### `read(const Time& time, const Duration& period)`

**功能：** 从硬件读取状态

**调用频率：** 500 Hz（由 controller_manager 调用）

**主要任务：**
1. 从 CAN 总线读取电机反馈
2. 更新状态接口：
   - `hw_positions_[]`：关节位置（弧度）
   - `hw_velocities_[]`：关节速度（弧度/秒）
   - `hw_efforts_[]`：关节力矩（牛·米）

**返回：** `OK` 或 `ERROR`

**伪代码：**
```cpp
for (size_t i = 0; i < ARM_DOF; ++i) {
  auto state = openarm_->GetMotorState(i);
  hw_positions_[i] = state.position;
  hw_velocities_[i] = state.velocity;
  hw_efforts_[i] = state.torque;
}
```

---

#### `write(const Time& time, const Duration& period)`

**功能：** 向硬件写入命令

**调用频率：** 500 Hz（由 controller_manager 调用）

**主要任务：**
1. 从命令接口读取控制器命令：
   - `hw_commands_position_[]`
   - `hw_commands_velocity_[]`
   - `hw_commands_effort_[]`
2. 发送 CAN 命令到电机

**返回：** `OK` 或 `ERROR`

**伪代码：**
```cpp
for (size_t i = 0; i < ARM_DOF; ++i) {
  openarm_->SendPositionCommand(
    i, 
    hw_commands_position_[i],
    hw_commands_velocity_[i],  // 可选
    hw_commands_effort_[i]     // 可选
  );
}
```

---

#### `on_deactivate(const State& previous_state)`

**功能：** 停用硬件（禁用电机）

**执行时机：** 控制器停止时

**主要任务：**
1. 发送停止命令到所有电机
2. 禁用电机
3. 清理资源

**返回：** `SUCCESS` 或 `ERROR`

---

## 🔌 接口定义

### 命令接口（Command Interfaces）

每个关节提供以下命令接口：

| 接口名 | 类型 | 单位 | 说明 |
|--------|------|------|------|
| `<joint_name>/position` | double | 弧度 | 目标位置 |
| `<joint_name>/velocity` | double | 弧度/秒 | 目标速度（可选） |
| `<joint_name>/effort` | double | 牛·米 | 目标力矩（可选） |

**URDF 配置：**
```xml
<joint name="openarm_joint1">
  <command_interface name="position"/>
  <command_interface name="velocity"/>
  <command_interface name="effort"/>
</joint>
```

---

### 状态接口（State Interfaces）

每个关节提供以下状态接口：

| 接口名 | 类型 | 单位 | 说明 |
|--------|------|------|------|
| `<joint_name>/position` | double | 弧度 | 当前位置 |
| `<joint_name>/velocity` | double | 弧度/秒 | 当前速度 |
| `<joint_name>/effort` | double | 牛·米 | 当前力矩 |

**URDF 配置：**
```xml
<joint name="openarm_joint1">
  <state_interface name="position"/>
  <state_interface name="velocity"/>
  <state_interface name="effort"/>
</joint>
```

---

## ⚙️ URDF 配置

### 基本配置

```xml
<ros2_control name="openarm_hardware_interface" type="system">
  <hardware>
    <plugin>openarm_hardware/OpenArm_v10HW</plugin>
    
    <!-- CAN 接口配置 -->
    <param name="can_interface">can0</param>
    
    <!-- 机械臂侧（单臂可省略） -->
    <param name="arm_side">right</param>
  </hardware>
  
  <!-- 关节定义 -->
  <joint name="openarm_joint1">
    <command_interface name="position">
      <param name="min">-3.14</param>
      <param name="max">3.14</param>
    </command_interface>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
    <state_interface name="effort"/>
  </joint>
  
  <!-- 其他关节... -->
</ros2_control>
```

### 双臂配置

```xml
<!-- 左臂 -->
<ros2_control name="left_arm_hardware_interface" type="system">
  <hardware>
    <plugin>openarm_hardware/OpenArm_v10HW</plugin>
    <param name="can_interface">can1</param>
    <param name="arm_side">left</param>
  </hardware>
  <joint name="openarm_left_joint1">
    <!-- ... -->
  </joint>
</ros2_control>

<!-- 右臂 -->
<ros2_control name="right_arm_hardware_interface" type="system">
  <hardware>
    <plugin>openarm_hardware/OpenArm_v10HW</plugin>
    <param name="can_interface">can0</param>
    <param name="arm_side">right</param>
  </hardware>
  <joint name="openarm_right_joint1">
    <!-- ... -->
  </joint>
</ros2_control>
```

---

## 🛠️ 开发和调试

### 编译

```bash
cd ~/openarm_ros2_ws
colcon build --packages-select openarm_hardware
```

### 验证插件注册

```bash
# 查看插件是否正确注册
ros2 pkg prefix openarm_hardware
ros2 run controller_manager list_controller_types | grep OpenArm
```

### 查看硬件组件状态

```bash
# 启动系统后
ros2 control list_hardware_components

# 输出示例：
# openarm_hardware_interface[system] active
```

### 调试日志

```bash
# 启动时增加日志级别
ros2 launch openarm_bringup openarm.launch.py --log-level DEBUG

# 查看硬件接口日志
ros2 run rqt_console rqt_console
# 过滤：openarm_hardware
```

---

## ⚠️ 注意事项

### 实时性要求

- `read()` 和 `write()` 在实时循环中调用（500Hz）
- 避免在这些函数中进行阻塞操作
- 不要在 `read()` / `write()` 中打印日志（影响性能）

### 线程安全

- 状态和命令接口由 Controller Manager 管理
- 不要直接访问其他线程的数据

### 错误处理

- `read()` / `write()` 返回 `ERROR` 会导致控制器停止
- 应实现重试机制或错误恢复

---

## 🔗 相关文档

- [架构设计文档](../doc/ARCHITECTURE.md)
- [开发指南](../doc/DEVELOPMENT_GUIDE.md)
- [openarm_bringup](../openarm_bringup/README.md)

---

**维护：** 修改硬件接口时请更新本文档。
