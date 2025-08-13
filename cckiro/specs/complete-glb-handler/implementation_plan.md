# GLBファイル処理完成の実装計画

## 実装ステップ

### ステップ1: utils/glb_utils.pyへの新規関数追加
**ファイル**: `utils/glb_utils.py`
**作業内容**:
1. `encode_textures_to_base64()`関数を新規追加
2. base64ライブラリのimport追加
3. ファイル読み込みとBase64エンコード処理の実装

**実装詳細**:
```python
import base64

def encode_textures_to_base64(texture_paths: list[str]) -> list[dict]:
    """
    テクスチャファイルをBase64エンコード
    
    Args:
        texture_paths: テクスチャファイルのパスリスト
    
    Returns:
        list[dict]: Base64エンコードされたテクスチャデータのリスト
    """
    textures = []
    for texture_path in texture_paths:
        with open(texture_path, 'rb') as f:
            texture_data = f.read()
            encoded_data = base64.b64encode(texture_data).decode('utf-8')
            filename = os.path.basename(texture_path)
            textures.append({
                "data": encoded_data,
                "filename": filename
            })
    return textures
```

### ステップ2: rp_handler.pyのメイン処理更新
**ファイル**: `rp_handler.py`
**作業内容**:
1. import文の追加（encode_textures_to_base64）
2. handler関数の処理フロー更新
3. try-exceptによるエラーハンドリング実装
4. 一時ファイルのクリーンアップ処理追加

**実装詳細**:
```python
from utils.glb_utils import fetch_glb_from_url, extract_texture_from_glb, encode_textures_to_base64

def handler(event):
    """
    外部APIから3Dモデルを取得する
    """
    glb_dir = None
    
    try:
        # 入力値を取得
        input_data = event['input']
        image_path = input_data.get('image_path')
        prompt = input_data.get('prompt', '')
        timeout = input_data.get('timeout', 300)
        
        # 入力検証
        if not image_path:
            raise ValueError("image_path is required")

        # 外部APIにリクエストを投げる
        output = client.run(
            "tencent/hunyuan3d-2",
            input={
                "seed": 1234,
                "image": image_path,
                "steps": 5,
                "caption": prompt,
                "shape_only": False,
                "guidance_scale": 5.5,
                "multiple_views": [],
                "check_box_rembg": True,
                "octree_resolution": "256"
            },
            wait=timeout
        )
        
        # GLBファイルURLを取得
        textured_glb_file_url = None
        for f in output:
            if 'textured_mesh' in f.url:
                textured_glb_file_url = f.url
                break
        
        if not textured_glb_file_url:
            raise ValueError("No textured mesh found in API response")
        
        # URLからglbファイルを保存し、出力先ディレクトリとファイル名を取得する
        glb_dir, glb_filename = fetch_glb_from_url(textured_glb_file_url)
        
        # glbファイルからテクスチャをpngで保存
        texture_paths = extract_texture_from_glb(glb_dir=glb_dir, glb_filename=glb_filename)
        
        # テクスチャをBase64エンコード
        textures = encode_textures_to_base64(texture_paths)
        
        # 成功時のレスポンス
        return {
            "glb_url": textured_glb_file_url,
            "textures": textures
        }
        
    except Exception as e:
        # エラー時のレスポンス（RunPod推奨形式）
        return {
            "error": str(e)
        }
    
    finally:
        # 一時ファイルのクリーンアップ
        if glb_dir:
            try:
                clean(folder_list=[glb_dir])
            except:
                # クリーンアップの失敗は無視
                pass
```

### ステップ3: デバッグ用ログの削除
**ファイル**: `rp_handler.py`
**作業内容**:
1. print文の削除（10行目、12行目）
2. 不要なreturn文の削除（68行目の未定義変数）

**削除対象**:
```python
# 以下の行を削除
print(os.getenv('SYNEXA_API_KEY'))  # 10行目
print(api_key)  # 12行目
return glb, texture  # 68行目（未定義変数）
```

### ステップ4: dotenv読み込みの条件付き実装
**ファイル**: `rp_handler.py`
**作業内容**:
1. ローカル環境でのみdotenvを読み込むように修正
2. RunPod環境では環境変数から直接取得

**実装詳細**:
```python
import os

# ローカル開発環境でのみdotenvを使用
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()
```

## 実装順序

1. **utils/glb_utils.py**への関数追加（ステップ1）
2. **rp_handler.py**のクリーンアップ（ステップ3, 4）
3. **rp_handler.py**のメイン処理更新（ステップ2）

## テストの実施

### 単体テスト
1. `encode_textures_to_base64()`関数のテスト
   - サンプルPNGファイルでのエンコード確認
   - 複数ファイルの処理確認

### 統合テスト
1. サンプル画像での実行確認
   - test_input.jsonを使用
   - 返却値の形式確認

### エラーケーステスト
1. APIキー未設定時
2. 不正な入力画像パス
3. API呼び出し失敗時
4. テクスチャ抽出失敗時

## 確認事項

### 実装前の確認
- [ ] 現在のブランチが`feature/complete-glb-handler`であること
- [ ] 必要なライブラリ（pygltflib）がインストール済みであること

### 実装後の確認
- [ ] 不要なprint文が削除されていること
- [ ] エラーハンドリングが適切に実装されていること
- [ ] 一時ファイルのクリーンアップが動作すること
- [ ] 返却値の形式が要件通りであること

## リスクと対策

### リスク1: メモリ不足
**対策**: 大きなテクスチャファイルの場合、チャンク単位での読み込みを検討

### リスク2: 一時ファイルの残留
**対策**: finallyブロックでの確実なクリーンアップ実装

### リスク3: API応答の変更
**対策**: 柔軟なレスポンス解析とエラーメッセージの充実

## 完了基準

1. rp_handler.pyが正常に動作すること
2. GLBファイルのURLが返却されること
3. テクスチャがBase64エンコードされて返却されること
4. エラー時に適切なエラーメッセージが返却されること
5. 一時ファイルが適切にクリーンアップされること