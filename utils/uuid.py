import uuid


def generate_uuid(file_extension: str = "") -> str:
    """
    UUIDを使ったファイル名を生成

    Args:
        file_extention: ".png", ".txt"などのファイル拡張子

    Returns:
        uuid4の文字列.拡張子
    """
    # ファイル拡張子が.で始まっていない場合は追加
    if not file_extension.startswith("."):
        file_extension = f".{file_extension}"

    # uuidを生成
    id = uuid.uuid4()
    filename = f"{id}{file_extension}"
    return filename
