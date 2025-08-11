# Kachaka Mission System - Speaker Detection and Following

このワークスペースは、**Kachakaロボット用の自律的な話者発見追従システム**を実装しています。ロボットが自動で屋内を巡回し、話している人を発見・接近・追従する完全統合システムです。

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

## 🚀 初心者向けチュートリアル

### システム要件
- **Ubuntu 22.04 LTS**
- **ROS2 Humble Hawksbill** 
- **Kachaka Robot** (ネットワーク接続済み)
- **RealSense D435 Camera** (推奨)

### 📦 必要なパッケージのインストール

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

#### 3. YOLOモデルファイル
```bash
cd ~/ws_kachaka
# YOLOv8モデルは自動ダウンロードされますが、事前に取得する場合：
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt
```

### 🗺️ 地図の準備（重要！）
**システム実行前に必ず地図を作成してください：**

#### 地図の確認方法
```bash
cd ~/kachaka-api/python/demos/grpc_samples
python3 get_map_list.py <KACHAKA_IP>:26400
```

#### 地図がない場合の作成手順
1. **Kachakaスマートフォンアプリ**を起動
2. **「地図作成」**機能を選択
3. **手動操縦**でロボットを環境内で移動させる
4. **地図を保存**する
5. アプリで地図が正しく保存されたことを確認

### 🔧 Kachaka API の準備
```bash
# ~/kachaka-api ディレクトリにKachaka APIが配置されていることを確認
ls ~/kachaka-api/protos/kachaka-api.proto

# プロトコルバッファファイルを生成
~/kachaka-api/tools/generate_proto_for_ros2.sh
```

## ⚙️ セットアップ手順（初回のみ）

### 1. ワークスペースの準備
```bash
cd ~/ws_kachaka
source /opt/ros/humble/setup.bash
```

### 2. 依存関係のインストール
```bash
# ROS2パッケージの依存関係を自動解決
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 3. プロトコルバッファファイルの生成とコピー
```bash
# Kachaka APIからプロトコルバッファファイルを生成
~/kachaka-api/tools/generate_proto_for_ros2.sh

# 生成されたファイルをワークスペースにコピー
cp -r ~/kachaka-api/ros2/kachaka_grpc_ros2_bridge/gen-src ~/ws_kachaka/src/kachaka_grpc_ros2_bridge/
```

### 4. ワークスペースのビルド
```bash
cd ~/ws_kachaka
colcon build --cmake-args -DUSE_LIFECYCLE_NODE=ON

# ビルド成功後、環境を設定
source install/setup.bash
```

### 5. システム準備状況の確認
```bash
# システムの準備状況を確認（重要！）
python3 kachaka_map_manager.py <KACHAKA_IP>
```

## 🚀 システムの実行

### 方法1: 簡単起動（初心者推奨）
```bash
cd ~/ws_kachaka
source install/setup.bash

# 一発起動スクリプトを使用
./start_mission_system.sh <KACHAKA_IP>

# 例: ./start_mission_system.sh 192.168.118.95
```

### 方法2: 手動起動（上級者向け）

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

# 基本システム（ナビゲーションなし）
ros2 launch my_kachaka_apps mission_system.launch.py
```

### 実行可能なコマンド一覧

#### 個別コンポーネント実行
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

#### テレオペ（手動制御）
```bash
# キーボード制御
ros2 launch my_kachaka_apps teleop_keyboard.launch.py

# ジョイスティック制御 
ros2 launch my_kachaka_apps teleop_joy.launch.py
```

#### テスト・確認コマンド
```bash
# システム準備確認
python3 kachaka_map_manager.py <KACHAKA_IP>

# ミッションコントローラーテスト
python3 test_mission_controller.py

# 顔追従制御テスト
python3 test_is_active.py
```

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

### 🔄 状態遷移システム

1. **PATROLLING（巡回）**: 事前定義されたウェイポイントを巡回
2. **APPROACHING（接近）**: YOLO検出した人物に向かって移動
3. **TRACKING（追従）**: 近距離での顔追従制御

## 🛠️ トラブルシューティング

### よくある問題と解決法

#### 1. 「カメラデータが取得できない」

**症状**: `/camera/camera/color/image_raw` にデータが流れない

**解決方法**:
```bash
# RealSenseカメラの手動アクティベーション
ros2 lifecycle set /camera/camera configure
ros2 lifecycle set /camera/camera activate

# カメラトピックの確認
ros2 topic list | grep camera
ros2 topic echo /camera/camera/color/image_raw --once
```

#### 2. 「人物検出ができない」
**症状**: YOLOが人を検出しない

**解決方法**:
```bash
# YOLO検出結果の確認
ros2 topic echo /yolo/detections

# YOLOデバッグ画像の確認
ros2 topic echo /yolo/dbg_image

# YOLOモデルファイルの確認
ls -la ~/ws_kachaka/yolov8m.pt
```

#### 3. 「ナビゲーションが動かない」
**症状**: ロボットが移動しない、Nav2エラー

**解決方法**:
```bash
# 地図データの確認
ros2 topic echo /kachaka/mapping/map --once

# Nav2ノードの確認
ros2 node list | grep nav2
ros2 action list | grep navigate

# 地図の再作成が必要な場合はKachakaアプリで実行
```

#### 4. **⚠️ 重要: gRPCブリッジRMW実装エラー**

**症状**: Dockerブリッジ起動時にRMW実装エラーが発生
```
[ERROR] [rcl]: Error getting RMW implementation identifier / RMW implementation not installed
(expected identifier of 'rmw_cyclonedx_cpp'), with error message 'failed to load shared library
'librmw_cyclonedx_cpp.so' due to dlopen error: librmw_cyclonedx_cpp.so: cannot open shared object file'
```

**解決方法**:
```bash
# 1. Dockerコンテナのクリーンアップ
cd ~/kachaka-api/tools/ros2_bridge
sudo docker-compose down --remove-orphans
sudo docker system prune -f

# 2. 正しいRMW実装を設定して起動
export TAG=latest
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=0
sudo -E ./start_bridge.sh <KACHAKA_IP>

# 例
sudo -E ./start_bridge.sh 192.168.118.95
```

**原因**: Dockerコンテナ内でCycloneDDS RMW実装が利用できない場合、FastRTPSに切り替えが必要

#### 5. 「ロボットが反応しない」
**症状**: パラメータ変更してもロボットの動作が変わらない

**解決方法**:
```bash
# face_tracker_nodeの状態確認
ros2 param get /face_tracker_node is_active

# ミッションコントローラーの状態確認
ros2 node info /mission_controller

# 手動制御でテスト
ros2 launch my_kachaka_apps teleop_keyboard.launch.py
```

### RealSenseカメラの手動アクティベーション

このワークスペースはLifecycleNode機能が有効のため、RealSenseカメラは手動アクティベーションが必要です：

```bash
# カメラノードの起動
ros2 launch realsense2_camera rs_launch.py &

# アクティベーション
ros2 lifecycle set /camera/camera configure
ros2 lifecycle set /camera/camera activate

# 状態確認
ros2 lifecycle get /camera/camera
ros2 topic list | grep camera
```

### 環境変数の設定確認

```bash
# ROS2環境を設定
export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp  # ローカル用
export ROS_DOMAIN_ID=0
source ~/ws_kachaka/install/setup.bash

# トピック・ノードの確認
ros2 topic list
ros2 node list
```

## 📁 重要ファイル

- **`MISSION_SYSTEM_GUIDE.md`**: 詳細な使用説明書とトラブルシューティング
- **`kachaka_map_manager.py`**: システム準備状況確認ツール  
- **`start_mission_system.sh`**: 簡単起動スクリプト
- **`test_mission_controller.py`**: ミッションコントローラーテストツール
- **`test_is_active.py`**: 顔追従制御テストツール

## 🎯 次のステップ

### 初回セットアップ完了後
1. **地図作成**: Kachakaアプリで環境の地図を作成
2. **システム確認**: `python3 kachaka_map_manager.py <KACHAKA_IP>` でシステム準備状況を確認
3. **統合テスト**: `./start_mission_system.sh <KACHAKA_IP>` で完全システム起動
4. **動作確認**: カメラの前に立って状態遷移 (PATROLLING→APPROACHING→TRACKING) をテスト

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

システムに問題がある場合:
1. **システム状態確認**: `kachaka_map_manager.py` でシステム状態をチェック
2. **詳細ガイド参照**: `MISSION_SYSTEM_GUIDE.md` の詳細トラブルシューティングを確認  
3. **個別テスト**: 各テストスクリプトで個別コンポーネントを検証
4. **ログ確認**: `ros2 node info <ノード名>` でノード状態を確認

---
**🤖 Kachaka Mission System v1.0** - 完全自律話者追従システム  
**実装完了**: PATROLLING → APPROACHING → TRACKING の状態遷移による自律的な人物発見・追従機能

### 環境設定の確認
```bash
# ROS2環境を設定
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
export FRAME_PREFIX="kachaka"
source ~/kachaka_ws/install/setup.bash

# トピック一覧を確認
ros2 topic list

# ノード一覧を確認
ros2 node list
```

### サンプルノードの実行
```bash
# フォローノードの実行例
ros2 run kachaka_follow follow
```

### ナビゲーションの起動
```bash
ros2 launch kachaka_nav2_bringup navigation_launch.py
```

### RealSenseカメラの使用方法

このワークスペースはLifecycleNode機能が有効化されているため、RealSenseカメラは通常のノードとは異なる起動手順が必要です。

#### 1. カメラノードの起動
```bash
# ワークスペースの環境を読み込み
source install/setup.bash

# RealSenseカメラノードを起動（バックグラウンドで実行）
ros2 launch realsense2_camera rs_launch.py &
```

#### 2. LifecycleNodeのアクティベーション
カメラノードを起動した後、以下のコマンドでノードを設定・アクティベートする必要があります：

```bash
# ノードを設定状態に移行
ros2 lifecycle set /camera/camera configure

# ノードをアクティブ状態に移行（この時点でトピックが配信開始）
ros2 lifecycle set /camera/camera activate
```

#### 3. カメラトピックの確認
アクティベーション後、以下のトピックが利用可能になります：

```bash
# カメラトピック一覧を確認
ros2 topic list | grep camera

# カラー画像の取得
ros2 topic echo /camera/camera/color/image_raw --once

# 深度画像の取得  
ros2 topic echo /camera/camera/depth/image_rect_raw --once

# カメラ情報の取得
ros2 topic echo /camera/camera/color/camera_info --once
```

#### 4. LifecycleNodeの状態管理
```bash
# 現在の状態を確認
ros2 lifecycle get /camera/camera

# ノードを非アクティブ化（トピック配信停止）
ros2 lifecycle set /camera/camera deactivate

# ノードを設定解除
ros2 lifecycle set /camera/camera cleanup

# ノードを再アクティブ化
ros2 lifecycle set /camera/camera configure
ros2 lifecycle set /camera/camera activate
```

**💡 ヒント**: 
- LifecycleNodeを使用する理由は、カメラリソースの適切な管理とシステムの安定性向上のためです
- カメラを使用しない場合は `deactivate` でリソースを解放できます
- システム起動時に自動でアクティベーションしたい場合は、起動スクリプトに上記コマンドを含めてください

### 顔検出・追従アプリケーション（my_kachaka_apps）の使用方法

このワークスペースには、RealSenseカメラを使用した顔検出・追従機能が含まれています。

#### 📋 機能概要
- **顔検出**: MediaPipe による高精度な人物の顔検出
- **リアルタイム表示**: cv2.imshowによるカメラ映像と検出結果の表示
- **バウンディングボックス**: 検出された顔をMediaPipeの描画機能で表示
- **画像強化**: 逆光・暗所での検出性能向上のための画像前処理機能
- **追従制御**: 人物を検出し、設定距離を保ちながら追従する機能
- **制御コマンド送信**: `/kachaka/manual_control/cmd_vel`トピックに制御コマンドを送信
- **デバッグ機能**: 検出結果を `/tmp/face_detection_test_*.jpg` に自動保存
- **柔軟なパラメータ設定**: 動的パラメータ調整によるリアルタイム制御チューニング
- **テレオペ機能**: キーボードおよびジョイスティックによる手動制御

#### 🔧 最新機能強化（2025年1月実装）
**アップデート①: 顔検出アルゴリズムの向上**
- **MediaPipe採用**: Haar Cascade から MediaPipe への移行で検出精度が大幅向上
- **RealSense D435対応**: pyrealsense2 SDK による直接カメラアクセス
- **画像強化処理**: bilateral filter、gamma correction、CLAHE による逆光・暗所対応
- **設定可能な前処理**: `enable_image_enhancement` パラメータで生画像/強化画像を選択可能

**アップデート②: 距離制御機能の追加**
- **前後移動制御**: 深度カメラを使用して人物との距離を測定し、設定距離を維持
- **適応制御**: 距離エラーに応じて移動速度を調整する適応制御機能
- **安全機能**: デッドゾーン設定による振動防止と、人物を見失った際の安全停止

**アップデート③: テレオペレーション機能**
- **キーボード制御**: teleop_twist_keyboard による手動制御
- **ジョイスティック制御**: PS4/Xbox コントローラーによる手動制御
- **起動ファイル統合**: 簡単な起動コマンドでテレオペ機能を利用可能

**アップデート④: 柔軟な制御設定**
- **動的パラメータ調整**: 実行中にリアルタイムでパラメータ変更可能
- **画像処理レベル調整**: 照明条件に応じた最適化設定

#### 📊 パラメータ一覧
| パラメータ名 | 型 | デフォルト値 | 説明 |
| :--- | :--- | :--- | :--- |
| `turn_gain` | Double | 0.003 | P制御の比例ゲイン [rad/s per pixel] |
| `dead_zone_percent` | Integer | 15 | 不感帯幅の画像幅に対する% |
| `target_distance` | Double | 0.5 | 追従時の目標距離 [m] |
| `linear_gain` | Double | 0.8 | 前後移動制御の比例ゲイン |
| `distance_dead_zone` | Double | 0.1 | 距離制御のデッドゾーン [m] |
| `enable_image_enhancement` | Boolean | false | 画像強化処理の有効/無効 |
| `clahe_clip_limit` | Double | 8.0 | CLAHE contrast enhancement clip limit |
| `clahe_grid_size` | Integer | 6 | CLAHE tile grid size |
| `gamma_correction` | Double | 1.5 | Gamma correction value (>1.0 brightens) |
| `enable_bilateral_filter` | Boolean | true | Bilateral filtering for noise reduction |

#### 使用方法

**前提条件**: 
- RealSenseカメラが接続され、カメラトピックが利用可能である必要があります
- Kachakaロボットとの接続が確立されている必要があります

**顔追従システムの実行**:
```bash
cd ~/ws_kachaka
source install/setup.bash

# 顔追従システムの起動（Launch file使用 - 推奨）
ros2 launch my_kachaka_apps face_tracker.launch.py

# または直接ノードを起動
ros2 run my_kachaka_apps face_tracker_node
```

**テレオペレーション機能の使用**:
```bash
# キーボード制御
ros2 launch my_kachaka_apps teleop_keyboard.launch.py

# ジョイスティック制御（PS4/Xboxコントローラー）
ros2 launch my_kachaka_apps teleop_joy.launch.py
```

#### 期待される動作
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

#### 🎛️ パラメータ調整方法

**基本実行（デフォルトパラメータ使用）**:
```bash
ros2 run my_kachaka_apps face_tracker_node
```

**カスタムパラメータでの起動**:
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

**実行中のリアルタイム調整**:
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

**パラメータ確認**:
```bash
# 現在のパラメータ値を確認
ros2 param list /face_tracker_node
ros2 param get /face_tracker_node enable_image_enhancement
ros2 param get /face_tracker_node turn_gain
```

#### 制御コマンドの監視
```bash
# 別ターミナルでKachakaへの制御コマンドを監視
ros2 topic echo /kachaka/manual_control/cmd_vel
```

#### 🔧 トラブルシューティング

**問題: 顔検出が動作しない**
- カメラが接続されているか確認: `ros2 topic list | grep camera`
- カメラデータが配信されているか確認: `ros2 topic echo /camera/camera/color/image_raw --once`
- カメラがアクティブ状態か確認: `ros2 lifecycle get /camera/camera`
- MediaPipeライブラリがインストールされているか確認: `pip3 list | grep mediapipe`
- pyrealsense2がインストールされているか確認: `pip3 list | grep pyrealsense2`

**問題: Kachakaロボットが動作しない**
- Kachaka制御トピックが配信されているか確認: `ros2 topic echo /kachaka/manual_control/cmd_vel`
- Kachakaトピックが利用可能か確認: `ros2 topic list | grep kachaka`
- ロボットがマニュアル制御モードになっているか確認

**問題: ロボットがハンチング（振動）する**
- `turn_gain`を小さくする: `ros2 param set /face_tracker_node turn_gain 0.001`
- `dead_zone_percent`を大きくする: `ros2 param set /face_tracker_node dead_zone_percent 25`

**問題: ロボットの反応が鈍い**
- `turn_gain`を大きくする: `ros2 param set /face_tracker_node turn_gain 0.004`
- `dead_zone_percent`を小さくする: `ros2 param set /face_tracker_node dead_zone_percent 10`

**問題: 処理速度を優先したい**
- 画像強化は既にデフォルトで無効（生画像を使用）
- bilateral filterのみ無効化: `ros2 param set /face_tracker_node enable_bilateral_filter false`

**問題: 暗所や逆光で検出性能が悪い**
- 画像強化を有効化: `ros2 param set /face_tracker_node enable_image_enhancement true`
- gamma correction を上げる: `ros2 param set /face_tracker_node gamma_correction 2.0`
- CLAHE clip limit を上げる: `ros2 param set /face_tracker_node clahe_clip_limit 12.0`

詳細な使用方法と設定については、`src/my_kachaka_apps/README.md` を参照してください。

## トピックの利用方法

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

### Dockerブリッジからのデータアクセス
Dockerブリッジが実行されている場合、以下のコマンドでコンテナ内から直接データにアクセスできます：
```bash
# 実行中のDockerコンテナを確認
docker ps

# コンテナ内でトピックデータを確認
docker exec <container_id> /bin/bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /kachaka/front_camera/image_raw --once"

# コンテナ内でトピック頻度を確認
docker exec <container_id> /bin/bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /kachaka/front_camera/image_raw"
```

## パッケージ詳細

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

## トラブルシューティング

### ビルドエラー: "A required package was not found"

**症状**: `pkg_check_modules` でgRPC++やprotobufが見つからない

**解決方法**:
```bash
sudo apt install -y libgrpc++-dev libprotobuf-dev protobuf-compiler-grpc
```

### ビルドエラー: "gen-src/kachaka-api.grpc.pb.cc: No such file"

**症状**: プロトコルバッファの生成ファイルが見つからない

**解決方法**:
```bash
# プロトコルバッファファイルを生成
~/kachaka-api/tools/generate_proto_for_ros2.sh

# ファイルをワークスペースにコピー
cp -r ~/kachaka-api/ros2/kachaka_grpc_ros2_bridge/gen-src ~/kachaka_ws/src/kachaka_grpc_ros2_bridge/
```

### ビルドエラー: RealSense "fastrtps" target missing

**症状**: `realsense2_camera` パッケージのビルド時に「The following imported targets are referenced, but are missing: fastrtps」エラーが発生

**原因**: Intel RealSense SDK が FastRTPS サポート付きでコンパイルされているが、FastRTPS の cmake ターゲットが見つからない

**解決方法**: 
このエラーは既に修正済みです。`src/realsense-ros/realsense2_camera/CMakeLists.txt` にワークアラウンドが適用されています。それでも問題が発生する場合は：

```bash
# RealSenseパッケージのみを除外してビルド
colcon build --packages-skip realsense2_camera --cmake-args -DUSE_LIFECYCLE_NODE=ON

# または、RealSense SDK を完全に削除
sudo apt remove librealsense2-dev librealsense2-utils
```

**注意**: このワークアラウンドは基本的な機能は提供しますが、RealSense カメラの高度なDDS通信機能が制限される可能性があります。

### 警告: "unused variable 'kPngUnkown'"

**症状**: ビルド時に未使用変数の警告が表示される

**対処**: この警告は機能に影響しないため、無視して構いません。

### Docker権限エラー

**症状**: プロトコルバッファ生成時にDocker権限エラーが発生

**解決方法**:
```bash
# Dockerグループにユーザーを追加
sudo usermod -aG docker $USER
# ログアウト・ログインして権限を反映
```

### RealSenseカメラトピックにデータが流れない

**症状**: `/camera/camera/color/image_raw` などのRealSenseカメラトピックでデータが取得できない

**原因**: RealSenseカメラがLifecycleNodeとして起動しており、手動でのアクティベーションが必要

**解決方法**:

1. **LifecycleNodeをアクティベート**:
   ```bash
   # ノードを設定
   ros2 lifecycle set /camera/camera configure
   
   # ノードをアクティブ化
   ros2 lifecycle set /camera/camera activate
   ```

2. **ノードの状態を確認**:
   ```bash
   # 現在の状態を確認（"active"になっているか確認）
   ros2 lifecycle get /camera/camera
   ```

3. **トピック一覧を確認**:
   ```bash
   # カメラトピックが表示されるか確認
   ros2 topic list | grep camera
   ```

### 画像トピックにデータが流れない（Kachaka関連）

**症状**: `/kachaka/front_camera/image_raw` などの画像トピックでデータが取得できない

**原因**: DockerブリッジとローカルROS2環境でRMW実装が異なる、またはネットワーク分離の問題

**解決方法**:

1. **CycloneDDS RMWをインストール**:
   ```bash
   sudo apt install ros-humble-rmw-cyclonedds-cpp
   ```

2. **環境変数を設定**:
   ```bash
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   export ROS_DOMAIN_ID=0
   source ~/kachaka_ws/install/setup.bash
   ```

3. **Dockerコンテナから直接アクセス**:
   ```bash
   # コンテナIDを確認
   docker ps
   
   # コンテナ内でデータを確認
   docker exec <container_id> /bin/bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /kachaka/front_camera/image_raw --once"
   ```

### トピックは見えるがデータが流れない

**症状**: `ros2 topic list` でトピックは表示されるが、`ros2 topic echo` でデータが取得できない

**原因**: Kachakaロボットに接続されていない、またはRMW実装の不一致

**解決方法**:
1. Kachakaロボットが起動しており、ネットワーク接続されていることを確認
2. gRPCブリッジが正常に動作していることを確認:
   ```bash
   docker logs <container_id>
   ```
3. RMW実装とドメインIDを一致させる

### QoS互換性警告

**症状**: `offering incompatible QoS` 警告が表示される

**対処**: この警告は正常で、Dockerブリッジとローカル環境でQoS設定が異なることを示します。機能に影響はありません。

## 開発者向け情報

### パッケージ構造
```
kachaka_ws/
├── src/
│   ├── kachaka_grpc_ros2_bridge/
│   │   ├── gen-src/           # 自動生成されるプロトコルバッファファイル
│   │   ├── src/               # ソースコード
│   │   └── launch/            # 起動ファイル
│   ├── kachaka_interfaces/    # メッセージ・アクション定義
│   ├── kachaka_description/   # ロボットモデル
│   ├── kachaka_follow/        # サンプルノード
│   └── kachaka_nav2_bringup/  # ナビゲーション設定
├── build/                     # ビルド結果
├── install/                   # インストール結果
└── log/                       # ビルドログ
```

### 依存関係
- **ROS2パッケージ**: rclcpp, sensor_msgs, nav_msgs, tf2_ros, cv_bridge
- **システムライブラリ**: gRPC++, protobuf, OpenCV
- **外部プロジェクト**: Kachaka API (~/kachaka-api)

## ライセンス

各パッケージは以下のライセンスに従います：
- kachaka_grpc_ros2_bridge: Apache License 2.0
- その他のパッケージ: 各パッケージのpackage.xmlを参照

## 便利なスクリプト

### 環境設定スクリプト
以下のスクリプトを `~/setup_kachaka.sh` として保存すると便利です：

```bash
#!/bin/bash
# Kachaka ROS2環境設定スクリプト

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
export FRAME_PREFIX="kachaka"

source /opt/ros/humble/setup.bash
source ~/kachaka_ws/install/setup.bash

echo "Kachaka ROS2環境が設定されました！"
echo ""
echo "利用可能なコマンド："
echo "  ros2 topic list                     # トピック一覧"
echo "  ros2 node list                      # ノード一覧"
echo "  ros2 topic echo /kachaka/lidar/scan # LIDARデータ表示"
echo "  ros2 run kachaka_follow follow      # フォローノード実行"
echo ""
echo "Dockerブリッジコマンド："
echo "  docker ps                           # コンテナ確認"
echo "  docker exec <container_id> /bin/bash -c \"source /opt/ros/humble/setup.bash && ros2 topic list\""
```

使用方法：
```bash
chmod +x ~/setup_kachaka.sh
source ~/setup_kachaka.sh
```

### 診断スクリプト
システムの状態を確認するスクリプト：

```bash
#!/bin/bash
# Kachaka システム診断スクリプト

echo "=== Kachaka ROS2 システム診断 ==="
echo ""

echo "1. ROS2環境変数："
echo "   ROS_DISTRO: $ROS_DISTRO"
echo "   ROS_DOMAIN_ID: $ROS_DOMAIN_ID"
echo "   RMW_IMPLEMENTATION: $RMW_IMPLEMENTATION"
echo "   FRAME_PREFIX: $FRAME_PREFIX"
echo ""

echo "2. Kachakaパッケージ："
ros2 pkg list | grep kachaka
echo ""

echo "3. 実行中のDockerコンテナ："
docker ps --filter "name=ros2_bridge" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "4. ROS2ノード："
ros2 node list 2>/dev/null || echo "   ノードが見つかりません"
echo ""

echo "5. 主要トピック："
echo "   カメラトピック："
ros2 topic list 2>/dev/null | grep camera | head -5
echo "   センサートピック："
ros2 topic list 2>/dev/null | grep -E "(lidar|imu|odometry)" | head -5
echo ""

echo "診断完了"
```

## サポート

問題が発生した場合は、以下を確認してください：

1. **全ての前提条件がインストールされているか**
   - CycloneDDS RMW実装を含む
2. **Kachaka APIが正しい場所に配置されているか**
   - `~/kachaka-api` ディレクトリの存在確認
3. **プロトコルバッファファイルが正しく生成されているか**
   - `gen-src/` ディレクトリの存在確認
4. **環境変数が正しく設定されているか**
   - RMW_IMPLEMENTATION, ROS_DOMAIN_ID, FRAME_PREFIX
5. **Dockerブリッジが正常に動作しているか**
   - `docker ps` でコンテナ状態を確認
   - `docker logs <container_id>` でログを確認

### よくある問題と解決策

| 問題 | 解決策 |
|------|--------|
| トピックが見えない | ROS_DOMAIN_IDとRMW_IMPLEMENTATIONを確認 |
| 画像データが取得できない | Dockerコンテナから直接アクセスを試す |
| ビルドエラー | 依存パッケージのインストール状況を確認 |
| QoS警告 | 無視して構わない（正常な動作） |

それでも問題が解決しない場合は、ビルドログ (`log/` ディレクトリ) を確認してください。