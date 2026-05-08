#include <memory>
#include <thread>

#include <rclcpp/rclcpp.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit_visual_tools/moveit_visual_tools.h>

int main(int argc, char * argv[])
{
  // Initialize ROS and create the Node
  rclcpp::init(argc, argv);
  auto const node = std::make_shared<rclcpp::Node>(
    "hello_moveit",
    rclcpp::NodeOptions().automatically_declare_parameters_from_overrides(true)
  );

  // Create a ROS logger
  auto const logger = rclcpp::get_logger("hello_moveit");

  // Spin in background so MoveIt subscriptions (joint_states, etc.) can update.
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::thread spinner([&executor]() { executor.spin(); });

  // Create the MoveIt MoveGroup Interface
  using moveit::planning_interface::MoveGroupInterface;
  auto move_group_interface = MoveGroupInterface(node, "left_arm");
  // 
  auto const planning_frame = move_group_interface.getPlanningFrame();
  RCLCPP_INFO(logger, "Planning frame: %s", planning_frame.c_str());
  RCLCPP_INFO(
    logger, "Pose reference frame: %s", move_group_interface.getPoseReferenceFrame().c_str());
  move_group_interface.setPoseReferenceFrame(planning_frame);
  move_group_interface.startStateMonitor(2.0);

  auto ee_link = move_group_interface.getEndEffectorLink();
  if (ee_link.empty()) {
    ee_link = "openarm_left_hand_tcp";
    if (!move_group_interface.getRobotModel()->hasLinkModel(ee_link)) {
      ee_link = "openarm_left_hand";
    }
    move_group_interface.setEndEffectorLink(ee_link);
  }
  RCLCPP_INFO(logger, "Using end effector link: %s", ee_link.c_str());

  // Construct and initialize MoveItVisualTools
  auto moveit_visual_tools = moveit_visual_tools::MoveItVisualTools{
      node, planning_frame, rviz_visual_tools::RVIZ_MARKER_TOPIC,
      move_group_interface.getRobotModel()};
  moveit_visual_tools.deleteAllMarkers();
  moveit_visual_tools.loadRemoteControl();

  auto current_state = move_group_interface.getCurrentState(2.0);
  if (!current_state) {
    RCLCPP_ERROR(logger, "Failed to get current robot state from /joint_states.");
    executor.cancel();
    if (spinner.joinable()) {
      spinner.join();
    }
    rclcpp::shutdown();
    return 1;
  }

  // Create a closures for visualization
  auto const draw_title = [&moveit_visual_tools](auto text) {
    auto const text_pose = [] {
      auto msg = Eigen::Isometry3d::Identity();
      msg.translation().z() = 1.0;
      return msg;
    }();
    moveit_visual_tools.publishText(text_pose, text, rviz_visual_tools::WHITE,
                                    rviz_visual_tools::XLARGE);
  };
  auto const prompt = [&moveit_visual_tools](auto text) {
    moveit_visual_tools.prompt(text);
  };
  auto const draw_trajectory_tool_path =
      [&moveit_visual_tools,
      robot_model = move_group_interface.getRobotModel(),
      jmg = move_group_interface.getRobotModel()->getJointModelGroup("left_arm"),
      ee_link](auto const trajectory) {
        const moveit::core::LinkModel* ee_link_model = robot_model->getLinkModel(ee_link);
        if (ee_link_model) {
          moveit_visual_tools.publishTrajectoryLine(trajectory, ee_link_model, jmg);
        } else {
          moveit_visual_tools.publishTrajectoryLine(trajectory, jmg);
        }
      };

  // Use current pose as a seed, then apply a small reachable offset
  auto current_pose_stamped = move_group_interface.getCurrentPose(ee_link);
  // 打印当前位置
  RCLCPP_INFO(
    logger,
    "Current pose in frame [%s]: pos=[%.6f, %.6f, %.6f], quat(xyzw)=[%.6f, %.6f, %.6f, %.6f]",
    current_pose_stamped.header.frame_id.c_str(),
    current_pose_stamped.pose.position.x,
    current_pose_stamped.pose.position.y,
    current_pose_stamped.pose.position.z,
    current_pose_stamped.pose.orientation.x,
    current_pose_stamped.pose.orientation.y,
    current_pose_stamped.pose.orientation.z,
    current_pose_stamped.pose.orientation.w);
  auto target_pose = current_pose_stamped.pose;
  
  target_pose.position.z += 0.05;  // small upward offset in planning frame
  move_group_interface.setStartStateToCurrentState();
  move_group_interface.setPoseTarget(target_pose, ee_link);

  // Create a plan to that target pose
  prompt("Press 'Next' in the RvizVisualToolsGui window to plan");
  draw_title("Planning");
  moveit_visual_tools.trigger();
  auto const [success, plan] = [&move_group_interface] {
    moveit::planning_interface::MoveGroupInterface::Plan msg;
    auto const ok = static_cast<bool>(move_group_interface.plan(msg));
    return std::make_pair(ok, msg);
  }();

  // Execute the plan
  if (success) {
    draw_trajectory_tool_path(plan.trajectory_);
    moveit_visual_tools.trigger();
    prompt("Press 'Next' in the RvizVisualToolsGui window to execute");
    draw_title("Executing");
    moveit_visual_tools.trigger();
    move_group_interface.execute(plan);
    move_group_interface.clearPoseTargets();
  } else {
    draw_title("Planning Failed!");
    moveit_visual_tools.trigger();
    RCLCPP_ERROR(logger, "Planing failed!");
  }
#if 0
  // Create a plan to that target pose
  auto const [success, plan] = [&move_group_interface]{
    moveit::planning_interface::MoveGroupInterface::Plan msg;
    auto const ok = static_cast<bool>(move_group_interface.plan(msg));
    return std::make_pair(ok, msg);
  }();

  // Execute the plan
  if(success) {
    move_group_interface.execute(plan);
  } else {
    RCLCPP_ERROR(logger, "Planing failed!");
  }
#endif
  executor.cancel();
  if (spinner.joinable()) {
    spinner.join();
  }

  // Shutdown ROS
  rclcpp::shutdown();
  return 0;
}
