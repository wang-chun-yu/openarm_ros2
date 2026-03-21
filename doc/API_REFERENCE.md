# OpenArm ROS2 API 参考文档

**版本：** 1.0  
**日期：** 2026-02-09

---

## 📋 目录

1. [Launch 参数](#launch-参数)
2. [ROS2 话题](#ros2-话题)
3. [ROS2 服务](#ros2-服务)
4. [ROS2 Action](#ros2-action)
5. [控制器接口](#控制器接口)
6. [硬件接口](#硬件接口)
7. [坐标系定义](#坐标系定义)

---

## Launch 参数

### openarm.launch.py（单臂）

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `arm_type` | string | `v10` | 机械臂型号 |
| `description_package` | string | `openarm_description` | URDF 包名 |
| `description_file` | string | `v10.urdf.xacro` | URDF 文件名 |
| `use_fake_hardware` | bool | `false` | 使用仿真硬件 |
| `can_interface` | string | `can0` | CAN 接口名称 |
| `controllers_file` | string | `openarm_v10_controllers.yaml` | 控制器配置文件 |
| `launch_rviz` | bool | `false` | 启动 RViz |
| `arm_prefix` | string | `''` | 命名空间前缀 |

**使用示例：**
```bash
ros2 launch openarm_bringup openarm.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=true \
    launch_rviz:=true
```

---

### openarm.bimanual.launch.py（双臂）

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `arm_type` | string | `v10` | 机械臂型号 |
| `description_package` | string | `openarm_description` | URDF 包名 |
| `description_file` | string | `v10.urdf.xacro` | URDF 文件名 |
| `use_fake_hardware` | bool | `false` | 使用仿真硬件 |
| `left_can_interface` | string | `can1` | 左臂 CAN 接口 |
| `right_can_interface` | string | `can0` | 右臂 CAN 接口 |
| `controllers_file` | string | `openarm_v10_bimanual_controllers.yaml` | 控制器配置 |
| `launch_rviz` | bool | `false` | 启动 RViz |
| `robot_controller` | string | `joint_trajectory_controller` | 主控制器类型 |
| `arm_prefix` | string | `''` | 命名空间前缀 |

**使用示例：**
```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py \
    arm_type:=v10 \
    use_fake_hardware:=false \
    left_can_interface:=can1 \
    right_can_interface:=can0
```

---

## ROS2 话题

### 机器人状态话题

#### `/joint_states`
**类型：** `sensor_msgs/msg/JointState`

**发布者：** `joint_state_broadcaster`

**频率：** ~100 Hz

**内容：**
```yaml
header:
  stamp: {sec: 1234, nanosec: 567890000}
  frame_id: ''
name:
  - openarm_joint1
  - openarm_joint2
  - openarm_joint3
  - openarm_joint4
  - openarm_joint5
  - openarm_joint6
  - openarm_joint7
position: [0.0, 0.5, 0.3, 0.8, 0.0, 0.0, 0.0]  # 弧度
velocity: [0.0, 0.1, 0.05, 0.2, 0.0, 0.0, 0.0] # 弧度/秒
effort: [0.0, 2.5, 1.3, 3.2, 0.0, 0.0, 0.0]   # 牛·米
```

---

#### `/tf` 和 `/tf_static`
**类型：** `tf2_msgs/msg/TFMessage`

**发布者：** `robot_state_publisher`

**内容：** 机器人所有链接的坐标变换

---

### 控制器命令话题

#### `/joint_trajectory_controller/joint_trajectory`
**类型：** `trajectory_msgs/msg/JointTrajectory`

**订阅者：** `joint_trajectory_controller`

**用途：** 发送轨迹命令

**示例：**
```python
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

msg = JointTrajectory()
msg.joint_names = [
    'openarm_joint1', 'openarm_joint2', 'openarm_joint3',
    'openarm_joint4', 'openarm_joint5', 'openarm_joint6', 'openarm_joint7'
]

point = JointTrajectoryPoint()
point.positions = [0.5, 0.3, 0.0, 0.8, 0.0, 0.0, 0.0]
point.velocities = [0.0] * 7
point.time_from_start = Duration(sec=2, nanosec=0)

msg.points = [point]

publisher.publish(msg)
```

---

#### `/forward_position_controller/commands`
**类型：** `std_msgs/msg/Float64MultiArray`

**订阅者：** `forward_position_controller`

**用途：** 直接位置控制（无轨迹插值）

**示例：**
```bash
ros2 topic pub --once /forward_position_controller/commands \
    std_msgs/msg/Float64MultiArray \
    "{data: [0.5, 0.3, 0.0, 0.8, 0.0, 0.0, 0.0]}"
```

---

#### `/forward_velocity_controller/commands`
**类型：** `std_msgs/msg/Float64MultiArray`

**订阅者：** `forward_velocity_controller`

**用途：** 速度控制

---

### 双臂话题（bimanual）

**左臂：**
- `/left_joint_trajectory_controller/joint_trajectory`
- `/left_forward_position_controller/commands`

**右臂：**
- `/right_joint_trajectory_controller/joint_trajectory`
- `/right_forward_position_controller/commands`

---

## ROS2 服务

### Controller Manager 服务

#### `/controller_manager/list_controllers`
**类型：** `controller_manager_msgs/srv/ListControllers`

**功能：** 列出所有控制器及其状态

**CLI 使用：**
```bash
ros2 service call /controller_manager/list_controllers \
    controller_manager_msgs/srv/ListControllers
```

**返回示例：**
```yaml
controller:
  - name: joint_state_broadcaster
    type: joint_state_broadcaster/JointStateBroadcaster
    state: active
  - name: joint_trajectory_controller
    type: joint_trajectory_controller/JointTrajectoryController
    state: active
```

---

#### `/controller_manager/switch_controller`
**类型：** `controller_manager_msgs/srv/SwitchController`

**功能：** 切换控制器（启动/停止）

**CLI 使用：**
```bash
# 停止 controller_a，启动 controller_b
ros2 service call /controller_manager/switch_controller \
    controller_manager_msgs/srv/SwitchController \
    "{
        start_controllers: ['controller_b'],
        stop_controllers: ['controller_a'],
        strictness: 2,
        start_asap: false,
        timeout: {sec: 0, nanosec: 0}
    }"
```

---

#### `/controller_manager/load_controller`
**类型：** `controller_manager_msgs/srv/LoadController`

**功能：** 加载控制器插件

---

#### `/controller_manager/unload_controller`
**类型：** `controller_manager_msgs/srv/UnloadController`

**功能：** 卸载控制器

---

### 硬件组件服务

#### `/controller_manager/list_hardware_components`
**类型：** `controller_manager_msgs/srv/ListHardwareComponents`

**功能：** 列出所有硬件组件

**CLI 使用：**
```bash
ros2 service call /controller_manager/list_hardware_components \
    controller_manager_msgs/srv/ListHardwareComponents
```

---

## ROS2 Action

### `/joint_trajectory_controller/follow_joint_trajectory`
**类型：** `control_msgs/action/FollowJointTrajectory`

**功能：** 执行轨迹并返回执行结果

**Goal：**
```yaml
trajectory:
  joint_names: [openarm_joint1, openarm_joint2, ...]
  points:
    - positions: [0.5, 0.3, ...]
      time_from_start: {sec: 2, nanosec: 0}
```

**Result：**
```yaml
error_code: 0  # 0 = SUCCESSFUL, -1 = INVALID_GOAL, ...
error_string: "Success"
```

**Feedback：**
```yaml
header:
  stamp: ...
joint_names: [...]
actual:
  positions: [...]
  velocities: [...]
desired:
  positions: [...]
  velocities: [...]
error:
  positions: [...]
  velocities: [...]
```

**CLI 使用：**
```bash
ros2 action send_goal /joint_trajectory_controller/follow_joint_trajectory \
    control_msgs/action/FollowJointTrajectory \
    "trajectory:
      joint_names: ['openarm_joint1', 'openarm_joint2', ...]
      points:
      - positions: [0.5, 0.3, 0.0, 0.8, 0.0, 0.0, 0.0]
        time_from_start: {sec: 2}
    " --feedback
```

---

### `/gripper_controller/gripper_cmd`
**类型：** `control_msgs/action/GripperCommand`

**功能：** 控制夹爪开合

**Goal：**
```yaml
command:
  position: 0.02  # 米
  max_effort: 5.0 # 牛顿
```

**CLI 使用：**
```bash
ros2 action send_goal /gripper_controller/gripper_cmd \
    control_msgs/action/GripperCommand \
    "{command: {position: 0.02, max_effort: 5.0}}"
```

---

## 控制器接口

### JointTrajectoryController

**命令接口：**
- `<joint_name>/position`

**状态接口：**
- `<joint_name>/position`
- `<joint_name>/velocity`（可选）

**参数：**
```yaml
joints: [list of joint names]
command_interfaces: [position]
state_interfaces: [position, velocity]
state_publish_rate: 50.0
action_monitor_rate: 50.0
allow_partial_joints_goal: false
constraints:
  stopped_velocity_tolerance: 0.01
  goal_time: 0.0
```

---

### ForwardCommandController

**命令接口：**
- `<joint_name>/<interface_name>`（position/velocity/effort）

**状态接口：**
- `<joint_name>/<interface_name>`

**参数：**
```yaml
joints: [list of joint names]
interface_name: position  # or velocity, effort
```

---

## 硬件接口

### OpenArmV10SimpleHardware

**类型：** `hardware_interface::SystemInterface`

**命令接口：**
- `<joint_name>/position`
- `<joint_name>/velocity`
- `<joint_name>/effort`

**状态接口：**
- `<joint_name>/position`
- `<joint_name>/velocity`
- `<joint_name>/effort`

**URDF 配置：**
```xml
<ros2_control name="openarm_hardware_interface" type="system">
  <hardware>
    <plugin>openarm_hardware/OpenArmV10SimpleHardware</plugin>
    <param name="can_interface">can0</param>
    <param name="arm_side">right</param>
  </hardware>
  
  <joint name="openarm_joint1">
    <command_interface name="position"/>
    <command_interface name="velocity"/>
    <command_interface name="effort"/>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
    <state_interface name="effort"/>
  </joint>
  <!-- 其他关节... -->
</ros2_control>
```

---

## 坐标系定义

### 单臂坐标系

```
world (固定参考系)
  └─ openarm_link0 (机械臂基座)
      ├─ openarm_link1 (关节1旋转轴)
      │   └─ openarm_link2 (关节2旋转轴)
      │       └─ openarm_link3 (关节3旋转轴)
      │           └─ openarm_link4 (关节4旋转轴)
      │               └─ openarm_link5 (关节5旋转轴)
      │                   └─ openarm_link6 (关节6旋转轴)
      │                       └─ openarm_link7 (末端法兰)
      │                           └─ openarm_hand (夹爪, 可选)
```

### 双臂坐标系

```
world
  └─ openarm_body_link0 (机身基座)
      ├─ openarm_left_link0 (左臂基座)
      │   └─ openarm_left_link1
      │       └─ ... (7个关节)
      │           └─ openarm_left_hand
      │
      └─ openarm_right_link0 (右臂基座)
          └─ openarm_right_link1
              └─ ... (7个关节)
                  └─ openarm_right_hand
```

**坐标系约定：**
- **X 轴**：红色，指向前方
- **Y 轴**：绿色，指向左侧
- **Z 轴**：蓝色，指向上方
- **右手坐标系**

---

## Python API 示例

### 发送轨迹命令

```python
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class ArmController(Node):
    def __init__(self):
        super().__init__('arm_controller')
        self._action_client = ActionClient(
            self, FollowJointTrajectory, 
            '/joint_trajectory_controller/follow_joint_trajectory'
        )
    
    def send_goal(self, positions, duration_sec=2.0):
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory.joint_names = [
            'openarm_joint1', 'openarm_joint2', 'openarm_joint3',
            'openarm_joint4', 'openarm_joint5', 'openarm_joint6', 
            'openarm_joint7'
        ]
        
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start = Duration(sec=int(duration_sec))
        
        goal_msg.trajectory.points = [point]
        
        self._action_client.wait_for_server()
        return self._action_client.send_goal_async(goal_msg)

def main():
    rclpy.init()
    controller = ArmController()
    future = controller.send_goal([0.5, 0.3, 0.0, 0.8, 0.0, 0.0, 0.0])
    rclpy.spin_until_future_complete(controller, future)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## C++ API 示例

### 监听关节状态

```cpp
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>

class JointStateListener : public rclcpp::Node
{
public:
  JointStateListener() : Node("joint_state_listener")
  {
    subscription_ = this->create_subscription<sensor_msgs::msg::JointState>(
      "/joint_states", 10,
      [this](const sensor_msgs::msg::JointState::SharedPtr msg) {
        RCLCPP_INFO(this->get_logger(), "Received joint states:");
        for (size_t i = 0; i < msg->name.size(); ++i) {
          RCLCPP_INFO(this->get_logger(), "  %s: %.3f", 
            msg->name[i].c_str(), msg->position[i]);
        }
      });
  }

private:
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr subscription_;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<JointStateListener>());
  rclcpp::shutdown();
  return 0;
}
```

---

## 相关文档

- [架构设计文档](ARCHITECTURE.md)
- [开发指南](DEVELOPMENT_GUIDE.md)
- [快速开始](QUICK_START.md)

---

**文档维护**：请在添加新 API 或修改接口时更新本文档。
