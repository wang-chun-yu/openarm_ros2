#!/usr/bin/env python3
import sys
from typing import Dict, List

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from moveit_msgs.srv import GetPositionFK


LEFT_ARM_JOINTS: List[str] = [
    "openarm_left_joint1",
    "openarm_left_joint2",
    "openarm_left_joint3",
    "openarm_left_joint4",
    "openarm_left_joint5",
    "openarm_left_joint6",
    "openarm_left_joint7",
]

BASE_FRAME = "world"
EEF_LINK = "openarm_left_hand_tcp"


class FkClient(Node):
    def __init__(self) -> None:
        super().__init__("openarm_left_fk")
        self._joint_map: Dict[str, float] = {}
        self._joint_sub = self.create_subscription(
            JointState, "/joint_states", self._on_joint_state, 10
        )
        self._fk_client = self.create_client(GetPositionFK, "/compute_fk")

    def _on_joint_state(self, msg: JointState) -> None:
        for name, position in zip(msg.name, msg.position):
            self._joint_map[name] = position

    def _have_all_joints(self) -> bool:
        return all(j in self._joint_map for j in LEFT_ARM_JOINTS)

    def _build_request(self) -> GetPositionFK.Request:
        req = GetPositionFK.Request()
        req.header.frame_id = BASE_FRAME
        req.fk_link_names = [EEF_LINK]
        req.robot_state.joint_state.name = list(LEFT_ARM_JOINTS)
        req.robot_state.joint_state.position = [self._joint_map[j] for j in LEFT_ARM_JOINTS]
        return req

    def run(self, timeout_sec: float = 5.0) -> int:
        if not self._fk_client.wait_for_service(timeout_sec=timeout_sec):
            self.get_logger().error("Service /compute_fk not available.")
            return 1

        self.get_logger().info("Waiting for joint_states...")
        start = self.get_clock().now()
        while rclpy.ok() and not self._have_all_joints():
            rclpy.spin_once(self, timeout_sec=0.1)
            if (self.get_clock().now() - start).nanoseconds > int(5e9):
                self.get_logger().error("Timed out waiting for all left arm joints.")
                return 1

        req = self._build_request()
        future = self._fk_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if not future.done() or future.result() is None:
            self.get_logger().error("FK service call failed.")
            return 1

        res = future.result()
        if res.error_code.val != res.error_code.SUCCESS:
            self.get_logger().error(f"FK failed, error code: {res.error_code.val}")
            return 1

        pose = res.pose_stamped[0].pose
        self.get_logger().info(
            "EE pose in %s:\n  position: [%.6f, %.6f, %.6f]\n  orientation: [%.6f, %.6f, %.6f, %.6f]"
            % (
                BASE_FRAME,
                pose.position.x,
                pose.position.y,
                pose.position.z,
                pose.orientation.x,
                pose.orientation.y,
                pose.orientation.z,
                pose.orientation.w,
            )
        )
        return 0


def main() -> None:
    rclpy.init()
    node = FkClient()
    try:
        rc = node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(rc)


if __name__ == "__main__":
    main()
