# Kachaka Follow Node

## 概要

このパッケージは、Kachakaロボットがカメラで人を検出し、LIDARで最も近い障害物を検知して人を追従するROS2ノードです。

### 主な機能
- **人検出**: カメラによる物体検出で人を識別
- **LIDAR追従**: 最も近い障害物（人）に向かって移動
- **安全制御**: 一定距離を保って追従

## 前提条件

### システム要件
- Ubuntu 22.04 LTS
- ROS2 Humble Hawksbill
- Python 3.10+

### 必要なパッケージ
```bash
# ROS2パッケージ
sudo apt install ros-humble-rmw-cyclonedx-cpp

# Pythonパッケージ
pip3 install angles
```

### 依存するKachakaパッケージ
- `kachaka_interfaces`: カスタムメッセージ定義
- `kachaka_grpc_ros2_bridge`: KachakaとROS2の通信ブリッジ

## セットアップ

### 1. ワークスペースの準備
```bash
cd ~/kachaka_ws
source /opt/ros/humble/setup.bash
```

### 2. 環境変数の設定
```bash
export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
export ROS_DOMAIN_ID=0
export FRAME_PREFIX="kachaka"
```

### 3. ビルド
```bash
colcon build --packages-select kachaka_follow
source install/setup.bash
```

## 実行方法

### 1. Kachaka gRPCブリッジの起動
```bash
# Dockerブリッジを使用（推奨）
cd ~/kachaka-api/tools/ros2_bridge
./start_bridge.sh <KachakaのIPアドレス>
```

### 2. フォローノードの実行
```bash
ros2 run kachaka_follow follow
```

## ノードの仕様

### 購読するトピック
- `/kachaka/lidar/scan` (sensor_msgs/LaserScan): LIDAR距離データ
- `/kachaka/object_detection/result` (kachaka_interfaces/ObjectDetectionListStamped): 物体検出結果

### 配信するトピック
- `/kachaka/manual_control/cmd_vel` (geometry_msgs/Twist): 移動指令

### パラメータ
- `MAX_RANGE_FOR_FOLLOW`: 追従開始距離 (1.0m)
- `ANGULAR_TOLERANCE`: 角度許容範囲 (0.8rad)

## 動作ロジック

1. **人検出チェック**: カメラで人が検出されているかを確認
2. **角度調整**: 最も近い障害物の方向に回転
3. **前進**: 障害物が追従距離内にある場合は前進

## トラブルシューティング

### よくある問題と解決策

#### 1. QoS互換性警告
**症状**: 
```
[WARN] New publisher discovered on topic '/kachaka/lidar/scan', offering incompatible QoS
```

**解決策**: 
このパッケージでは既にQoS設定を最適化済みです。警告は無視して構いません。

#### 2. "no person" が継続表示される
**症状**: 
```
[INFO] [follow]: no person
```

**原因と解決策**:
- Kachaka gRPCブリッジが起動していない → ブリッジを起動
- カメラが人を検出していない → 人がカメラの視野内にいることを確認
- トピックにデータが流れていない → `ros2 topic echo /kachaka/object_detection/result` で確認

#### 3. パッケージが見つからない
**症状**:
```bash
Package 'kachaka_follow' not found
```

**解決策**:
```bash
# ワークスペースを再ビルド
colcon build --packages-select kachaka_follow
source install/setup.bash
```

#### 4. 依存パッケージエラー
**症状**:
```
ModuleNotFoundError: No module named 'angles'
```

**解決策**:
```bash
pip3 install angles
```

### デバッグ用コマンド

#### トピック確認
```bash
# 利用可能なトピック一覧
ros2 topic list

# LIDAR データの確認
ros2 topic echo /kachaka/lidar/scan --once

# 物体検出結果の確認  
ros2 topic echo /kachaka/object_detection/result --once

# 移動指令の確認
ros2 topic echo /kachaka/manual_control/cmd_vel
```

#### ノード情報確認
```bash
# 実行中のノード一覧
ros2 node list

# ノードの詳細情報
ros2 node info /follow
```

## 設定ファイル

### 便利な環境設定スクリプト
`~/setup_kachaka_follow.sh` として保存:

```bash
#!/bin/bash
# Kachaka Follow環境設定スクリプト

export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
export ROS_DOMAIN_ID=0  
export FRAME_PREFIX="kachaka"

source /opt/ros/humble/setup.bash
source ~/kachaka_ws/install/setup.bash

echo "Kachaka Follow環境が設定されました！"
echo ""
echo "実行コマンド:"
echo "  ros2 run kachaka_follow follow"
```

使用方法:
```bash
chmod +x ~/setup_kachaka_follow.sh
source ~/setup_kachaka_follow.sh
```

## コードの改良点

### 実装済みの修正
- **QoS互換性の改善**: `BEST_EFFORT`信頼性ポリシーを使用してセンサーデータとの互換性を向上
- **型安全性**: 適切な型ヒントを追加

### 今後の改善案
- パラメータ化: 追従距離や角度許容範囲を動的に変更可能に
- エラーハンドリング: センサーデータの異常値に対する対処
- 複数人対応: 最も近い人を選択的に追従

## ライセンス

Apache License 2.0

## サポート

問題が発生した場合は、以下を確認してください:
1. 全ての依存パッケージがインストールされているか
2. Kachaka gRPCブリッジが正常に動作しているか  
3. 環境変数が正しく設定されているか
4. ロボットがネットワークに接続されているか

