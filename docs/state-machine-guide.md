# 状態遷移システム詳細ガイド

## 概要

Kachaka Mission Systemの中核となる状態遷移システムの詳細仕様書です。システムの自律的な動作を理解し、トラブルシューティングや性能調整に活用してください。

## システムアーキテクチャ

### 状態遷移図
```
    [PATROLLING]  
         |  
         | 人物検出（信頼度>0.5, 2秒以内）
         ↓
    [APPROACHING]
         |         ↑
         |         | 人物ロスト（5秒以上）
         |         |
    距離<1.5m      |
         |         |
         ↓         |
    [TRACKING] ---+
         |
         | 人物ロスト（5秒以上）
         ↓
    [PATROLLING]
```

## 状態詳細仕様

### 1. PATROLLING状態（巡回状態）

#### 基本動作
- **目的**: 環境内を自律的に巡回し、人物を探索
- **制御**: Nav2 FollowWaypoints アクション使用
- **更新頻度**: 2Hz（0.5秒間隔）

#### ウェイポイント設定
```python
waypoint_dict = {
    'base': {'x': 1.080, 'y': -1.191},
    'jin-san': {'x': 1.193, 'y': -3.832}, 
    'charger': {'x': 0.886, 'y': 0.243},
    'suenaga-san': {'x': 3.134, 'y': -1.210}
}
waypoint_sequence = ['jin-san', 'charger', 'suenaga-san', 'base']
```

#### 遷移条件
- **PATROLLING → APPROACHING**: 
  - YOLO検出結果に`person`クラスが含まれる
  - 検出信頼度 ≥ 0.5
  - 最後の検出時刻から2秒以内
  
#### 技術的制約
- Nav2ナビゲーションスタックが起動済みであること
- 地図データ（/kachaka/mapping/map）が利用可能であること
- TF変換（map ↔ base_link）が正常に機能していること

#### 監視項目
```bash
# 巡回状況の監視
ros2 topic echo /simple_patrol_node/current_goal

# Nav2アクションサーバーの状態
ros2 action list | grep follow_waypoints
```

### 2. APPROACHING状態（接近状態）

#### 基本動作
- **目的**: 検出された人物の位置まで移動
- **制御**: Nav2 NavigateToPose アクション使用
- **座標変換**: 2D検出 + 深度画像 → 3D地図座標

#### 座標変換プロセス
1. **2D検出座標取得**: YOLO境界ボックス中心点
2. **深度値取得**: 深度画像から対応ピクセルの距離値
3. **3D座標計算**: カメラ内部パラメータを使用
4. **座標変換**: camera_color_optical_frame → map フレーム

```python
# カメラ座標系での3D点計算
x_cam = (center_u - cx) * depth_meters / fx
y_cam = (center_v - cy) * depth_meters / fy  
z_cam = depth_meters

# RealSense光学座標系への変換
camera_point.x = z_cam    # 前方向
camera_point.y = -x_cam   # 左方向
camera_point.z = -y_cam   # 上方向
```

#### 遷移条件
- **APPROACHING → TRACKING**:
  - ロボットと目標位置の距離 < 1.5m
  - 人物検出が継続している
  
- **APPROACHING → PATROLLING**: 
  - 人物ロストから5秒以上経過

#### 技術的制約
- カメラ校正情報（/camera/camera/color/camera_info）が利用可能
- 深度画像（/camera/camera/depth/image_rect_raw）が利用可能
- TF変換（camera_color_optical_frame → map）が利用可能
- 深度値が有効範囲（0 < depth ≤ 10.0m）内にある

#### エラーハンドリング
```python
# 無効な深度値の検出
if depth_meters <= 0 or depth_meters > 10.0:
    logger.debug(f'Invalid depth value: {depth_meters}')
    return None

# 境界ボックスが画像範囲外
if (center_u < 0 or center_v < 0 or 
    center_u >= image_width or center_v >= image_height):
    logger.debug(f'Detection center outside image bounds')
    return None
```

### 3. TRACKING状態（追従状態）

#### 基本動作
- **目的**: 人物の至近距離での精密追従
- **制御**: face_tracker_node による直接速度制御
- **技術**: MediaPipe顔検出 + PID制御

#### face_tracker_node制御
```bash
# 追従開始
ros2 param set /face_tracker_node is_active true

# 追従停止  
ros2 param set /face_tracker_node is_active false
```

#### 遷移条件
- **TRACKING → PATROLLING**:
  - 人物ロストから5秒以上経過

#### 技術的制約
- face_tracker_nodeが正常に起動していること
- MediaPipe顔検出が機能していること  
- カメラ映像（/camera/camera/color/image_raw）が利用可能

## 状態監視とデバッグ

### リアルタイム状態監視

```bash
# メイン状態の監視（2Hz更新）
ros2 topic echo /mission_state

# 状態変更履歴の確認
ros2 topic echo /mission_state | ts '[%Y-%m-%d %H:%M:%S]'

# 人物検出状況の詳細監視
ros2 topic echo /yolo/detections --no-arr

# 検出信頼度のみ抽出
ros2 topic echo /yolo/detections | grep -A5 "score:"
```

### 状態別デバッグコマンド

#### PATROLLING状態のデバッグ
```bash
# 現在の目標ウェイポイント確認
ros2 topic echo /simple_patrol_node/current_goal --once

# Nav2アクションサーバーの状態
ros2 action send_goal /follow_waypoints nav2_msgs/action/FollowWaypoints "{}" --feedback

# 巡回速度の調整
ros2 param set /simple_patrol_node patrol_speed 0.2
```

#### APPROACHING状態のデバッグ  
```bash
# カメラ校正情報の確認
ros2 topic echo /camera/camera/color/camera_info --once

# 深度画像の確認
ros2 topic hz /camera/camera/depth/image_rect_raw

# TF変換の確認
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo camera_color_optical_frame map
```

#### TRACKING状態のデバッグ
```bash  
# face_tracker_nodeの状態確認
ros2 param get /face_tracker_node is_active
ros2 topic echo /face_tracker_node/debug --once

# 顔検出の確認
ros2 topic echo /face_tracker_node/face_detected --once
```

## パフォーマンス調整

### 検出感度の調整
```bash
# YOLO検出閾値（デフォルト: 0.5）
ros2 launch my_kachaka_apps mission_system.launch.py yolo_threshold:=0.3

# 接近距離閾値（デフォルト: 1.5m）
ros2 param set /mission_controller approach_distance_threshold 2.0

# 人物ロストタイムアウト（デフォルト: 5秒）
ros2 param set /mission_controller person_lost_timeout 3.0
```

### 巡回速度の最適化
```bash
# 巡回速度（デフォルト: 0.3 m/s）
ros2 param set /simple_patrol_node patrol_speed 0.25

# 目標到達許容誤差（デフォルト: 0.5m）
ros2 param set /simple_patrol_node goal_tolerance 0.3
```

### 追従精度の調整
```bash
# 回転ゲイン（デフォルト: 0.003）
ros2 param set /face_tracker_node turn_gain 0.002

# 不感帯（デフォルト: 15%）
ros2 param set /face_tracker_node dead_zone_percent 20

# 目標距離（デフォルト: 0.5m）
ros2 param set /face_tracker_node target_distance 0.8
```

## トラブルシューティング

### 状態遷移が発生しない場合

#### PATROLLING → APPROACHING 遷移しない
```bash
# 人物検出の確認
ros2 topic echo /yolo/detections | grep -A5 "person"

# カメラ映像の確認  
ros2 topic hz /camera/camera/color/image_raw

# YOLO検出閾値の確認
ros2 param get /yolo_ros_node threshold
```

#### APPROACHING → TRACKING 遷移しない
```bash
# ロボット位置の確認
ros2 run tf2_ros tf2_echo map base_link

# 目標との距離計算
ros2 topic echo /mission_controller/distance_to_goal --once

# ナビゲーション状態の確認
ros2 action list | grep navigate_to_pose
```

#### TRACKING → PATROLLING 遷移しない
```bash
# 人物検出継続状況の確認
ros2 topic echo /yolo/detections --no-arr | grep "person"

# face_tracker_nodeの状態
ros2 param get /face_tracker_node is_active
ros2 topic echo /face_tracker_node/face_detected --once
```

### システム復旧手順

#### 状態がスタックした場合
```bash
# 1. 現在状態の確認
ros2 topic echo /mission_state --once

# 2. 手動で巡回状態に復帰
ros2 service call /mission_controller/reset_to_patrol std_srvs/srv/Trigger

# 3. face_tracker無効化
ros2 param set /face_tracker_node is_active false

# 4. ナビゲーション再開
ros2 service call /simple_patrol_node/resume_patrol std_srvs/srv/Trigger
```

## 開発者向け情報

### 状態遷移ログの分析
```bash
# 状態遷移履歴の抽出
grep "State transition" ~/.ros/log/latest/mission_controller/*.log

# タイミング分析
grep -E "(PATROLLING|APPROACHING|TRACKING)" ~/.ros/log/latest/mission_controller/*.log | tail -50
```

### 新しい状態の追加方法
1. `MissionState` enumに新状態を追加
2. `state_machine_update()`に状態処理を追加
3. 遷移条件を`handle_*_state()`メソッドに実装
4. 必要に応じて`transition_to_*()`メソッドを作成

### パラメータ設定の永続化
```bash
# 設定を保存
ros2 param dump /mission_controller > mission_controller_params.yaml
ros2 param dump /face_tracker_node > face_tracker_params.yaml

# 起動時に設定を読込
ros2 launch my_kachaka_apps mission_system.launch.py \
  mission_params_file:=mission_controller_params.yaml \
  face_tracker_params_file:=face_tracker_params.yaml
```

## まとめ

状態遷移システムは、人物検出・接近・追従という一連の動作を自律的に実行する中核機能です。各状態の条件と制約を理解することで、システムの動作を正確に予測し、問題発生時の迅速な対応が可能になります。

定期的な監視とパラメータ調整により、環境に最適化されたシステム性能を維持してください。