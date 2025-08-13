# Kachaka Mission System - 自律話者追従システム

Kachakaロボット用の自律的な話者発見追従システムです。ロボットが自動で屋内を巡回し、話している人を発見・接近・追従します。

## 🎯 主要機能

- **🔍 人物検出**: YOLOv8による遠距離人物検出  
- **🧭 自律ナビゲーション**: Nav2を使用した巡回・接近移動制御
- **👤 顔追従**: MediaPipeによる精密な人物追従
- **🤖 状態遷移**: PATROLLING → APPROACHING → TRACKING の自動切り替え
- **📊 リアルタイム制御**: 動的パラメータ調整による最適化

## 📚 ドキュメント

- **[現在の状態](docs/current_status.md)** - 最新のシステム状態と動作確認結果 🆕
- **[システム概要](docs/system-overview.md)** - 詳細な機能仕様とアーキテクチャ
- **[トラブルシューティングガイド](docs/troubleshooting-guide.md)** - 問題解決とデバッグ情報
- **[Gitワークフローガイド](docs/git-workflow-guide.md)** - 開発ワークフロー完全ガイド（日本語）
- **[巡回システム修正記録](docs/patrol_system_fixes.md)** - AMCL/ローカライゼーション問題の完全解決 🔥
- **[巡回テスト開発記録](docs/patrol_test_development.md)** - PATROLLINGモードテスト開発の進捗

## 🚀 クイックスタート

### システム要件
- **Ubuntu 22.04 LTS**
- **ROS2 Humble Hawksbill** 
- **Kachaka Robot** (ネットワーク接続済み)
- **RealSense D435 Camera** (推奨)

### 📦 インストール

#### 1. 基本パッケージ
```bash
sudo apt update
sudo apt install -y \
    libgrpc++-dev \
    libprotobuf-dev \
    protobuf-compiler-grpc \
    libopencv-dev \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-nav2-bringup \
    ros-humble-tf2-tools \
    python3-pip
```

#### 2. Pythonライブラリ
```bash
pip3 install mediapipe opencv-python numpy
```

#### 3. 依存関係のインストール
```bash
cd ~/ws_kachaka
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 🗺️ 地図の準備（重要！）

**システム実行前に必ず地図を作成してください：**

1. **Kachakaスマートフォンアプリ**を起動
2. **「地図作成」**機能を選択
3. **手動操縦**でロボットを環境内で移動させる
4. **地図を保存**する

地図の確認：
```bash
cd ~/kachaka-api/python/demos/grpc_samples
python3 get_map_list.py <KACHAKA_IP>:26400
```

### 🔧 セットアップ

#### 1. Kachaka API の準備
```bash
# プロトコルバッファファイルを生成
~/kachaka-api/tools/generate_proto_for_ros2.sh

# 生成されたファイルをコピー
cp -r ~/kachaka-api/ros2/kachaka_grpc_ros2_bridge/gen-src ~/ws_kachaka/src/kachaka_grpc_ros2_bridge/
```

#### 2. ワークスペースのビルド
```bash
cd ~/ws_kachaka
source /opt/ros/humble/setup.bash
colcon build --cmake-args -DUSE_LIFECYCLE_NODE=ON
source install/setup.bash
```

#### 3. システム準備状況の確認
```bash
# システムの準備状況を確認
python3 kachaka_map_manager.py <KACHAKA_IP>
```

## 🚀 実行方法

### 簡単起動（推奨）
```bash
cd ~/ws_kachaka
source install/setup.bash

# 一発起動スクリプトを使用
./start_mission_system.sh <KACHAKA_IP>

# 例: ./start_mission_system.sh 192.168.118.95
```

### 手動起動

#### ステップ1: gRPCブリッジ起動
```bash
cd ~/kachaka-api/tools/ros2_bridge
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=0
sudo -E ./start_bridge.sh <KACHAKA_IP>
```

#### ステップ2: ミッションシステム起動
```bash
cd ~/ws_kachaka
source install/setup.bash

# 完全システム（ナビゲーション有効）
ros2 launch my_kachaka_apps mission_system.launch.py enable_nav2:=true
```

## 🎮 基本操作

### システム状態の監視
```bash
# 実行中のノード確認
ros2 node list

# 人物検出状況の監視
ros2 topic echo /yolo/detections

# ロボット制御コマンドの監視
ros2 topic echo /kachaka/manual_control/cmd_vel
```

### パラメータ調整
```bash
# 顔追従システムの有効/無効切り替え
ros2 param set /face_tracker_node is_active false  # 停止
ros2 param set /face_tracker_node is_active true   # 再開

# 追従距離の調整
ros2 param set /face_tracker_node target_distance 0.8  # 80cm

# 回転速度の調整 
ros2 param set /face_tracker_node turn_gain 0.002
```

### テレオペ（手動制御）
```bash
# キーボード制御
ros2 launch my_kachaka_apps teleop_keyboard.launch.py

# ジョイスティック制御 
ros2 launch my_kachaka_apps teleop_joy.launch.py
```

## 🔄 状態遷移システム

システムは3つの主要状態を持ち、以下の条件で自動的に遷移します：

### 状態一覧

1. **PATROLLING（巡回状態）** 
   - **動作**: 事前定義されたウェイポイント間を自律巡回
   - **ウェイポイント**: `base`, `jin-san`, `charger`, `suenaga-san`
   - **使用技術**: Nav2 FollowWaypoints アクション

2. **APPROACHING（接近状態）**
   - **動作**: 検出された人物に向かってナビゲーション移動  
   - **使用技術**: Nav2 NavigateToPose アクション + YOLO検出座標変換

3. **TRACKING（追従状態）**
   - **動作**: 近距離での人物追従（face_tracker_node制御）
   - **使用技術**: MediaPipe顔検出 + 精密角速度制御

### 状態遷移条件と制約

#### PATROLLING → APPROACHING 遷移
**遷移条件:**
- YOLO検出で人物（person）クラスが検出される
- 検出信頼度が 0.5 以上
- 最後の検出から 2秒以内

**制約:**
- カメラ校正情報（camera_info）が利用可能であること  
- 深度画像（depth_image）が利用可能であること
- TF変換（camera_color_optical_frame → map）が利用可能であること

#### APPROACHING → TRACKING 遷移  
**遷移条件:**
- ロボットが目標人物位置から 1.5m 以内に到達
- 人物検出が継続している

**制約:**
- TF変換（map → base_link）でロボット位置取得が可能であること
- Nav2ナビゲーションが正常に完了していること

#### TRACKING → PATROLLING 遷移
**遷移条件:**
- 人物を見失ってから 5秒以上経過

**制約:**
- face_tracker_nodeが正常に非アクティブ化されること

#### APPROACHING → PATROLLING 遷移
**遷移条件:**  
- 人物を見失ってから 5秒以上経過（接近中に人物が消失）

**制約:**
- 進行中のナビゲーションタスクが正常にキャンセルされること

### 監視可能なトピック

```bash
# 現在の状態を監視（2Hz更新）
ros2 topic echo /mission_state

# 人物検出状況を監視
ros2 topic echo /yolo/detections  

# 顔追従の有効/無効状態を確認
ros2 param get /face_tracker_node is_active

# 現在のナビゲーション目標を確認
ros2 topic echo /simple_patrol_node/current_goal
```

### パラメータ設定

```bash
# 接近距離閾値の変更（デフォルト: 1.5m）
ros2 param set /mission_controller approach_distance_threshold 2.0

# 人物ロスト時のタイムアウト変更（デフォルト: 5秒）
ros2 param set /mission_controller person_lost_timeout 3.0

# YOLO検出閾値の変更（デフォルト: 0.5）
ros2 launch my_kachaka_apps mission_system.launch.py yolo_threshold:=0.3
```

## 🛠️ よくある問題

### カメラデータが取得できない
```bash
# RealSenseカメラの手動アクティベーション
ros2 lifecycle set /camera/camera configure
ros2 lifecycle set /camera/camera activate
```

### gRPCブリッジエラー
```bash
# Dockerコンテナのクリーンアップ
cd ~/kachaka-api/tools/ros2_bridge
sudo docker-compose down --remove-orphans

# FastRTPSで再起動
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
sudo -E ./start_bridge.sh <KACHAKA_IP>
```

### ナビゲーションが動かない
```bash
# 地図データの確認
ros2 topic echo /kachaka/mapping/map --once

# TF関係の確認
ros2 run tf2_tools view_frames
```

**詳細なトラブルシューティングは [docs/troubleshooting-guide.md](docs/troubleshooting-guide.md) を参照してください。**

## 📁 重要ファイル

- **`kachaka_map_manager.py`**: システム準備状況確認ツール  
- **`start_mission_system.sh`**: 簡単起動スクリプト
- **`test_mission_controller.py`**: ミッションコントローラーテストツール
- **`test_is_active.py`**: 顔追従制御テストツール

## 🎯 次のステップ

### 初回セットアップ完了後
1. **地図作成**: Kachakaアプリで環境の地図を作成
2. **システム確認**: `python3 kachaka_map_manager.py <KACHAKA_IP>` でシステム準備状況を確認
3. **統合テスト**: `./start_mission_system.sh <KACHAKA_IP>` で完全システム起動
4. **動作確認**: カメラの前に立って状態遷移をテスト

### システム性能の調整
```bash
# 検出感度の調整
ros2 launch my_kachaka_apps mission_system.launch.py yolo_threshold:=0.3

# 暗所対応
ros2 param set /face_tracker_node enable_image_enhancement true
ros2 param set /face_tracker_node gamma_correction 2.0

# 追従動作の調整  
ros2 param set /face_tracker_node turn_gain 0.002
ros2 param set /face_tracker_node dead_zone_percent 20
```

## 📞 サポート

問題が発生した場合:
1. **[トラブルシューティングガイド](docs/troubleshooting-guide.md)** の詳細情報を確認
2. **システム状態確認**: `kachaka_map_manager.py` でシステム状態をチェック
3. **個別テスト**: 各テストスクリプトで個別コンポーネントを検証
4. **ログ確認**: `ros2 node info <ノード名>` でノード状態を確認

## 🏗️ 開発者向け

- **[システム概要](docs/system-overview.md)** - 詳細な機能仕様とアーキテクチャ
- **[Gitワークフローガイド](docs/git-workflow-guide.md)** - 開発ワークフロー完全ガイド

## ライセンス

各パッケージは以下のライセンスに従います：
- kachaka_grpc_ros2_bridge: Apache License 2.0
- その他のパッケージ: 各パッケージのpackage.xmlを参照

---

**🤖 Kachaka Mission System v1.0** - 完全自律話者追従システム  
**実装完了**: PATROLLING → APPROACHING → TRACKING の状態遷移による自律的な人物発見・追従機能