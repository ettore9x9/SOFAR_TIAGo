import rclpy # Python library for ROS 2
from simple_pid import PID
import time
import numpy as np
from rclpy.node import Node # Handles the creation of nodes
from geometry_msgs.msg import Point, Twist
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

class Controller(Node):

  def __init__(self):
    """
    Class constructor to set up the node
    """
    # Initiate the Node class's constructor and give it a name
    super().__init__('controller')

    self.data_received = 0
    self.x = 0
    self.y = 0
    self.depth = 0

    self.sub_control_input = self.create_subscription(
      Point, 
      '/TIAGo_Iron/control_msgs', 
      self.control_cb, 
      10)


    self.cmd_vel_publisher = self.create_publisher(Twist, "des_cmd_vel", 1)
    self.cmd_vel_joint_publisher = self.create_publisher(JointTrajectory, "/joint_trajectory_controller/joint_trajectory", 1)


    self.timer = self.create_timer(0.01, self.publisher_cmd)

    self.pid_distance = PID(-1, 0, -2, setpoint=2)

    self.pid_orientation = PID(0.004, 0, 0.008, setpoint=320)

    self.pid_y_rotation = PID(0.004, 0, 0.008, setpoint=240)

    self.msg = Twist()

    self.msg_joint = JointTrajectory()
    self.msg_joint.joint_names = ["head_2_joint"]

    self.traj_points = JointTrajectoryPoint()
    #self.traj_points.positions = [3.14/2]
    self.traj_points.time_from_start.sec = 0

    
  def control_cb(self, data):
    """
    Callback function.
    """
    self.data_received = 1
    self.x = data.x
    self.y = data.y
    self.depth = data.z


  def publisher_cmd(self):

    if self.data_received == 1:

      self.msg.linear.x = float(self.pid_distance(self.depth))
      self.msg.angular.z = float(self.pid_orientation(self.x))


      self.traj_points.velocities = [float(self.pid_y_rotation(self.y))]

      self.msg_joint.points = [self.traj_points]

      print("aaaaaaa         " + str(self.traj_points.velocities))

      self.data_received = 0

    else:
      self.msg.linear.x = self.msg.linear.x * 0.8
      self.msg.angular.z = self.msg.angular.z * 0.8

    self.cmd_vel_publisher.publish(self.msg)
    self.cmd_vel_joint_publisher.publish(self.msg_joint)

    self.get_logger().info('Control y Error [' + str(self.y - 240) +  ' [px]')
    self.get_logger().info('Control Errors [' + str(self.x - 320) +  ' [px], ' + str(round(self.depth - 2, 4)) + ' [m] ]')
    

def main(args=None):
  
  # Initialize the rclpy library
  rclpy.init(args=args)
  
  # Create the node
  controller = Controller()
  
  # Spin the node so the callback function is called.
  rclpy.spin(controller)
  
  # Destroy the node explicitly
  # (optional - otherwise it will be done automatically
  # when the garbage collector destroys the node object)
  controller.destroy_node()
  
  # Shutdown the ROS client library for Python
  rclpy.shutdown()

if __name__ == '__main__':
    main()