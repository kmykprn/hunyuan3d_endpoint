import logging
import time
from typing import Optional

import torch


class Timer:
    """GPU同期を考慮した処理時間計測クラス"""

    def __init__(self, time_scale: float = 1000.0, time_unit: str = "ms"):
        """
        Args:
            time_scale: 時間のスケール（1000.0でミリ秒、1.0で秒）
            time_unit: 時間の単位表示
        """
        self.items = {}
        self.time_scale = time_scale
        self.time_unit = time_unit

    def start(self, name: str) -> None:
        """計測を開始する

        Args:
            name: 計測対象の名前
        """
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        self.items[name] = time.time()
        logging.info(f"{name} ...")

    def end(self, name: str) -> Optional[float]:
        """計測を終了して経過時間を返す

        Args:
            name: 計測対象の名前

        Returns:
            経過時間（time_scaleでスケーリング済み）、計測開始していない場合はNone
        """
        if name not in self.items:
            return None
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start_time = self.items.pop(name)
        delta = time.time() - start_time
        t = delta * self.time_scale
        logging.info(f"{name} finished in {t:.2f}{self.time_unit}.")
        return t

    def reset(self) -> None:
        """全ての計測をリセットする"""
        self.items.clear()
