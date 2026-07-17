<a name="readme-top"></a>

# HSRB Simulator (ROS 2 Jazzy / Gazebo Sim)

<!--目次-->
<details>
   <summary>目次</summary>
   <ol>
    <li>
      <a href="#概要">概要</a>
    </li>
    <li>
      <a href="#セットアップ">セットアップ</a>
      <ul>
        <li><a href="#環境条件">環境条件</a></li>
        <li><a href="#インストール方法">インストール方法</a></li>
      </ul>
    </li>
    <li>
    <a href="#実行・操作方法">実行・操作方法</a>
      <ul>
        <li><a href="#シミュレータを起動">シミュレータを起動</a></li>
        <li><a href="#台車を動かす">台車を動かす</a></li>
        <li><a href="#アーム・首を動かす">アーム・首を動かす</a></li>
        <li><a href="#グリッパーを操作">グリッパーを操作</a></li>
        <li><a href="#センサーを確認">センサーを確認</a></li>
      </ul>
    </li>
    <li>
    <a href="#パッチの管理">パッチの管理</a>
      <ul>
        <li><a href="#パッチの内訳">パッチの内訳</a></li>
        <li><a href="#パッチの更新方法">パッチの更新方法</a></li>
      </ul>
    </li>
    <li><a href="#対応インターフェース">対応インターフェース</a></li>
    <li><a href="#ファイル構成">ファイル構成</a></li>
    <li><a href="#マイルストーン">マイルストーン</a></li>
    <li><a href="#参考文献">参考文献</a></li>
   </ol>
</details>


<!--レポジトリの概要-->
## 概要

トヨタHSR（HSRB）をROS 2 Jazzy＋Gazebo Sim 8で動かすためのシミュレータパッケージ．
[hsr-project公式のhsrb_simulator（jazzyブランチ）](https://github.com/hsr-project/hsrb_simulator)をベースに，
Jazzy／Gazebo Harmonic世代のAPIでパッチ一式と，
依存リポジトリの取得からビルドまでを自動化する`install.sh`を追加している．

現在は以下の機能が動作確認済み．

- 公式オムニ台車コントローラによる全方向移動（前後・**真横**・旋回）
- アーム5関節・首2関節のJointTrajectoryController制御
- グリッパーの開閉（開き幅指定）
- センサー一式のROS 2ブリッジ（LiDAR，IMU，頭部RGB-D／ステレオ／広角カメラ，手部カメラ，手首力覚）
- ground truth odomと車輪odomの切り替え（`tmc_odometry_switcher`）

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- セットアップ -->
## セットアップ

ここで，本パッケージのセットアップ方法について説明します．

### 環境条件

まず，以下の環境を整えてから，次のインストール段階に進んでください．

| System | Version |
| ------------- | ------------- |
| Ubuntu | 24.04 (Noble Numbat) |
| ROS | Jazzy |
| Gazebo | Gazebo Sim 8系 |

> [!NOTE]
> `Ubuntu`や`ROS`のインストール方法に関しては，[SOBIT Manual](https://github.com/TeamSOBITS/sobits_manual#%E9%96%8B%E7%99%BA%E7%92%B0%E5%A2%83%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)を参照してください．

### インストール方法

1. ROSの`src`フォルダに移動します．
   ```sh
   $ cd ~/colcon_ws/src/
   ```
2. 本レポジトリを`hsrb_simulator`という名前でこのフォルダにcloneします．
3. レポジトリのフォルダへ移動します．
   ```sh
   $ cd hsrb_simulator/
   ```
4. 依存パッケージをインストールします．
   ```sh
   $ bash install.sh
   ```
5. パッケージをコンパイルします．
   ```sh
   $ cd ~/colcon_ws/
   $ colcon build --symlink-install
   $ source ~/colcon_ws/install/setup.bash
   ```

`install.sh`は次の3工程を自動で行います（ビルドは行いません）．
全工程は冪等なので，途中で失敗しても再実行できます．

| 工程 | 内容 |
| --- | --- |
| clone | hsr-projectの依存リポジトリ（jazzyブランチ）を`src/`へ取得 |
| 重複解決＋パッチ適用 | `hsrb_description`の重複をCOLCON_IGNOREで解決し，`patches/*.patch`をJazzy／Harmonic対応として各リポジトリに適用 |
| rosdep | 依存パッケージのインストール |

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- 実行・操作方法 -->
## 実行・操作方法

### シミュレータを起動

```sh
$ ros2 launch hsrb_gazebo_bringup hsrb_gazebo_bringup.launch.py
```

Gazeboが起動し，HSRBがspawnされ，コントローラ6基（オムニ台車・アーム・首・
グリッパー・速度リミッタ・joint_state_broadcaster）が自動で立ち上がります．

主な起動引数は以下の通りです．

| 引数 | デフォルト | 説明 |
| --- | --- | --- |
| `world_file_name` | 同梱の`worlds/empty.sdf` | Gazeboのworldファイル |
| `robot_pos_x` / `robot_pos_y` / `robot_pos_z` | `0.0` | spawn座標 |
| `robot_rpy_Y` | `0.0` | spawn時のyaw |
| `robot_name` | `hsrb` | Gazebo上のモデル名 |

> [!IMPORTANT]
> 独自のworldを使う場合，worldに`gz::sim::systems::Sensors`・`Imu`・`ForceTorque`の
> 3プラグインが入っていないと，センサーのトピックは存在するのにデータが一切流れません．
> 同梱の`empty.sdf`は対応済みです（<a href="#パッチの内訳">パッチの内訳</a>参照）．

### 台車を動かす

オムニ台車なので，前後（`linear.x`）・**真横（`linear.y`）**・旋回（`angular.z`）が全て使えます．

```sh
$ ros2 topic pub -r 10 /omni_base_controller/cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.3, y: 0.0}, angular: {z: 0.0}}"
```

### アーム・首を動かす

```sh
$ ros2 topic pub --once /arm_trajectory_controller/joint_trajectory \
    trajectory_msgs/msg/JointTrajectory \
    "{joint_names: [arm_lift_joint, arm_flex_joint, arm_roll_joint, wrist_flex_joint, wrist_roll_joint],
      points: [{positions: [0.3, -0.8, 0.0, -0.5, 0.0], time_from_start: {sec: 3}}]}"

$ ros2 topic pub --once /head_trajectory_controller/joint_trajectory \
    trajectory_msgs/msg/JointTrajectory \
    "{joint_names: [head_pan_joint, head_tilt_joint],
      points: [{positions: [0.6, -0.3], time_from_start: {sec: 2}}]}"
```

### グリッパーを操作

開き幅[m]を指定します．

```sh
$ ros2 topic pub --once /gripper_controller/command_distance std_msgs/msg/Float32 "{data: 0.8}"  # 開く
$ ros2 topic pub --once /gripper_controller/command_distance std_msgs/msg/Float32 "{data: 0.0}"  # 閉じる
```

### センサーを確認

```sh
$ ros2 topic hz /scan                                      # LiDAR (~30Hz)
$ ros2 topic hz /imu/data                                  # IMU (~100Hz)
$ ros2 topic hz /head_rgbd_sensor/rgb/image_rect_color     # RGB-D (~30Hz)
$ ros2 topic hz /wrist_wrench/raw                          # 手首力覚 (~30Hz)
```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- パッチの管理 -->
## パッチの管理

上流（hsr-project）のコードはHumble世代のAPIで書かれている箇所があるため，
Jazzy／Gazebo Harmonicで動かすための修正を`patches/`以下にgit diff形式で管理しています．
`install.sh`が各リポジトリへ自動適用します（適用済みならスキップ，上流更新と競合したら
ファイルを壊さずエラー停止）．

### パッチの内訳

| パッチ | 対象 | 内容 |
| --- | --- | --- |
| `hsrb_simulator.patch` | 本レポジトリ | gz vendorパッケージ化，gz_ros2_control Jazzy API対応，コントローラ設定のtimeout調整，worldへのセンサーシステム追加 |
| `tmc_realtime_control.patch` | tmc_realtime_control | 旧3引数`init()`の`on_init()`移行，chainable controller API対応，旧APIテストの無効化（`-DTMC_REALTIME_CONTROLLERS_ENABLE_TESTS=ON`で復活） |
| `tmc_navigation.patch` | tmc_navigation | tf2／PCLヘッダ改名対応，重複environment hook削除，テストの`ament_index_cpp`依存宣言追加（9パッケージ） |
| `tmc_gazebo.patch` | tmc_gazebo | `odometry_publisher`のignition→gz名前空間移植 |
| `hsrb_controllers.patch` | hsrb_controllers | control_msgsフィールド改名対応，Lifecycle API対応，diagnosticテストのJazzy API移植，旧APIテストの無効化（base／gripperは`-D..._ENABLE_TESTS=ON`で復活） |

### パッチの更新方法

修正したいリポジトリのソースを直接編集して動作確認した後，そのリポジトリの差分を書き出すだけです．

```sh
$ cd ~/colcon_ws/src/<対象リポジトリ>
$ git diff > ~/colcon_ws/src/hsrb_simulator/patches/<対象リポジトリ>.patch
```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- 対応インターフェース -->
## 対応インターフェース

| 機能 | トピック | 型 |
| --- | --- | --- |
| 台車速度指令 | `/omni_base_controller/cmd_vel` | `geometry_msgs/Twist` |
| アーム | `/arm_trajectory_controller/joint_trajectory` | `trajectory_msgs/JointTrajectory` |
| 首 | `/head_trajectory_controller/joint_trajectory` | `trajectory_msgs/JointTrajectory` |
| グリッパー | `/gripper_controller/command_distance` | `std_msgs/Float32` |
| オドメトリ | `/odom`（switcher経由），`/odom_ground_truth` | `nav_msgs/Odometry` |
| LiDAR | `/scan` | `sensor_msgs/LaserScan` |
| IMU | `/imu/data` | `sensor_msgs/Imu` |
| 頭部RGB-D | `/head_rgbd_sensor/rgb/…`，`/head_rgbd_sensor/depth_registered/…` | `sensor_msgs/Image` 等 |
| 手首力覚 | `/wrist_wrench/raw` | `geometry_msgs/WrenchStamped` |
| 関節状態 | `/joint_states` | `sensor_msgs/JointState` |

アームの関節は`arm_lift_joint`／`arm_flex_joint`／`arm_roll_joint`／`wrist_flex_joint`／`wrist_roll_joint`，
首は`head_pan_joint`／`head_tilt_joint`です．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- マイルストーン -->
## マイルストーン

- [x] ROS 2 Jazzy／Gazebo Sim 8でのビルド対応（パッチ一式）
- [x] 依存取得〜ビルドまでの冪等な`install.sh`
- [x] オムニ台車・アーム・首・グリッパーの動作確認
- [x] センサー一式の動作確認（worldへのセンサーシステム追加）

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- 参考文献 -->
## 参考文献

* [hsr-project (HSR OSS)](https://github.com/hsr-project)
* [hsr-project/hsrb_simulator](https://github.com/hsr-project/hsrb_simulator)
* [ROS Jazzy](https://docs.ros.org/en/jazzy/index.html)
* [Gazebo Sim](https://gazebosim.org/docs/latest/getstarted/)

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- ファイル構成 -->
## ファイル構成

<details>
  <summary>Tree構造</summary>

```text
.
├── LICENSE.txt
├── README.md
├── install.sh
├── patches/
│   ├── hsrb_simulator.patch
│   ├── hsrb_controllers.patch
│   ├── tmc_gazebo.patch
│   ├── tmc_navigation.patch
│   └── tmc_realtime_control.patch
├── hsrb_gazebo_bringup/
│   ├── config/          # gz_ros2_controlのコントローラ設定 (hsrb / hsrc)
│   ├── launch/          # 起動launch一式 (bringup / spawn / relay / sensor frames)
│   └── worlds/          # empty.sdf (センサーシステム対応済み)
├── hsrb_gz_ros2_control/        # HSR専用のgz_ros2_controlハードウェアプラグイン
└── hsrb_gripper_fake_interface/ # グリッパーのfakeハードウェアインターフェース
```

</details>

<details>
  <summary>パスごとの役割</summary>

| パス | 役割 |
| --- | --- |
| `install.sh` | 依存clone・パッチ適用・ビルドの自動セットアップ（冪等） |
| `patches/` | Jazzy／Gazebo Harmonic対応パッチ（git diff形式） |
| `hsrb_gazebo_bringup/launch/gazebo_bringup.launch.py` | gz起動〜spawn〜コントローラ〜ブリッジまでの本体launch |
| `hsrb_gazebo_bringup/launch/spawn_hsrb.launch.py` | 起動済みworldへHSRBをspawnするlaunch |
| `hsrb_gazebo_bringup/config/gazebo_ros2_control_hsrb.yaml` | コントローラ定義（オムニ台車・アーム・首・グリッパー等） |
| `hsrb_gz_ros2_control/` | gz_ros2_control用のHSRハードウェアプラグイン（グリッパーシミュレーション込み） |
| `hsrb_gripper_fake_interface/` | グリッパーfakeインターフェース |

</details>
