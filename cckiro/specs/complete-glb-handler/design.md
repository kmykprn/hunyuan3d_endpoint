# GLBファイル処理完成の設計

## アーキテクチャ設計

### 処理フロー
```
1. 外部API呼び出し
   ↓
2. GLBファイルURL取得
   ↓
3. GLBファイル一時ダウンロード
   ↓
4. テクスチャ抽出・Base64エンコード
   ↓
5. 結果返却（URL + Base64テクスチャ）
   ↓
6. 一時ファイルクリーンアップ
```

## モジュール設計

### 1. rp_handler.py（メインハンドラー）

#### 責務
- RunPodイベントの受け取り
- 外部API（Synexa）の呼び出し
- GLB処理の統括
- エラーハンドリング
- レスポンスの生成

#### 主要関数の更新

```python
def handler(event):
    """
    外部APIから3Dモデルを取得し、GLBファイルURLとテクスチャを返却
    
    Args:
        event: RunPodイベント
            - input.image_path: 入力画像のパス
            - input.prompt: プロンプト
            - input.timeout: タイムアウト時間
    
    Returns:
        dict: 
            成功時: {
                "glb_url": str,  # GLBファイルのURL
                "textures": list  # Base64エンコードされたテクスチャのリスト
            }
            エラー時: {
                "error": str  # エラーメッセージ
            }
    """
```

### 2. utils/glb_utils.py（ユーティリティ関数）

#### 既存関数（変更なし）
- `fetch_glb_from_url()`: GLBファイルをダウンロード
- `extract_texture_from_glb()`: テクスチャを抽出

#### 新規追加関数

```python
def encode_textures_to_base64(texture_paths: list[str]) -> list[dict]:
    """
    テクスチャファイルをBase64エンコード
    
    Args:
        texture_paths: テクスチャファイルのパスリスト
    
    Returns:
        list[dict]: [
            {
                "data": "Base64エンコードされたデータ",
                "filename": "ファイル名"
            }
        ]
    """
```

## データフロー設計

### 1. 入力データ
```json
{
    "input": {
        "image_path": "画像のパスまたはURL",
        "prompt": "生成プロンプト",
        "timeout": 300
    }
}
```

### 2. 外部API応答
```python
output = [
    File(url="https://...textured_mesh.glb"),
    File(url="https://...other_files")
]
```

### 3. 内部処理データ
```python
# GLBファイルダウンロード後
glb_dir = "e9d16206-de03-4dbc-97d7-6a17c4c86e1e"
glb_filename = "textured_mesh.glb"

# テクスチャ抽出後
textures_path = [
    "e9d16206-de03-4dbc-97d7-6a17c4c86e1e/texture_0.png",
    "e9d16206-de03-4dbc-97d7-6a17c4c86e1e/texture_1.png"
]
```

### 4. 出力データ

#### 成功時
```json
{
    "glb_url": "https://example.com/textured_mesh.glb",
    "textures": [
        {
            "data": "iVBORw0KGgoAAAANSUhEUgA...",
            "filename": "texture_0.png"
        },
        {
            "data": "iVBORw0KGgoAAAANSUhEUgA...",
            "filename": "texture_1.png"
        }
    ]
}
```

#### エラー時
```json
{
    "error": "具体的なエラーメッセージ"
}
```

## エラーハンドリング設計

### エラーケース
1. **APIキー未設定**
   - ValueError: "SYNEXA_API_KEY not found"
   
2. **外部API呼び出し失敗**
   - エラーステータスとメッセージを返却
   
3. **GLBファイルダウンロード失敗**
   - URLError/HTTPError処理
   
4. **テクスチャ抽出失敗**
   - pygltflibのエラー処理
   
5. **Base64エンコード失敗**
   - メモリ不足/ファイル読み込みエラー

### エラーレスポンス形式
```python
{
    "error": "具体的なエラーメッセージ"
}
```

### 実装パターン
```python
def handler(event):
    try:
        # 正常処理
        # ...
        return {
            "glb_url": glb_url,
            "textures": textures
        }
    except Exception as e:
        # エラー時のみerrorキーを含める
        return {
            "error": str(e)
        }
```

## メモリ管理設計

### 1. ストリーミング処理
- 大きなファイルの読み込みはチャンク単位で処理
- Base64エンコードは必要に応じてストリーミング対応

### 2. 一時ファイルクリーンアップ
- `runpod.serverless.utils.rp_cleanup.clean()`を使用
- 処理完了後、即座に一時ディレクトリを削除
- エラー発生時も必ずクリーンアップを実行（try-finally）

### 3. メモリ使用量の最適化
- GLBファイル本体はBase64エンコードしない（URLのみ返却）
- テクスチャのみBase64エンコード（通常数MB程度）

## セキュリティ設計

### 1. APIキー管理
- 環境変数からAPIキーを取得
- ローカル実行時: `.env`ファイル
- RunPod実行時: Secretsから取得

### 2. ファイルパス検証
- 一時ディレクトリ外へのアクセスを防止
- ファイル名のサニタイズ

### 3. エラー情報の制限
- 内部実装の詳細を露出しない
- スタックトレースは返却しない

## パフォーマンス最適化

### 1. 通信量削減
- GLBファイル本体はURLのみ返却（数十MB〜100MBの転送を回避）
- テクスチャのみBase64エンコード（数MB程度）

### 2. 並列処理
- 複数テクスチャのBase64エンコードは並列化可能（将来的な拡張）

### 3. キャッシュ戦略
- 同一リクエストの結果をキャッシュ（将来的な拡張）

## 依存関係

### 外部ライブラリ
- `runpod`: RunPodサーバーレス環境
- `synexa`: 外部API クライアント
- `pygltflib`: GLBファイル処理
- `urllib`: ファイルダウンロード

### Python標準ライブラリ
- `os`: ファイルシステム操作
- `base64`: Base64エンコード
- `glob`: ファイルパターンマッチング

## テスト設計

### 単体テスト
1. `test_encode_textures_to_base64()`: Base64エンコード機能
2. `test_error_handling()`: 各種エラーケース
3. `test_response_format()`: レスポンス形式の検証

### 統合テスト
1. モックAPIレスポンスでの全体フロー
2. サンプルGLBファイルでの処理確認
3. メモリリーク検証