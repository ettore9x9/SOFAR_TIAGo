# Author: Addison Sears-Collins
# Edited by: Pagano, Predieri, Sani
# Date: June 22, 2022
# ROS Version: ROS 2 Foxy Fitzroy Galactic
 
### IMPORT LIBRARIES ###

# Python math library
import math 
 
# ROS client library for Python
import rclpy 
 
# Enables pauses in the execution of code
from time import sleep 
 
# Used to create nodes
from rclpy.node import Node
 
# Enables the use of the string message type
from std_msgs.msg import String 
 
# Twist is linear and angular velocity
from geometry_msgs.msg import Twist     
                     
# Handles LaserScan messages to sense distance to obstacles (i.e. walls)        
from sensor_msgs.msg import LaserScan    
 
# Handle Pose messages
from geometry_msgs.msg import Pose 
 
# Handle float64 arrays
from std_msgs.msg import Float64MultiArray
                     
# Handles quality of service for LaserScan data
from rclpy.qos import qos_profile_sensor_data 
 
# Scientific computing library
import numpy as np

from geometry_msgs.msg import Point
from interfaces.srv import SendPoint
from interfaces.srv import ProcessPoint
 
class Controller(Node):
  """
  Create a Controller class, which is a subclass of the Node 
  class for ROS2.
  """
  def __init__(self):
    """
    Class constructor to set up the node
    """

    ### ROS SETUP ###
    # Initiate the Node class's constructor and give it a name

    super().__init__('Controller')
 
    # Create a subscriber
    # This node subscribes to messages of type 
    # sensor_msgs/LaserScan     
    self.scan_subscriber = self.create_subscription(
                           LaserScan,
                           '/scan',
                           self.scan_callback,
                           10)
                            
    # Create a publisher
    # This node publishes the linear and angular velocity of the robot.
    self.publisher_ = self.create_publisher(
                      Twist, 
                      '/cmd_vel', 
                      10)

    # Desired linear and angular velocities for centroid tracking
    self.vel_x = 0.0
    self.vel_z = 0.0

    # Initialize the LaserScan sensor readings to some large value
    # Values are in meters.
    self.max_distance = 5.0
    self.front_dist = self.max_distance

    # Create a server to the centroid service, to process the client (depth_finder.py) request.
    # composed of the centroid position and depth.
    self.srv = self.create_service(SendPoint, 'centroid', self.receive_point_callback)

    # This value will be the request value to bee processed in the des_vel server.
    self.pid_request = ProcessPoint.Request()

    # Create a client to the des_vel service, to send the centroid position and depth to the 
    # pid_controller node.
    self.cli = self.create_client(ProcessPoint, 'des_vel')

    # Waiting for the service to be availabe
    while not self.cli.wait_for_service(timeout_sec=1.0):
      self.get_logger().info('Service not available, waiting again...')

    self.data_received = 0

    ### OBSTALCE AVOIDANCE PARAMETERS ### 
 
    # Distance threshold.
    # We want to try to keep within this distance from the wall.
    self.dist_thresh_wf = 1.1 # meters

    # Calling the collision_avoidance() method.
    self.collision_avoidance()


  def receive_point_callback(self, req, res):
    """
    This method receives the request message from the depth_finder node 
    and send a true value as response every time a request is correctly received.
    """
    self.get_logger().info('Received centroid')
    self.pid_request.centroid = req.centroid
    self.data_received = 1
    res.check = True
    return res

  def scan_callback(self, msg):
    """
    This method gets called every time a LaserScan message is 
    received and updates the frontal distance. 
    """
    self.get_logger().info('Received laserscan')
    self.front_dist = min(msg.ranges[260:400])
   
  def collision_avoidance(self):
    """
    This method receives the pid generated velocities for the target tracking 
    and causes the robot to stop if a frontal obstacle is detected.
    """

    # Create a geometry_msgs/Twist message
    msg = Twist()

    while rclpy.ok():
      rclpy.spin_once(self)

      if self.data_received == 1:

        # Send a client request with the centroid's coordinates and depth.
        self.future = self.cli.call_async(self.pid_request)

        # Wait until a response from pid_controller node is received. 
        rclpy.spin_until_future_complete(self, self.future)
        self.get_logger().info('Received pid controller response')

        # These are the linear and angular velocities generated by the pid controllers.
        res = self.future.result()
        self.vel_x = res.desired_velocities.linear.x
        self.vel_z = res.desired_velocities.angular.z

      else:
        # If no centroid is received from the centroid service, the 80% of the previous velocities are published.
        self.vel_x = 0.8 * self.vel_x
        self.vel_z = 0.8 * self.vel_z

      # Logic:
      # >d means no wall detected by the laser beam
      # <d means an wall was detected by the laser beam
      d = self.dist_thresh_wf

      # Only data front laser scan data are evaluated so as to avoid losing sight of the centroid.

      if self.front_dist > d:     # No obstacles detected in front of the robot.
        self.wall_following_state = "1: No obstacles detected"
        msg.linear.x = self.vel_x
        msg.angular.z = self.vel_z

      else:                       # Obstacles detected in front of the robot. 
        self.wall_following_state = "2: Obstacles detected at " + str(round(self.front_dist, 3)) + " meters in front of the robot."
        msg.linear.x = 0.0            # stops the robot.
        msg.angular.z = self.vel_z    # only anglular velocities are allowed.
  
      # Send velocity command to the robot.
      self.publisher_.publish(msg)

      self.data_received = 0
    
      # Print robot state information in terminal.
      self.get_logger().info('State: "%s"' % self.wall_following_state)

def main(args=None):
 
    # Initialize rclpy library
    rclpy.init(args=args)
     
    # Create the node
    controller = Controller()
 
    # Spin the node so the callback function is called
    # Pull messages from any topics this node is subscribed to
    # Publish any pending messages to the topics
    rclpy.spin(controller)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    controller.destroy_node()
     
    # Shutdown the ROS client library for Python
    rclpy.shutdown()
 
if __name__ == '__main__':
    main()
