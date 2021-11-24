#!/usr/bin/env python

import sys
import yaml
import rospy
from control_msgs.msg import FollowJointTrajectoryAction
from control_msgs.msg import FollowJointTrajectoryFeedback
from control_msgs.msg import FollowJointTrajectoryResult
import actionlib
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from dynamixel_workbench_msgs.msg import DynamixelStateList

class DynamixelJointTrajectoryServer():
    _feedback = FollowJointTrajectoryFeedback()
    _result = FollowJointTrajectoryResult()
    _namespace = None
    _conf_file = None
    _joint_names = None

    def __init__(self, ns, conf):
        self._namespace = ns
        self._conf_file = conf
        rospy.init_node(ns + '_server', anonymous=True)
        self.r = rospy.Rate(100)
        self.server = actionlib.SimpleActionServer('/' + ns + '/follow_joint_trajectory_action', FollowJointTrajectoryAction, self.execute, False)
        self.server.start()
        self.joint_command_pub = rospy.Publisher('/' + ns + '/joint_trajectory', JointTrajectory, queue_size=2)
        self.dynamixel_state_sub = rospy.Subscriber('/' + ns + '/dynamixel_state', DynamixelStateList, self.state_callback)
        self.interpolatingp = False
        with open(conf) as f:
            yml = yaml.load(f)
            self._joint_names = yml.keys()

    def execute(self, goal):
        success = True
        pub_msg = JointTrajectory()
        pub_msg.header = goal.trajectory.header
        pub_msg.joint_names = self._joint_names
        hand_thumb_roll_id = goal.trajectory.joint_names.index(self._joint_names[0])
        hand_1st_inner_id = goal.trajectory.joint_names.index(self._joint_names[1])
        hand_1st_outer_id = goal.trajectory.joint_names.index(self._joint_names[2])
        hand_2nd_id = goal.trajectory.joint_names.index(self._joint_names[3])
        hand_2nd_inner_id = goal.trajectory.joint_names.index(self._joint_names[4])
        hand_2nd_outer_id = goal.trajectory.joint_names.index(self._joint_names[5])
        hand_45_id = goal.trajectory.joint_names.index(self._joint_names[6])
        pub_msg.points = []
        wait_time = 0.0
        for p in goal.trajectory.points:
            point = JointTrajectoryPoint()
            point.positions = [
                    p.positions[hand_thumb_roll_id],
                    p.positions[hand_1st_inner_id],
                    p.positions[hand_1st_outer_id],
                    p.positions[hand_2nd_id],
                    p.positions[hand_2nd_inner_id],
                    p.positions[hand_2nd_outer_id],
                    p.positions[hand_45_id]]
            point.velocities = [
                    p.velocities[hand_thumb_roll_id],
                    p.velocities[hand_1st_inner_id],
                    p.velocities[hand_2nd_outer_id],
                    p.velocities[hand_2nd_id],
                    p.velocities[hand_2nd_inner_id],
                    p.velocities[hand_2nd_outer_id],
                    p.velocities[hand_45_id]]

            point.time_from_start = p.time_from_start
            pub_msg.points.append(point)
            wait_time = p.time_from_start.to_sec()
        start_time = rospy.get_rostime()
        self.joint_command_pub.publish(pub_msg)
        while True:
            now = rospy.get_rostime()
            if self.server.is_preempt_requested():
                rospy.loginfo('%s: Preempted' % "Hand")
                self.server.set_preempted()
                success = False
                break
            if ((now - start_time).to_sec() > wait_time) and (not self.interpolatingp):
                break
            self.r.sleep()

        if success:
            self._result.error_code = FollowJointTrajectoryResult.SUCCESSFUL
            self.server.set_succeeded(self._result)

    def state_callback(self, msg):
        if msg.dynamixel_state == []:
            self.interpolatingp = True
        else:
            self.interpolatingp = False

if __name__ == '__main__':
    args = sys.argv
    namespace = args[1]
    conf_file = args[2]

    try:
        s = DynamixelJointTrajectoryServer(namespace, conf_file)
        rospy.spin()
    except rospy.ROSInterruptException: pass
