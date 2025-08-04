# Kachaka ROS2 Workspace

このワークスペースは、Kachaka ロボット用のROS2パッケージ群を含んでいます。

## 概要

このワークスペースには以下のパッケージが含まれています：

- **kachaka_grpc_ros2_bridge**: Kachaka API と ROS2 の間のgRPCブリッジ
- **kachaka_interfaces**: Kachakaシステム用のカスタムROS2メッセージとアクション定義
- **kachaka_description**: Kachakaロボットの3DモデルとURDF記述
- **kachaka_follow**: LIDARを使用して最も近いオブジェクトに向かって移動するサンプルノード
- **kachaka_nav2_bringup**: Nav2ナビゲーションスタック用の起動ファイルと設定

## 前提条件

### システム要件
- Ubuntu 22.04 LTS
- ROS2 Humble Hawksbill
- Docker (プロトコルバッファファイル生成用)

### 必要なパッケージ
```bash
sudo apt update
sudo apt install -y \
    libgrpc++-dev \
    libprotobuf-dev \
    protobuf-compiler-grpc \
    libopencv-dev \
    ros-humble-rmw-cyclonedds-cpp
```

### RMW実装の設定
KachakaのDockerブリッジとの互換性のため、CycloneDDSを使用することを推奨します：
```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
```

### Kachaka API
このワークスペースをビルドするには、Kachaka APIリポジトリが必要です：
```bash
# ~/kachaka-api ディレクトリにKachaka APIが配置されていることを確認してください
ls ~/kachaka-api/protos/kachaka-api.proto
```

## セットアップ手順

### 1. ワークスペースの準備
```bash
cd ~/kachaka_ws
source /opt/ros/humble/setup.bash
```

### 2. プロトコルバッファファイルの生成
```bash
# Kachaka APIからプロトコルバッファファイルを生成
~/kachaka-api/tools/generate_proto_for_ros2.sh

# 生成されたファイルをワークスペースにコピー
cp -r ~/kachaka-api/ros2/kachaka_grpc_ros2_bridge/gen-src ~/kachaka_ws/src/kachaka_grpc_ros2_bridge/
```

### 3. ビルド
```bash
cd ~/kachaka_ws
colcon build
```

### 4. 環境の設定
```bash
source install/setup.bash
```

## 使用方法

### Kachaka gRPCブリッジの起動

#### 方法1: Dockerブリッジ（推奨）
```bash
# Kachaka APIブリッジをDockerで起動
cd ~/kachaka-api/tools/ros2_bridge
./start_bridge.sh <KachakaのIPアドレス>

# 例: ./start_bridge.sh 192.168.1.100
```

#### 方法2: ネイティブブリッジ
```bash
# ワークスペースから直接起動
export FRAME_PREFIX="kachaka"
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
source ~/kachaka_ws/install/setup.bash
ros2 launch kachaka_grpc_ros2_bridge grpc_ros2_bridge.launch.xml server_uri:="<KachakaのIPアドレス>:26400"
```

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

### 画像トピックにデータが流れない

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