#!/usr/bin/env python3
# Copyright (c) 2024 TOYOTA MOTOR CORPORATION
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted (subject to the limitations in the disclaimer
# below) provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the copyright holder nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS
# LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
# -*- coding: utf-8 -*-
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource

from tmc_launch_ros_utils.ros2_control import (
    create_spawner_node,
    set_on_process_exit_event_handler,
)
from tmc_launch_ros_utils.tmc_launch_ros_utils import load_robot_description


def declare_arguments():
    declared_arguments = []

    declared_arguments.append(DeclareLaunchArgument(
        'description_package',
        default_value='hsrb_description',
        description='Description package with robot URDF/xacro files.'))
    declared_arguments.append(DeclareLaunchArgument(
        'description_file',
        default_value='hsrb4s.urdf.xacro',
        description='URDF/XACRO description file with the robot.'))

    default_world_file = os.path.join(get_package_share_directory('hsrb_gazebo_bringup'), 'worlds', 'empty.sdf')
    declared_arguments.append(DeclareLaunchArgument(
        'world_file_name', default_value=default_world_file, description='Gazebo world file.'))

    declared_arguments.append(DeclareLaunchArgument(
        'robot_pos_x', default_value='0.0', description='Initial robot position x'))
    declared_arguments.append(DeclareLaunchArgument(
        'robot_pos_y', default_value='0.0', description='Initial robot position y'))
    declared_arguments.append(DeclareLaunchArgument(
        'robot_pos_z', default_value='0.0', description='Initial robot position z'))
    declared_arguments.append(DeclareLaunchArgument(
        'robot_rpy_Y', default_value='0.0', description='Initial robot orientation around z axis'))
    declared_arguments.append(DeclareLaunchArgument(
        'gazebo_visualization', default_value='True', description='Visualized laser'))

    declared_arguments.append(DeclareLaunchArgument(
        'robot_name', default_value='hsrb', description='Robot name'))
    declared_arguments.append(DeclareLaunchArgument(
        'start_gazebo', default_value='True',
        description='Launch gz sim. Set False to spawn the robot into a '
                    'world that is already running (e.g. guider).'))
    declared_arguments.append(DeclareLaunchArgument(
        'spawn_entity', default_value='True',
        description='False re-attaches to a gz entity that already exists '
                    '(e.g. guider parked it out of sight instead of '
                    'removing it) instead of spawning a new one. Skips '
                    'spwan_entity_node and starts the controller spawners '
                    'immediately instead of waiting on its exit.'))
    return declared_arguments


def _start_gazebo_enabled(context: LaunchContext, args: dict) -> bool:
    return context.perform_substitution(args['start_gazebo']).lower() in ('true', '1')


def _spawn_entity_enabled(context: LaunchContext, args: dict) -> bool:
    return context.perform_substitution(args['spawn_entity']).lower() in ('true', '1')


def gzsim_launch(context: LaunchContext, args: dict):
    if not _start_gazebo_enabled(context, args):
        return []
    world_file_name = context.perform_substitution(args['world_file_name'])
    launch_path = os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource([launch_path]),
                                     launch_arguments=[('gz_args', ' -r -v 3 ' + world_file_name)])]


def robot_state_publisher_node(context: LaunchContext, args: dict):
    robot_pos_x = float(context.perform_substitution(args['robot_pos_x']))
    robot_pos_y = float(context.perform_substitution(args['robot_pos_y']))
    robot_pos_z = float(context.perform_substitution(args['robot_pos_z']))
    robot_rpy_Y = float(context.perform_substitution(args['robot_rpy_Y']))
    gazebo_visualization_value = context.perform_substitution(args['gazebo_visualization'])
    ground_truth_xyz_offset = f'"{robot_pos_x} {robot_pos_y} {robot_pos_z}"'
    ground_truth_rpy_offset = f'"0.0 0.0 {robot_rpy_Y}"'

    robot_description = load_robot_description(
        xacro_arg=f'ignition_gazebo_sim:=True '
                  f'ground_truth_xyz_offset:={ground_truth_xyz_offset} '
                  f'ground_truth_rpy_offset:={ground_truth_rpy_offset} '
                  f'gazebo_visualization_enabled:={gazebo_visualization_value}')
    return [Node(package='robot_state_publisher',
                 executable='robot_state_publisher',
                 parameters=[robot_description, {'publish_frequency': 50.0}],
                 namespace='whole_body',
                 remappings=[('robot_description', '/robot_description')])]


def spwan_entity_node(context: LaunchContext, args: dict):
    if not _spawn_entity_enabled(context, args):
        # Re-attach path (see the spawn_entity argument above): the
        # entity already exists (parked, not removed), so creating a
        # second one -- which -allow_renaming would silently allow -- is
        # skipped. Everything else below still restarts fresh.
        return []
    return [Node(package='ros_gz_sim',
                 executable='create',
                 output='screen',
                 arguments=['-topic', '/robot_description',
                            '-name', context.perform_substitution(args['robot_name']),
                            '-allow_renaming', 'true',
                            '-x', args['robot_pos_x'],
                            '-y', args['robot_pos_y'],
                            '-z', args['robot_pos_z'],
                            '-Y', args['robot_rpy_Y']])]


def gz_parameter_bridge_node(context: LaunchContext, args: dict):
    robot_name_value = context.perform_substitution(args['robot_name'])
    start_gazebo = _start_gazebo_enabled(context, args)

    # “@” for bidirectional mode, “[” for one-way mode. Bidirectional mode often causes trouble and should be avoided as much as possible
    argument_list = []
    # When spawning into an already-running world (start_gazebo:=False) the
    # host launch already bridges /clock; a second bridge would put a
    # competing publisher on it, so only bridge the clock when we own gz sim.
    if start_gazebo:
        argument_list.append('/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock')
    argument_list += [
        f'/model/{robot_name_value}/odometry@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
        # Teleop: the guider Robot Manager panel (and any external tool)
        # publishes gz.msgs.Twist on the gz topic /<robot_name>/cmd_vel;
        # bridge it to HSRB's (global) omni base controller command topic.
        f'/{robot_name_value}/cmd_vel@geometry_msgs/msg/Twist[gz.msgs.Twist',
        '/base_range_sensor/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
        '/base_imu/data@sensor_msgs/msg/Imu[ignition.msgs.IMU',
        '/wrist_wrench/raw@geometry_msgs/msg/WrenchStamped[ignition.msgs.Wrench',
        '/hand_camera/image_rect_color@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/hand_camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        '/head_center_camera/image_rect_color@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/head_center_camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        '/head_l_stereo_camera/image_rect_color@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/head_l_stereo_camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        '/head_r_stereo_camera/image_rect_color@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/head_r_stereo_camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        '/head_rgbd_sensor/rgb/image_rect_color@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/head_rgbd_sensor/rgb/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
        '/head_rgbd_sensor/depth_registered/image@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/head_rgbd_sensor/depth_registered/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo'
    ]

    remapping_list = [
        (f'/{robot_name_value}/cmd_vel', '/omni_base_controller/cmd_vel'),
        ('/base_range_sensor/scan', '/scan'),
        ('/base_imu/data', '/imu/data'),
        ('/head_center_camera/image_rect_color', '/head_center_camera/image_raw'),
        ('/hand_camera/image_rect_color', '/hand_camera/image_raw'),
        (f'/model/{robot_name_value}/odometry', '/odom_ground_truth')
    ]

    return [Node(package='ros_gz_bridge',
                 executable='parameter_bridge',
                 output='screen',
                 arguments=argument_list,
                 remappings=remapping_list)]


def generate_launch_description():
    args = {}
    for arg in declare_arguments():
        args[arg.name] = LaunchConfiguration(arg.name)

    gz_sim = OpaqueFunction(function=gzsim_launch, args=[args])

    spawn_entity = OpaqueFunction(function=spwan_entity_node, args=[args])

    joint_state_publisher = Node(package='joint_state_publisher',
                                 executable='joint_state_publisher',
                                 parameters=[{'source_list': ['/joint_states']}, {'rate': 100}],
                                 namespace='whole_body',
                                 remappings=[('robot_description', '/robot_description')])
    robot_state_publisher = OpaqueFunction(function=robot_state_publisher_node, args=[args])

    bridge_node = OpaqueFunction(function=gz_parameter_bridge_node, args=[args])

    relay_node_launch_path = os.path.join(
        get_package_share_directory('hsrb_gazebo_bringup'), 'launch', 'hsrb_relay_topics.launch.xml')
    relay_node = IncludeLaunchDescription(XMLLaunchDescriptionSource([relay_node_launch_path]))

    sensor_frames_launch_path = os.path.join(
        get_package_share_directory('hsrb_gazebo_bringup'), 'launch', 'hsrb_sensor_frames.launch.xml')
    sensor_frames_node = IncludeLaunchDescription(XMLLaunchDescriptionSource([sensor_frames_launch_path]))

    odometry_switcher = Node(
        package='tmc_odometry_switcher',
        executable='odometry_switcher',
        name='odometry_switcher',
        parameters=[{'odom_topics': {'gt_odom': 'odom_ground_truth',
                                     'wheel_odom': 'omni_base_controller/wheel_odom'},
                     'initial_odom': 'gt_odom',
                     'odom_frame': 'odom',
                     'odom_child_frame': 'base_footprint'}],
        remappings=[('switched_odom', 'odom')])

    motion_command_limitter_controller_spawner = create_spawner_node('motion_command_limitter_controller')
    omni_base_controller_spawner = create_spawner_node('omni_base_controller')
    return LaunchDescription(declare_arguments() + [
        SetParameter(name='use_sim_time', value=True),
        gz_sim,
        spawn_entity,
        joint_state_publisher,
        robot_state_publisher,
        bridge_node,
        relay_node,
        sensor_frames_node,
        odometry_switcher,
        create_spawner_node('joint_state_broadcaster'),
        create_spawner_node('head_trajectory_controller'),
        create_spawner_node('arm_trajectory_controller'),
        motion_command_limitter_controller_spawner,
        set_on_process_exit_event_handler(motion_command_limitter_controller_spawner.actions[0],
                                          omni_base_controller_spawner.actions),
        create_spawner_node('gripper_controller')])
