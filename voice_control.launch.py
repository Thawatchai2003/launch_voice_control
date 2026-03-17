from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Launch args (SIM only)
    ur_type = LaunchConfiguration("ur_type")
    robot_ip = LaunchConfiguration("robot_ip")   # required by ur_robot_driver even in fake mode
    launch_rviz = LaunchConfiguration("launch_rviz")

    # ReSpeaker args
    enable_respeaker = LaunchConfiguration("enable_respeaker")
    respeaker_mic_mode = LaunchConfiguration("respeaker_mic_mode")
    respeaker_enable_graph = LaunchConfiguration("respeaker_enable_graph")

    declare_ur_type = DeclareLaunchArgument(
        "ur_type",
        default_value="ur5e"
    )

    declare_robot_ip = DeclareLaunchArgument(
        "robot_ip",
        default_value="192.168.1.200",
        description="Dummy IP for fake hardware mode (required by ur_robot_driver)"
    )

    declare_launch_rviz = DeclareLaunchArgument(
        "launch_rviz",
        default_value="true"
    )

    # IMPORTANT:
    # เปิด ReSpeaker เป็น default 
    declare_enable_respeaker = DeclareLaunchArgument(
        "enable_respeaker",
        default_value="true",
        description="Enable ReSpeaker mic array launch"
    )

    # IMPORTANT:
    # เครื่องคุณใช้ mode2
    declare_respeaker_mic_mode = DeclareLaunchArgument(
        "respeaker_mic_mode",
        default_value="mode2",
        description="ReSpeaker mic mode: mode1=ReSpeaker, mode2=auto scan"
    )

    # IMPORTANT:
    # เปิด graph เป็น default
    declare_respeaker_enable_graph = DeclareLaunchArgument(
        "respeaker_enable_graph",
        default_value="true",
        description="Enable ReSpeaker graph node"
    )

    # Controllers yaml
    controllers_file = PathJoinSubstitution([
        FindPackageShare("ur5_custom_description"),
        "config",
        "ur5e_with_gripper_controllers.yaml",
    ])

    # RViz config
    rviz_config = PathJoinSubstitution([
        FindPackageShare("ur5_custom_description"),
        "rviz",
        "ur5_with_gripper.rviz",
    ])

    # UR config files (SIM only)
    ur5e_cfg_dir = PathJoinSubstitution([
        FindPackageShare("ur5_custom_description"),
        "config",
        "ur5e",
    ])

    joint_limit_params = PathJoinSubstitution([ur5e_cfg_dir, "joint_limits.yaml"])
    physical_params = PathJoinSubstitution([ur5e_cfg_dir, "physical_parameters.yaml"])
    visual_params = PathJoinSubstitution([ur5e_cfg_dir, "visual_parameters.yaml"])
    kinematics_params = PathJoinSubstitution([ur5e_cfg_dir, "default_kinematics.yaml"])

    # UR driver (SIM / fake hardware only)
    ur_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("ur_robot_driver"),
                "launch",
                "ur_control.launch.py",
            ])
        ),
        launch_arguments={
            "ur_type": ur_type,
            "robot_ip": robot_ip,
            "use_fake_hardware": "true",
            "launch_rviz": launch_rviz,
            "initial_joint_controller": "joint_trajectory_controller",

            # Custom URDF
            "description_package": "ur5_custom_description",
            "description_file": "ur5e_with_gripper.urdf.xacro",

            # Custom controllers
            "controllers_file": controllers_file,

            # RViz config
            "rviz_config": rviz_config,

            # Config params
            "joint_limit_params": joint_limit_params,
            "kinematics_params": kinematics_params,
            "physical_params": physical_params,
            "visual_params": visual_params,
        }.items(),
    )

    # ReSpeaker mic array
    respeaker_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("respeaker_mic_array"),
                "launch",
                "respeaker.launch.py",
            ])
        ),
        launch_arguments={
            "mic_mode": respeaker_mic_mode,
            "enable_graph": respeaker_enable_graph,
        }.items(),
        condition=IfCondition(enable_respeaker),
    )

    # MoveIt (SIM only)
    moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("ur_moveit_config"),
                "launch",
                "ur_moveit.launch.py",
            ])
        ),
        launch_arguments={
            "ur_type": ur_type,
            "use_fake_hardware": "true",
            "launch_rviz": "false",
        }.items(),
    )

    # Spawn only gripper controller (SIM only)
    gripper_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    auto_spawn_gripper = TimerAction(
        period=3.5,
        actions=[gripper_spawner]
    )

    # Voice stack nodes
    beep = Node(
        package="ur5e_voice_control",
        executable="beep_node",
        name="beep_node",
        output="screen",
    )

    tts = Node(
        package="ur5e_voice_control",
        executable="tts_node_gtts",
        name="tts_node_gtts",
        output="screen",
    )

    stt = Node(
        package="ur5e_voice_control",
        executable="speech_to_text_node",
        name="speech_to_text_node",
        output="screen",
        parameters=[{
            "debug_print_heard": False,
            "idle_recognize_interval_sec": 0.6,
            "post_tts_ignore_sec": 0.8,
            "tts_resume_delay_sec": 0.8,
        }],
    )

    fsm = Node(
        package="ur5e_voice_control",
        executable="dialog_fsm_node",
        name="dialog_fsm_node",
        output="screen",
        parameters=[{
            "wake_words": ["สวัสดี", "Hello"],
            "wake_timeout_sec": 6.0,
            "wake_cooldown_ms": 1200,
            "post_command_ignore_sec": 1.0,
            "tts_resume_delay_sec": 1.0,
            "dialog_max_retry": 2,
            "debug_heard_when_active": True,
            "beep_enabled": True,
        }],
    )

    gui = Node(
        package="ur5e_voice_control",
        executable="speech_gui_node",
        name="speech_gui_node",
        output="screen",
    )

    nlu = Node(
        package="ur5e_voice_control",
        executable="nlu_parser_node",
        name="nlu_parser_node",
        output="screen",
    )

    logger = Node(
        package="ur5e_voice_control",
        executable="voice_logger_node",
        name="voice_logger_node",
        output="screen",
    )

    # Gripper bridge (SIM only)
    gripper_bridge = Node(
        package="ur5e_voice_control",
        executable="gripper_bridge_node",
        name="gripper_bridge_node",
        output="screen",
        parameters=[{
            "mode": "sim",
            "cmd_topic": "/Neural_parser/cmd_group",
            "sim_topic": "/gripper_controller/commands",
            "sim_open": 0.0,
            "sim_close": 0.01,
        }],
    )

    # Robot command nodes (SIM only)
    mapper_sim = Node(
        package="ur5e_voice_control",
        executable="ur5_cmd_mapper_node",
        name="ur5_cmd_mapper_node",
        output="screen",
        parameters=[{
            "mode": "high_level",
            "debug": True,
            "traj_topic": "/joint_trajectory_controller/joint_trajectory",
            "step_xyz_m": 0.03,
            "rotate_step_deg": 15.0,
            "traj_time_s": 1.0,
            "max_deg": 180.0,
            "max_step_m": 0.20,
        }],
    )

    control_position_node = Node(
        package="ur5e_voice_control",
        executable="control_position_node",
        name="control_position_node",
        output="screen",
    )

    executor_sim = Node(
        package="ur5e_voice_control",
        executable="ur5_executor_node",
        name="ur5_executor_node",
        output="screen",
        remappings=[
            ("/ur5/command_trajectory", "/joint_trajectory_controller/joint_trajectory"),
        ],
    )

    # Logical pick object (SIM only)
    logical_pick_object_node = Node(
        package="ur5_workcell_scene",
        executable="logical_pick_object_node",
        name="logical_pick_object_node",
        output="screen",
        parameters=[{
            "world_frame": "world",
            "gripper_frame": "tool0",
        }],
    )

    delayed_logical_pick_object = TimerAction(
        period=4.0,
        actions=[logical_pick_object_node],
    )

    # Delay robot command nodes
    delayed_robot_nodes = TimerAction(
        period=6.0,
        actions=[
            mapper_sim,
            executor_sim,
        ],
    )

    # Force monitor (SIM only)
    force_monitor_sim = Node(
        package="ur5_force_tools",
        executable="force_gui",
        name="ur5_force_gui_sim",
        output="screen",
    )

    # Final launch list
    return LaunchDescription([
        declare_ur_type,
        declare_robot_ip,
        declare_launch_rviz,

        declare_enable_respeaker,
        declare_respeaker_mic_mode,
        declare_respeaker_enable_graph,

        ur_driver,
        moveit_launch,
        respeaker_launch,

        auto_spawn_gripper,

        # voice stack
        stt,
        beep,
        tts,
        fsm,
        gui,
        nlu,
        logger,
        gripper_bridge,

        # force monitor
        # force_monitor_sim,

        # control helper
        control_position_node,

        # logical object
        delayed_logical_pick_object,

        # motion nodes
        delayed_robot_nodes,
    ])
