import uuid


def generate_uuid(file_extension: str = "") -> str:
    """
    UUIDを使ったファイル名を生成

    Args:
        file_extention: ".png", ".txt"などのファイル拡張子

    Returns:
        uuid4の文字列.拡張子
    """
    id = uuid.uuid4()
    filename = f"{id}{file_extension}"
    return filename
