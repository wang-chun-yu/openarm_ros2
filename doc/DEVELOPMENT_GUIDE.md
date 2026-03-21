# OpenArm ROS2 开发指南

**版本：** 1.0  
**日期：** 2026-02-09  
**目标读者：** ROS2 开发者、系统集成工程师

---

## 📋 目录

1. [环境搭建](#环境搭建)
2. [开发工作流](#开发工作流)
3. [修改控制器配置](#修改控制器配置)
4. [开发自定义控制器](#开发自定义控制器)
5. [硬件接口开发](#硬件接口开发)
6. [调试技巧](#调试技巧)
7. [性能优化](#性能优化)
8. [测试策略](#测试策略)
9. [常见开发任务](#常见开发任务)

---

## 环境搭建

### 系统要求

**操作系统：**
- Ubuntu 22.04 LTS（推荐）
- Ubuntu 20.04 LTS（需要 ROS2 Humble backport）

**硬件：**
- CPU：4 核心以上（推荐 8 核心）
- RAM：8GB 以上（推荐 16GB）
- CAN 接口：Peak PCAN-USB 或兼容设备

### 安装 ROS2 Humble

```bash
# 添加 ROS2 apt 源
sudo apt update && sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 安装 ROS2 Humble Desktop
sudo apt update
sudo apt install ros-humble-desktop -y

# 安装开发工具
sudo apt install python3-colcon-common-extensions python3-rosdep -y
```

### 创建工作空间

```bash
# 创建工作空间目录
mkdir -p ~/openarm_ros2_ws/src
cd ~/openarm_ros2_ws/src

# 克隆 OpenArm 相关包（根据实际情况调整）
# git clone <openarm_ros2_repo>
# git clone <openarm_description_repo>
# git clone <openarm_can_repo>

# 初始化 rosdep
sudo rosdep init
rosdep update

# 安装依赖
cd ~/openarm_ros2_ws
rosdep install --from-paths src --ignore-src -r -y
```

### 编译工作空间

```bash
cd ~/openarm_ros2_ws

# 编译所有包
colcon build --symlink-install

# 使用符号链接（推荐开发时使用）
# 优点：修改 Python 脚本和 launch 文件无需重新编译

# 仅编译特定包
colcon build --packages-select openarm_hardware

# 并行编译（加速）
colcon build --symlink-install --parallel-workers 4
```

### 配置环境变量

```bash
# 添加到 ~/.bashrc
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/openarm_ros2_ws/install/setup.bash" >> ~/.bashrc

# 立即生效
source ~/.bashrc
```

---

## 开发工作流

### 基本工作流

```bash
# 1. 修改代码
vim ~/openarm_ros2_ws/src/openarm_hardware/src/v10_simple_hardware.cpp

# 2. 编译（C++ 代码需要重新编译）
cd ~/openarm_ros2_ws
colcon build --packages-select openarm_hardware

# 3. 源配置（如果是新终端）
source install/setup.bash

# 4. 运行测试
ros2 launch openarm_bringup openarm.launch.py use_fake_hardware:=true

# 5. 调试和验证
ros2 control list_controllers
ros2 topic echo /joint_states
```

### Git 分支策略

```bash
# 创建功能分支
git checkout -b feature/add-velocity-controller

# 开发和提交
git add .
git commit -m "feat: add velocity controller for improved teleoperation"

# 推送到远程
git push origin feature/add-velocity-controller

# 创建 Pull Request
```

---

## 修改控制器配置

### 调整控制器参数

**文件：** `openarm_bringup/config/v10_controllers/openarm_v10_controllers.yaml`

#### 示例 1：调整轨迹控制器频率

```yaml
joint_trajectory_controller:
  ros__parameters:
    joints: [...]
    
    # 提高状态发布频率（默认 50Hz → 100Hz）
    state_publish_rate: 100.0
    action_monitor_rate: 100.0
    
    # 调整停止容忍度（更严格）
    constraints:
      stopped_velocity_tolerance: 0.005  # 默认 0.01
      goal_time: 0.0
```

#### 示例 2：添加 PID 参数

```yaml
joint_trajectory_controller:
  ros__parameters:
    joints: [...]
    
    # 为每个关节配置 PID 参数
    gains:
      openarm_joint1:
        p: 100.0
        i: 1.0
        d: 10.0
      openarm_joint2:
        p: 150.0
        i: 1.0
        d: 15.0
      # ... 其他关节
```

#### 示例 3：配置速度限制

```yaml
joint_trajectory_controller:
  ros__parameters:
    joints: [...]
    
    # 设置速度和加速度限制
    command_interfaces:
      - position
    state_interfaces:
      - position
      - velocity
    
    # 限制（弧度/秒，弧度/秒²）
    limits:
      openarm_joint1:
        max_velocity: 2.0
        max_acceleration: 5.0
      # ... 其他关节
```

### 修改后测试

```bash
# 重新启动系统
ros2 launch openarm_bringup openarm.launch.py

# 验证新参数
ros2 param get /joint_trajectory_controller state_publish_rate
```

---

## 开发自定义控制器

### 创建控制器插件

#### 步骤 1：创建包

```bash
cd ~/openarm_ros2_ws/src
ros2 pkg create openarm_controllers \
    --build-type ament_cmake \
    --dependencies rclcpp controller_interface hardware_interface
```

#### 步骤 2：实现控制器类

**文件：** `openarm_controllers/include/openarm_controllers/my_custom_controller.hpp`

```cpp
#ifndef OPENARM_CONTROLLERS__MY_CUSTOM_CONTROLLER_HPP_
#define OPENARM_CONTROLLERS__MY_CUSTOM_CONTROLLER_HPP_

#include "controller_interface/controller_interface.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"

namespace openarm_controllers
{

class MyCustomController : public controller_interface::ControllerInterface
{
public:
  MyCustomController();
  
  // 必须实现的接口
  controller_interface::InterfaceConfiguration command_interface_configuration() const override;
  controller_interface::InterfaceConfiguration state_interface_configuration() const override;
  
  controller_interface::return_type update(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  
  controller_interface::CallbackReturn on_init() override;
  controller_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;
  controller_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;
  controller_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

private:
  std::vector<std::string> joint_names_;
  rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr command_subscriber_;
  std::vector<double> commands_;
};

}  // namespace openarm_controllers

#endif  // OPENARM_CONTROLLERS__MY_CUSTOM_CONTROLLER_HPP_
```

**实现文件：** `openarm_controllers/src/my_custom_controller.cpp`

```cpp
#include "openarm_controllers/my_custom_controller.hpp"

namespace openarm_controllers
{

MyCustomController::MyCustomController()
: controller_interface::ControllerInterface()
{
}

controller_interface::CallbackReturn MyCustomController::on_init()
{
  // 从参数服务器读取关节名称
  joint_names_ = node_->get_parameter("joints").as_string_array();
  commands_.resize(joint_names_.size(), 0.0);
  return controller_interface::CallbackReturn::SUCCESS;
}

controller_interface::InterfaceConfiguration 
MyCustomController::command_interface_configuration() const
{
  controller_interface::InterfaceConfiguration config;
  config.type = controller_interface::interface_configuration_type::INDIVIDUAL;
  
  for (const auto & joint_name : joint_names_) {
    config.names.push_back(joint_name + "/position");
  }
  
  return config;
}

controller_interface::InterfaceConfiguration 
MyCustomController::state_interface_configuration() const
{
  controller_interface::InterfaceConfiguration config;
  config.type = controller_interface::interface_configuration_type::INDIVIDUAL;
  
  for (const auto & joint_name : joint_names_) {
    config.names.push_back(joint_name + "/position");
    config.names.push_back(joint_name + "/velocity");
  }
  
  return config;
}

controller_interface::CallbackReturn MyCustomController::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // 创建命令订阅者
  command_subscriber_ = node_->create_subscription<std_msgs::msg::Float64MultiArray>(
    "~/commands", 10,
    [this](const std_msgs::msg::Float64MultiArray::SharedPtr msg) {
      if (msg->data.size() == commands_.size()) {
        commands_ = msg->data;
      }
    });
  
  return controller_interface::CallbackReturn::SUCCESS;
}

controller_interface::CallbackReturn MyCustomController::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // 初始化命令为当前位置
  for (size_t i = 0; i < command_interfaces_.size(); ++i) {
    commands_[i] = state_interfaces_[i * 2].get_value();  // position
  }
  
  return controller_interface::CallbackReturn::SUCCESS;
}

controller_interface::return_type MyCustomController::update(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  // 将命令写入硬件接口
  for (size_t i = 0; i < command_interfaces_.size(); ++i) {
    command_interfaces_[i].set_value(commands_[i]);
  }
  
  return controller_interface::return_type::OK;
}

controller_interface::CallbackReturn MyCustomController::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  return controller_interface::CallbackReturn::SUCCESS;
}

}  // namespace openarm_controllers

// 导出控制器插件
#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(
  openarm_controllers::MyCustomController, 
  controller_interface::ControllerInterface)
```

#### 步骤 3：注册插件

**文件：** `openarm_controllers/openarm_controllers.xml`

```xml
<library path="openarm_controllers">
  <class name="openarm_controllers/MyCustomController" 
         type="openarm_controllers::MyCustomController" 
         base_class_type="controller_interface::ControllerInterface">
    <description>
      My custom controller for OpenArm
    </description>
  </class>
</library>
```

**更新 CMakeLists.txt：**

```cmake
pluginlib_export_plugin_description_file(controller_interface openarm_controllers.xml)
```

**更新 package.xml：**

```xml
<export>
  <controller_interface plugin="${prefix}/openarm_controllers.xml"/>
</export>
```

#### 步骤 4：编译和测试

```bash
cd ~/openarm_ros2_ws
colcon build --packages-select openarm_controllers

# 验证插件注册
ros2 pkg prefix openarm_controllers
ros2 run controller_manager list_controller_types | grep MyCustomController
```

---

## 硬件接口开发

### 修改现有硬件接口

**文件：** `openarm_hardware/src/v10_simple_hardware.cpp`

#### 添加新状态接口（例如：电流）

```cpp
// 在 export_state_interfaces() 中
for (uint i = 0; i < info_.joints.size(); i++) {
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    info_.joints[i].name, hardware_interface::HW_IF_POSITION, &hw_positions_[i]));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    info_.joints[i].name, hardware_interface::HW_IF_VELOCITY, &hw_velocities_[i]));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    info_.joints[i].name, hardware_interface::HW_IF_EFFORT, &hw_efforts_[i]));
  
  // 新增：电流接口
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    info_.joints[i].name, "current", &hw_currents_[i]));
}
```

#### 在 read() 中更新电流值

```cpp
hardware_interface::return_type OpenArmV10SimpleHardware::read(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  for (uint i = 0; i < hw_positions_.size(); i++) {
    // 从 CAN 读取位置、速度、力矩
    auto motor_state = openarm_->GetMotorState(i);
    hw_positions_[i] = motor_state.position;
    hw_velocities_[i] = motor_state.velocity;
    hw_efforts_[i] = motor_state.torque;
    
    // 新增：读取电流
    hw_currents_[i] = motor_state.current;
  }
  
  return hardware_interface::return_type::OK;
}
```

---

## 调试技巧

### 使用 rqt 工具

```bash
# 打开 rqt
rqt

# 推荐插件：
# 1. Plugins > Topics > Topic Monitor：监控话题数据
# 2. Plugins > Robot Tools > Controller Manager：管理控制器
# 3. Plugins > Visualization > Plot：绘制数据曲线
# 4. Plugins > Logging > Console：查看日志
```

### 查看详细日志

```bash
# 设置日志级别为 DEBUG
ros2 launch openarm_bringup openarm.launch.py --log-level DEBUG

# 查看特定节点的日志
ros2 run rqt_console rqt_console
```

### 调试 CAN 通信

```bash
# 监控 CAN 消息
candump can0

# 发送测试消息
cansend can0 001#1122334455667788

# 查看 CAN 接口统计
ip -s link show can0

# 查看错误
dmesg | grep can
```

### GDB 调试

```bash
# 使用 GDB 启动节点
ros2 run --prefix 'gdb -ex run --args' controller_manager ros2_control_node

# 在代码中设置断点
(gdb) break OpenArmV10SimpleHardware::read
(gdb) continue
```

---

## 性能优化

### 使用实时内核

```bash
# 安装 RT-PREEMPT 内核
sudo apt install linux-image-rt-amd64

# 重启并选择 RT 内核
sudo reboot

# 验证
uname -a  # 应显示 PREEMPT RT
```

### 配置 ROS2 QoS

```cpp
// 为实时数据使用 BEST_EFFORT QoS
auto qos = rclcpp::QoS(rclcpp::KeepLast(10));
qos.best_effort();
qos.durability_volatile();

auto subscription = node->create_subscription<std_msgs::msg::Float64>(
  "topic", qos, callback);
```

### 优化 DDS 配置

**文件：** `~/.ros/fastdds.xml`

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>SharedMemTransport</transport_id>
      <type>SHM</type>
    </transport_descriptor>
  </transport_descriptors>
</profiles>
```

---

## 测试策略

### 单元测试

```cpp
// 文件：openarm_hardware/test/test_v10_hardware.cpp
#include <gtest/gtest.h>
#include "openarm_hardware/v10_simple_hardware.hpp"

TEST(OpenArmV10HardwareTest, InitializationTest) {
  auto hardware = std::make_shared<openarm_hardware::OpenArmV10SimpleHardware>();
  // 测试初始化逻辑
  ASSERT_NE(hardware, nullptr);
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
```

### 集成测试

```bash
# 使用 launch_testing
# 文件：openarm_bringup/test/test_bringup.py
import unittest
from launch import LaunchDescription
from launch_testing.actions import ReadyToTest

def generate_test_description():
    return LaunchDescription([
        # 启动节点
        # ...
        ReadyToTest()
    ])

class TestBringup(unittest.TestCase):
    def test_controllers_active(self):
        # 测试控制器是否激活
        pass
```

---

## 常见开发任务

### 添加新传感器

1. 在 URDF 中添加传感器描述
2. 在硬件接口中添加传感器接口
3. 实现 read() 方法读取传感器数据
4. 发布传感器话题

### 集成新电机

1. 修改 `openarm_can` 库支持新电机协议
2. 更新硬件接口的电机初始化代码
3. 调整控制参数（PID、限位等）
4. 测试和验证

### 实现力控模式

1. 确保硬件接口导出 `effort` 命令接口
2. 配置 `effort_controller`
3. 实现力传感器反馈（如需要）
4. 调整控制增益

---

## 参考资源

- **ROS2 Control 官方文档**：https://control.ros.org/
- **MoveIt2 教程**：https://moveit.picknik.ai/humble/
- **OpenArm 社区**：https://discord.gg/FsZaZ4z3We

---

**祝开发顺利！** 遇到问题请参考文档或联系社区。
