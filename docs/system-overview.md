# Kachaka Mission System - システム概要と詳細仕様

このドキュメントでは、Kachakaロボット用の自律的な話者発見追従システムの詳細な仕様と機能について説明します。

## 🎯 システム概要

### 主要機能
- **🔍 人物検出**: YOLOv8による2m以上の遠距離人物検出  
- **🧭 自律ナビゲーション**: Nav2を使用した巡回・接近移動制御
- **👤 顔追従**: MediaPipeによる近距離での精密な人物追従
- **🤖 状態遷移**: PATROLLING → APPROACHING → TRACKING の自動切り替え
- **📊 リアルタイム制御**: 動的パラメータ調整による最適化

### システム構成パッケージ
- **my_kachaka_apps**: ミッションコントローラーと顔追従システム（メイン機能）
- **yolo_ros**: 人物検出用YOLOv8統合
- **kachaka_grpc_ros2_bridge**: Kachaka API と ROS2 の間のgRPCブリッジ
- **kachaka_nav2_bringup**: Nav2ナビゲーション設定
- **realsense-ros**: RealSenseカメラ統合
- **kachaka_interfaces**: カスタムROS2メッセージとアクション定義
- **kachaka_description**: Kachakaロボットの3DモデルとURDF記述

### アーキテクチャ
```
[Kachaka Robot] ←→ [gRPC Bridge] ←→ [Mission Controller] ←→ [Nav2]
                                         ↓
[RealSense Camera] → [YOLO Detection] ↗   ↘ [Face Tracker]
```

## 🔄 状態遷移システム

### 状態定義と技術仕様

#### 1. PATROLLING（巡回状態）
- **技術**: Nav2 FollowWaypoints アクション
- **ウェイポイント**: `base` (1.08, -1.19), `jin-san` (1.19, -3.83), `charger` (0.89, 0.24), `suenaga-san` (3.13, -1.21)
- **制御周期**: 2Hz（mission_controller.py:121）
- **監視トピック**: `/simple_patrol_node/current_goal`

#### 2. APPROACHING（接近状態）
- **技術**: Nav2 NavigateToPose アクション + 3D座標変換
- **座標変換**: 2D YOLO検出 + 深度画像 → 3D地図座標
- **制御周期**: 2Hz（mission_controller.py:121）
- **監視トピック**: `/mission_controller/navigation_goal`

#### 3. TRACKING（追従状態）  
- **技術**: MediaPipe顔検出 + face_tracker_node制御
- **制御方式**: PID角速度制御
- **監視トピック**: `/face_tracker_node/face_detected`

### 詳細遷移条件と制約

#### PATROLLING → APPROACHING 遷移
**条件** (mission_controller.py:205):
- YOLO検出結果に`person`クラスが含まれる
- 検出信頼度 ≥ 0.6（yolo_threshold）
- 最後の検出から2秒以内（mission_controller.py:205）

**技術的制約**:
- カメラ校正情報が利用可能（camera_info）
- 深度画像が利用可能（depth_image）  
- TF変換（camera_color_optical_frame → map）が有効

#### APPROACHING → TRACKING 遷移
**条件** (mission_controller.py:218):
- ロボット-人物間距離 < 1.5m（approach_distance_threshold）
- TF変換（map → base_link）でロボット位置取得成功

**技術的制約**:
- Nav2ナビゲーションが正常完了
- 人物検出が継続中

#### TRACKING → PATROLLING 遷移  
**条件** (mission_controller.py:231):
- 人物ロストから5秒以上経過（person_lost_timeout）

**技術的制約**:
- face_tracker_nodeの正常非アクティブ化

#### APPROACHING → PATROLLING 遷移
**条件** (mission_controller.py:212):
- 人物ロストから5秒以上経過（接近中消失）

**技術的制約**:
- ナビゲーションタスクの正常キャンセル

### 状態監視コマンド
```bash
# 現在状態の確認（2Hz更新）
ros2 topic echo /mission_state

# 人物検出状況  
ros2 topic echo /yolo/detections

# 顔追従状態
ros2 param get /face_tracker_node is_active

# 距離測定（APPROACHING時）
ros2 run tf2_ros tf2_echo map base_link
```

### パラメータ調整
```bash
# 検出閾値（デフォルト: 0.6）
ros2 launch my_kachaka_apps mission_system.launch.py yolo_threshold:=0.5

# 接近距離（デフォルト: 1.5m）
ros2 param set /mission_controller approach_distance_threshold 2.0

# ロストタイムアウト（デフォルト: 5秒）
ros2 param set /mission_controller person_lost_timeout 3.0
```

## 📊 パラメータ詳細

### 顔追従システム (face_tracker_node)
| パラメータ名 | 型 | デフォルト値 | 説明 |
| :--- | :--- | :--- | :--- |
| `turn_gain` | Double | 0.003 | P制御の比例ゲイン [rad/s per pixel] |
| `dead_zone_percent` | Integer | 15 | 不感帯幅の画像幅に対する% |
| `target_distance` | Double | 0.5 | 追従時の目標距離 [m] |
| `linear_gain` | Double | 0.8 | 前後移動制御の比例ゲイン |
| `distance_dead_zone` | Double | 0.1 | 距離制御のデッドゾーン [m] |
| `is_active` | Boolean | true | 顔追従機能の有効/無効 |

### 画像強化パラメータ
| パラメータ名 | 型 | デフォルト値 | 説明 |
| :--- | :--- | :--- | :--- |
| `enable_image_enhancement` | Boolean | false | 画像強化処理の有効/無効 |
| `clahe_clip_limit` | Double | 8.0 | CLAHE contrast enhancement clip limit |
| `clahe_grid_size` | Integer | 6 | CLAHE tile grid size |
| `gamma_correction` | Double | 1.5 | Gamma correction value (>1.0 brightens) |
| `enable_bilateral_filter` | Boolean | true | Bilateral filtering for noise reduction |

### ミッションコントローラー (mission_controller)
| パラメータ名 | 型 | デフォルト値 | 説明 |
| :--- | :--- | :--- | :--- |
| `approach_distance_threshold` | Double | 1.0 | APPROACHING→TRACKING遷移距離閾値 [m] |
| `person_lost_timeout` | Double | 5.0 | 人物見失い時のタイムアウト [秒] |
| `patrol_waypoints` | List | 設定済み | 巡回ウェイポイントリスト |

## 🎮 システム操作とモニタリング

### システム状態の監視
```bash
# 実行中のノード確認
ros2 node list

# 人物検出状況の監視
ros2 topic echo /yolo/detections

# ロボット制御コマンドの監視
ros2 topic echo /kachaka/manual_control/cmd_vel

# カメラ画像の確認
ros2 topic echo /camera/camera/color/image_raw --once

# ミッション状態の確認
ros2 topic echo /mission_state
```

### パラメータによる制御
```bash
# 顔追従システムの有効/無効切り替え
ros2 param set /face_tracker_node is_active false  # 停止
ros2 param set /face_tracker_node is_active true   # 再開

# 追従距離の調整
ros2 param set /face_tracker_node target_distance 0.8  # 80cm

# 回転速度の調整 
ros2 param set /face_tracker_node turn_gain 0.002

# ミッションコントローラーの調整
ros2 param set /mission_controller approach_distance_threshold 2.0
ros2 param set /mission_controller person_lost_timeout 10.0
```

## 📋 実行可能なコマンド一覧

### 個別コンポーネント実行
```bash
# YOLO人物検出のみ
ros2 launch yolo_bringup yolov8.launch.py

# 顔追従システムのみ
ros2 run my_kachaka_apps face_tracker_node

# ミッションコントローラーのみ
ros2 run my_kachaka_apps mission_controller

# ナビゲーションのみ
ros2 launch kachaka_nav2_bringup navigation_launch.py
```

### テレオペ（手動制御）
```bash
# キーボード制御
ros2 launch my_kachaka_apps teleop_keyboard.launch.py

# ジョイスティック制御 
ros2 launch my_kachaka_apps teleop_joy.launch.py
```

### テスト・確認コマンド
```bash
# システム準備確認
python3 kachaka_map_manager.py <KACHAKA_IP>

# ミッションコントローラーテスト
python3 test_mission_controller.py

# 顔追従制御テスト
python3 test_is_active.py
```

## 🔧 最新機能強化（2025年1月実装）

### アップデート①: 顔検出アルゴリズムの向上
- **MediaPipe採用**: Haar Cascade から MediaPipe への移行で検出精度が大幅向上
- **RealSense D435対応**: pyrealsense2 SDK による直接カメラアクセス
- **画像強化処理**: bilateral filter、gamma correction、CLAHE による逆光・暗所対応
- **設定可能な前処理**: `enable_image_enhancement` パラメータで生画像/強化画像を選択可能

### アップデート②: 距離制御機能の追加
- **前後移動制御**: 深度カメラを使用して人物との距離を測定し、設定距離を維持
- **適応制御**: 距離エラーに応じて移動速度を調整する適応制御機能
- **安全機能**: デッドゾーン設定による振動防止と、人物を見失った際の安全停止

### アップデート③: テレオペレーション機能
- **キーボード制御**: teleop_twist_keyboard による手動制御
- **ジョイスティック制御**: PS4/Xbox コントローラーによる手動制御
- **起動ファイル統合**: 簡単な起動コマンドでテレオペ機能を利用可能

### アップデート④: 柔軟な制御設定
- **動的パラメータ調整**: 実行中にリアルタイムでパラメータ変更可能
- **画像処理レベル調整**: 照明条件に応じた最適化設定

## 🎛️ パラメータ調整方法

### 基本実行（デフォルトパラメータ使用）
```bash
ros2 run my_kachaka_apps face_tracker_node
```

### カスタムパラメータでの起動
```bash
# 画像強化を有効化（暗所・逆光対応）
ros2 run my_kachaka_apps face_tracker_node --ros-args \
  -p enable_image_enhancement:=true

# 制御パラメータのカスタマイズ
ros2 run my_kachaka_apps face_tracker_node --ros-args \
  -p turn_gain:=0.002 \
  -p dead_zone_percent:=20

# 画像強化パラメータの調整（暗所向け）
ros2 run my_kachaka_apps face_tracker_node --ros-args \
  -p enable_image_enhancement:=true \
  -p gamma_correction:=2.0 \
  -p clahe_clip_limit:=12.0
```

### 実行中のリアルタイム調整
```bash
# 画像強化を有効化（暗所・逆光対応）
ros2 param set /face_tracker_node enable_image_enhancement true

# P制御ゲインの調整
ros2 param set /face_tracker_node turn_gain 0.002

# 不感帯の調整
ros2 param set /face_tracker_node dead_zone_percent 20

# 距離制御パラメータの調整
ros2 param set /face_tracker_node target_distance 1.0
ros2 param set /face_tracker_node linear_gain 0.6
ros2 param set /face_tracker_node distance_dead_zone 0.15

# 画像強化パラメータの調整
ros2 param set /face_tracker_node gamma_correction 1.8
ros2 param set /face_tracker_node clahe_clip_limit 10.0
ros2 param set /face_tracker_node enable_bilateral_filter false
```

### パラメータ確認
```bash
# 現在のパラメータ値を確認
ros2 param list /face_tracker_node
ros2 param get /face_tracker_node enable_image_enhancement
ros2 param get /face_tracker_node turn_gain
```

## 💻 システム性能の調整

### 検出感度の調整
```bash
# 検出感度の調整
ros2 launch my_kachaka_apps mission_system.launch.py yolo_threshold:=0.3
```

### 暗所対応
```bash
# 暗所対応
ros2 param set /face_tracker_node enable_image_enhancement true
ros2 param set /face_tracker_node gamma_correction 2.0
```

### 追従動作の調整
```bash
# 追従動作の調整  
ros2 param set /face_tracker_node turn_gain 0.002
ros2 param set /face_tracker_node dead_zone_percent 20
```

## 🏗️ パッケージ詳細

### kachaka_grpc_ros2_bridge
Kachaka APIとROS2の間でデータをやり取りするためのgRPCブリッジです。以下の機能を提供します：

- カメラ画像の配信
- LIDARデータの配信
- IMUデータの配信
- ロボットの位置情報
- マッピング機能
- 移動コマンドの実行

### kachaka_interfaces
Kachakaシステム用のカスタムメッセージとアクション定義：

- `KachakaCommand`: ロボットへのコマンド
- `Location`: 位置情報
- `ObjectDetection`: 物体検出結果
- `ExecKachakaCommand`: コマンド実行アクション

### kachaka_description
Kachakaロボットの3DモデルとURDF記述ファイル：

- ロボットの物理的な形状定義
- センサーの配置
- 関節とリンクの定義

## 🔗 トピックの利用方法

### センサーデータの取得
```bash
# LIDARデータの取得
ros2 topic echo /kachaka/lidar/scan

# フロントカメラ画像の取得
ros2 topic echo /kachaka/front_camera/image_raw --once

# IMUデータの取得
ros2 topic echo /kachaka/imu/imu

# バッテリー状態の取得
ros2 topic echo /kachaka/robot_info/battery_state
```

### ロボット制御
```bash
# 手動制御（速度指令）
ros2 topic pub /kachaka/manual_control/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.1}}"

# 顔検出による自動制御（my_kachaka_appsパッケージ）
ros2 topic echo /cmd_vel  # 顔検出ノードからの制御コマンドを監視

# 目標位置の設定
ros2 topic pub /kachaka/goal_pose geometry_msgs/msg/PoseStamped "{header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 1.0, z: 0.0}, orientation: {w: 1.0}}}"
```

### 制御コマンドの監視
```bash
# 別ターミナルでKachakaへの制御コマンドを監視
ros2 topic echo /kachaka/manual_control/cmd_vel
```

## 🔍 期待される動作

### 顔追従システム
- **OpenCVウィンドウ**: "Face Detection"という名前のウィンドウが表示
- **顔の検出**: カメラの前に顔を向けるとMediaPipeの検出枠で囲まれる
- **高精度検出**: MediaPipeにより従来のHaar Cascadeより高精度な検出
- **画像強化**: 逆光・暗所でも安定した検出性能
- **追従制御**: ロボットが人物を中央に捉えるように旋回し、設定距離を保つように前後移動
- **制御値出力**: 顔の位置、距離、計算された速度がコンソールに表示
- **制御コマンド**: `/kachaka/manual_control/cmd_vel`トピックに制御コマンドが送信される
- **デッドゾーン**: 顔が中央付近かつ目標距離付近にある時は動作停止（振動防止）
- **安全機能**: 人物を見失った際の自動停止
- **テスト画像**: 30フレームごとに検出結果が `/tmp/` に保存

### ミッションシステム
- **自律巡回**: 定義されたウェイポイント間を巡回
- **人物検出**: YOLOv8による2m以上の遠距離検出
- **自動接近**: 検出した人物に向かって自動移動
- **精密追従**: 接近後はMediaPipeによる精密な顔追従
- **状態遷移**: 適切なタイミングでの状態切り替え

## 📁 重要ファイル

- **`docs/git-workflow-guide.md`**: Gitワークフローの完全ガイド（日本語）
- **`docs/troubleshooting-guide.md`**: 詳細なトラブルシューティングガイド
- **`kachaka_map_manager.py`**: システム準備状況確認ツール  
- **`start_mission_system.sh`**: 簡単起動スクリプト
- **`test_mission_controller.py`**: ミッションコントローラーテストツール
- **`test_is_active.py`**: 顔追従制御テストツール

## 🚀 開発者向け情報

### パッケージ構造
```
ws_kachaka/
├── src/
│   ├── kachaka_grpc_ros2_bridge/
│   │   ├── gen-src/           # 自動生成されるプロトコルバッファファイル
│   │   ├── src/               # ソースコード
│   │   └── launch/            # 起動ファイル
│   ├── kachaka_interfaces/    # メッセージ・アクション定義
│   ├── kachaka_description/   # ロボットモデル
│   ├── kachaka_nav2_bringup/  # ナビゲーション設定
│   ├── my_kachaka_apps/       # メインアプリケーション
│   ├── yolo_ros/              # YOLOv8統合
│   └── realsense-ros/         # RealSenseカメラ統合
├── docs/                      # ドキュメント
├── build/                     # ビルド結果
├── install/                   # インストール結果
└── log/                       # ビルドログ
```

### 依存関係
- **ROS2パッケージ**: rclcpp, sensor_msgs, nav_msgs, tf2_ros, cv_bridge, nav2_core
- **システムライブラリ**: gRPC++, protobuf, OpenCV, MediaPipe
- **外部プロジェクト**: Kachaka API (~/kachaka-api)

## ライセンス

各パッケージは以下のライセンスに従います：
- kachaka_grpc_ros2_bridge: Apache License 2.0
- その他のパッケージ: 各パッケージのpackage.xmlを参照

---

**🤖 Kachaka Mission System v1.0** - 完全自律話者追従システム  
**実装完了**: PATROLLING → APPROACHING → TRACKING の状態遷移による自律的な人物発見・追従機能