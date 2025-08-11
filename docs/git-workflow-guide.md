# Gitワークフローガイド: コミット → プルリクエスト → レビュー → マージ

このドキュメントでは、Gitを使用した開発ワークフローの完全な流れを日本語で説明します。

## 📋 目次

1. [基本的なワークフロー概要](#基本的なワークフロー概要)
2. [ステップ1: 変更内容の確認](#ステップ1-変更内容の確認)
3. [ステップ2: ステージングエリアに変更を追加](#ステップ2-ステージングエリアに変更を追加)
4. [ステップ3: コミットの作成](#ステップ3-コミットの作成)
5. [ステップ4: 変更のプッシュ](#ステップ4-変更のプッシュ)
6. [ステップ5: プルリクエストの作成](#ステップ5-プルリクエストの作成)
7. [ステップ6: コードレビュープロセス](#ステップ6-コードレビュープロセス)
8. [ステップ7: レビューフィードバックへの対応](#ステップ7-レビューフィードバックへの対応)
9. [ステップ8: プルリクエストのマージ](#ステップ8-プルリクエストのマージ)
10. [完全なワークフロー例](#完全なワークフロー例)
11. [プロのコツと技](#プロのコツと技)

## 基本的なワークフロー概要

```
作業 → ステージング → コミット → プッシュ → プルリクエスト → レビュー → マージ
```

## ステップ1: 変更内容の確認

### 現在の状態を確認
```bash
# どのファイルが変更されたかを確認
git status

# 実際の変更内容を詳細に確認
git diff

# 最近のコミット履歴を確認
git log --oneline -5

# 特定のファイルの変更のみ確認
git diff README.md

# ブランチの情報を確認
git branch -a
```

### 確認すべき項目
- ✅ 意図した変更のみが含まれているか
- ✅ 不要なファイル（一時ファイル、設定ファイルなど）が含まれていないか
- ✅ 機密情報（パスワード、IPアドレスなど）が含まれていないか

## ステップ2: ステージングエリアに変更を追加

### 個別ファイルの追加
```bash
# 特定のファイルをステージング
git add README.md
git add src/kachaka_nav2_bringup/params/nav2_params.yaml
git add src/my_kachaka_apps/scripts/face_detection_prototype.py

# ディレクトリ全体を追加
git add src/my_kachaka_apps/scripts/

# 変更されたファイルのみ追加（新規ファイルは除く）
git add -u

# すべての変更を追加（新規ファイル含む）
git add -A
# または
git add .
```

### ステージング状態の確認
```bash
# ステージされたファイルを確認
git status

# ステージされた変更の内容を確認
git diff --staged
```

### ステージングの取り消し
```bash
# 特定ファイルのステージングを取り消し
git restore --staged README.md

# すべてのステージングを取り消し
git restore --staged .
```

## ステップ3: コミットの作成

### 基本的なコミット
```bash
# シンプルなコミットメッセージ
git commit -m "顔検出プロトタイプとナビゲーション設定の更新"

# 詳細なコミットメッセージ
git commit -m "顔検出プロトタイプとナビゲーション設定の更新

- MediaPipeを使用したRealSense D435i対応の顔検出スクリプトを追加
- ナビゲーション性能向上のためNav2コストマップパラメータを更新
- ミッションコントローラーに状態パブリッシング機能を追加
- ナビゲーション設定のパラメータタイプ問題を修正"
```

### インタラクティブなコミット
```bash
# エディタでコミットメッセージを作成
git commit

# 変更の一部のみをコミット（対話式）
git add -p
```

### 良いコミットメッセージの書き方
```bash
# 形式: <タイプ>: <件名>
# 
# <詳細説明>

# タイプの例:
# feat: 新機能追加
# fix: バグ修正
# docs: ドキュメント変更
# style: フォーマット変更
# refactor: リファクタリング
# test: テスト追加
# chore: メンテナンス作業

# 良い例:
git commit -m "feat: MediaPipeによる顔検出機能を追加"
git commit -m "fix: ナビゲーションパラメータのタイプミスマッチを解決"
git commit -m "docs: インストールガイドでREADMEを更新"
```

## ステップ4: 変更のプッシュ

### 基本的なプッシュ
```bash
# 現在のブランチをプッシュ
git push

# 初回プッシュの場合（上流ブランチを設定）
git push -u origin track

# 特定のブランチにプッシュ
git push origin feature/face-detection
```

### プッシュ前の確認
```bash
# プッシュ前にリモートの状態を確認
git fetch
git status

# リモートとの差分を確認
git log origin/main..HEAD --oneline
```

## ステップ5: プルリクエストの作成

### 方法A: GitHub CLI使用（推奨）
```bash
# GitHub CLIがインストールされている場合
gh pr create \
  --title "顔検出とナビゲーションの改善" \
  --body "## 変更内容
- RealSenseカメラ対応のMediaPipe顔検出プロトタイプを追加
- ロボットナビゲーション改善のためNav2コストマップパラメータを更新
- 状態パブリッシング機能付きでミッションコントローラーを強化
- ナビゲーションパラメータタイプの問題を修正

## テスト済み
- model_selection=0とmodel_selection=1の両方で顔検出をテスト
- ナビゲーションシステムのクラッシュなし起動を確認
- RealSenseカメラ統合の動作を確認"

# ドラフトPRとして作成
gh pr create --draft --title "WIP: 顔検出機能の実装"

# 特定の人にレビューを依頼
gh pr create --reviewer username1,username2
```

### 方法B: GitHub Webインターフェース
1. **GitHubのリポジトリページにアクセス**
2. **「Pull requests」タブをクリック**
3. **「New pull request」をクリック**
4. **ブランチを選択:**
   - Base branch: `main`（またはターゲットブランチ）
   - Compare branch: `track`（あなたの作業ブランチ）
5. **PR詳細を入力:**
   - タイトル: 「顔検出とナビゲーションの改善」
   - 説明: 変更内容と理由を詳しく説明
6. **「Create pull request」をクリック**

### PRテンプレートの例
```markdown
## 概要
この変更の目的を簡潔に説明してください。

## 変更内容
- [ ] 新機能の追加
- [ ] バグ修正
- [ ] ドキュメント更新
- [ ] リファクタリング

## 具体的な変更
- ファイル1: 説明
- ファイル2: 説明

## テスト
- [ ] 既存テストが通ることを確認
- [ ] 新しいテストを追加
- [ ] 手動テストを実施

## スクリーンショット
必要に応じて画像を添付

## レビュー観点
レビュアーに特に見てもらいたい点

## 関連するIssue
Fixes #123
```

## ステップ6: コードレビュープロセス

### セルフレビューチェックリスト
```bash
# PR作成前に自分の変更をレビュー
git diff main...track

# 確認項目:
# ✅ コミットメッセージは明確か？
# ✅ すべてのファイルがコンパイル/実行できるか？
# ✅ 機密データ（パスワード、IP）が含まれていないか？
# ✅ コードが適切にフォーマットされているか？
# ✅ 不要なデバッグコードが残っていないか？
```

### レビューアーの観点
- **機能性**: コードが意図した通りに動作するか
- **可読性**: コードが理解しやすいか
- **保守性**: 将来の変更に対応しやすいか
- **性能**: パフォーマンスに問題ないか
- **セキュリティ**: セキュリティホールがないか
- **テスト**: 適切にテストされているか

### 一般的なレビューコメントと対応
```bash
# よくあるレビューコメント例:
# "この処理のロジックにコメントを追加してください"
# "この関数が長すぎます。分割を検討してください"
# "このケースでのエラーハンドリングが不足しています"
# "LGTM! (Looks Good To Me)"
```

## ステップ7: レビューフィードバックへの対応

### フィードバック対応の流れ
```bash
# 1. レビューコメントを確認
# GitHub上でコメントを読む

# 2. コードを修正
# ファイルを編集...

# 3. 修正をコミット
git add .
git commit -m "レビューフィードバック対応: エラーハンドリングとコメントを追加"

# 4. プッシュ（PRが自動更新される）
git push

# 5. レビューアーに返答
# GitHub上でコメントに返信
```

### 効果的なフィードバック対応
```bash
# 小さな修正は一つのコミットにまとめる
git add .
git commit -m "code review: 変数名の修正とコメント追加"

# 大きな変更は複数のコミットに分ける
git commit -m "refactor: 長い関数を複数の関数に分割"
git commit -m "feat: エラーハンドリング機能を追加"
git commit -m "docs: 新機能のドキュメントを追加"
```

### 議論が必要な場合
```bash
# GitHub上でディスカッション開始
# コメント例:
# "この実装についてですが、パフォーマンス上の理由でこのアプローチを選択しました。
# 別のアプローチをお考えでしたら、ご提案いただけますでしょうか？"
```

## ステップ8: プルリクエストのマージ

### 方法A: GitHub Webインターフェース
1. **PRページにアクセス**
2. **「Merge pull request」をクリック**（承認後）
3. **マージタイプを選択:**
   - **Merge commit**: 完全な履歴を保持
   - **Squash and merge**: すべてのコミットを1つにまとめる
   - **Rebase and merge**: コミットを線形に再配置
4. **「Confirm merge」をクリック**

### 方法B: コマンドライン
```bash
# メインブランチに切り替え
git checkout main

# 最新の変更を取得
git pull origin main

# フィーチャーブランチをマージ
git merge track

# マージした変更をプッシュ
git push origin main

# 作業ブランチをクリーンアップ
git branch -d track
git push origin --delete track
```

### マージタイプの選択指針

#### Merge Commit
```bash
# 使用場面: チーム開発、履歴保持が重要
git merge --no-ff feature/face-detection
```
- ✅ 完全な開発履歴が残る
- ✅ フィーチャーブランチの存在が明確
- ❌ 履歴が複雑になる可能性

#### Squash and Merge
```bash
# 使用場面: 細かいコミットをまとめたい
git merge --squash feature/face-detection
git commit -m "feat: 顔検出機能の完全実装"
```
- ✅ クリーンな履歴
- ✅ 論理的な単位でのコミット
- ❌ 詳細な開発過程が失われる

#### Rebase and Merge
```bash
# 使用場面: 線形の履歴を維持したい
git rebase main feature/face-detection
git checkout main
git merge feature/face-detection
```
- ✅ 線形で美しい履歴
- ✅ 個別コミットが保持される
- ❌ 複雑で間違いやすい

## 完全なワークフロー例

### 実際の作業例
```bash
# 1. 現状確認
git status
git diff

# 2. 変更をステージング
git add README.md
git add src/kachaka_nav2_bringup/params/nav2_params.yaml
git add src/my_kachaka_apps/scripts/

# 3. コミット作成
git commit -m "顔検出プロトタイプとナビゲーション改善

- BlazeFaceモデルを使用したMediaPipe顔検出を実装
- ナビゲーション改善のためNav2コストマップ膨張半径を更新
- RealSense D435iカメラ統合を追加
- ナビゲーションパラメータタイプの問題を修正"

# 4. プッシュ
git push -u origin track

# 5. プルリクエスト作成（GitHub Web UIで）
# GitHub → Pull requests → New pull request

# 6. レビューと承認後
git checkout main
git pull origin main
git merge track
git push origin main
git branch -d track
```

## プロのコツと技

### ブランチ管理
```bash
# フィーチャーブランチ作成
git checkout -b feature/face-detection

# ブランチ間の切り替え
git checkout main
git checkout feature/face-detection

# ブランチリスト表示
git branch -a

# リモートブランチの情報更新
git fetch --prune

# ブランチ削除
git branch -d feature/face-detection
git push origin --delete feature/face-detection
```

### 便利なGitコマンド
```bash
# 最後のコミットを修正（メッセージのみ）
git commit --amend -m "新しいコミットメッセージ"

# 最後のコミットを取り消し（変更は保持）
git reset --soft HEAD~1

# 最後のコミットを完全に取り消し
git reset --hard HEAD~1

# ファイルの変更を取り消し
git checkout -- filename.py
# または
git restore filename.py

# 特定のコミットの変更を確認
git show commit-hash

# コミット履歴をグラフで表示
git log --oneline --graph --all

# 誰がいつ変更したかを確認
git blame filename.py

# 変更を一時保存
git stash
git stash pop

# コンフリクト解決後
git add conflicted-file.py
git commit -m "merge: コンフリクト解決"
```

### .gitignore設定例
```bash
# .gitignoreファイルを作成
cat > .gitignore << EOF
# コンパイル済みファイル
*.pyc
__pycache__/
*.so

# IDE設定
.vscode/
.idea/
*.swp
*.swo

# ROS2関連
install/
build/
log/

# システムファイル
.DS_Store
Thumbs.db

# 一時ファイル
*.tmp
*.bak
*~

# 機密ファイル
*.key
*.pem
secrets.yaml
EOF
```

### チーム開発のベストプラクティス

#### コミットメッセージの統一
```bash
# プロジェクトで統一されたフォーマットを使用
git config --global commit.template ~/.gitmessage

# ~/.gitmessageファイル例:
# <type>(<scope>): <subject>
# 
# <body>
# 
# <footer>
```

#### プルリクエストのルール
- 🎯 **1PR1機能**: 一つのPRには一つの機能変更のみ
- 📝 **明確な説明**: 変更理由と影響を明記
- 🧪 **テスト必須**: 変更に対応するテストを含める
- 👥 **レビュー必須**: 最低1人のレビューを受ける
- 🔍 **セルフレビュー**: PR作成前に自分でコードレビュー

#### コードレビューの心得
```bash
# レビュアーとして:
# - 建設的なフィードバックを心がける
# - コードの背景を理解する
# - 迅速にレビューする

# 作成者として:
# - フィードバックを受け入れる姿勢
# - 説明責任を果たす
# - 感謝の気持ちを示す
```

## トラブルシューティング

### よくある問題と解決法

#### コンフリクトの解決
```bash
# マージコンフリクトが発生した場合
git status  # コンフリクトファイルを確認

# ファイルを手動編集してコンフリクトマーカーを削除
# <<<<<<<, =======, >>>>>>> を削除

# 解決後
git add conflicted-file.py
git commit -m "resolve: マージコンフリクトを解決"
```

#### 間違ったコミットの修正
```bash
# 最新コミットのメッセージ修正
git commit --amend -m "正しいコミットメッセージ"

# コミット履歴の修正（注意して使用）
git rebase -i HEAD~3  # 最新3コミットを編集

# 変更を強制プッシュ（チーム開発では避ける）
git push --force-with-lease origin branch-name
```

#### 誤って削除したブランチの復旧
```bash
# 削除されたブランチの復旧
git reflog  # 削除前のコミットハッシュを確認
git checkout -b recovered-branch commit-hash
```

## まとめ

このワークフローを習得することで、効率的で安全なチーム開発が可能になります。

### 重要なポイント
1. **小さく頻繁にコミット** - 変更を小分けにする
2. **明確なメッセージ** - 将来の自分やチームが理解できるように
3. **丁寧なレビュー** - コードの品質向上のために
4. **継続的な学習** - Gitの機能を徐々に覚えていく

### 参考資料
- [Pro Git Book（日本語版）](https://git-scm.com/book/ja/v2)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/ja/v1.0.0/)

---

**Happy Coding! 🚀**

このガイドを参考に、効率的な開発ワークフローを構築してください。