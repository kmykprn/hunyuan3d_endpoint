import argparse


def create_parser():
    """コマンドライン引数パーサーを作成する"""
    parser = argparse.ArgumentParser(
        description="TripoSR: Fast 3D Object Reconstruction from a Single Image"
    )

    # 必須引数
    parser.add_argument("image", type=str, nargs="+", help="Path to input image(s).")

    # デバイス設定
    parser.add_argument(
        "--device",
        default="cuda:0",
        type=str,
        help="Device to use. If no CUDA-compatible device is found, will fallback to 'cpu'. Default: 'cuda:0'",
    )

    # モデル設定
    parser.add_argument(
        "--pretrained-model-name-or-path",
        default="stabilityai/TripoSR",
        type=str,
        help="Path to the pretrained model. Could be either a huggingface model id is or a local path. Default: 'stabilityai/TripoSR'",
    )

    parser.add_argument(
        "--chunk-size",
        default=8192,
        type=int,
        help="Evaluation chunk size for surface extraction and rendering. Smaller chunk size reduces VRAM usage but increases computation time. 0 for no chunking. Default: 8192",
    )

    parser.add_argument(
        "--mc-resolution",
        default=256,
        type=int,
        help="Marching cubes grid resolution. Default: 256",
    )

    # 画像前処理設定
    parser.add_argument(
        "--no-remove-bg",
        action="store_true",
        help="If specified, the background will NOT be automatically removed from the input image, and the input image should be an RGB image with gray background and properly-sized foreground. Default: false",
    )

    parser.add_argument(
        "--foreground-ratio",
        default=0.85,
        type=float,
        help="Ratio of the foreground size to the image size. Only used when --no-remove-bg is not specified. Default: 0.85",
    )

    # 出力設定
    parser.add_argument(
        "--output-dir",
        default="output/",
        type=str,
        help="Output directory to save the results. Default: 'output/'",
    )

    parser.add_argument(
        "--model-save-format",
        default="obj",
        type=str,
        choices=["obj", "glb"],
        help="Format to save the extracted mesh. Default: 'obj'",
    )

    # テクスチャ設定
    parser.add_argument(
        "--bake-texture",
        action="store_true",
        help="Bake a texture atlas for the extracted mesh, instead of vertex colors",
    )

    parser.add_argument(
        "--texture-resolution",
        default=2048,
        type=int,
        help="Texture atlas resolution, only useful with --bake-texture. Default: 2048",
    )

    # レンダリング設定
    parser.add_argument(
        "--render",
        action="store_true",
        help="If specified, save a NeRF-rendered video. Default: false",
    )

    return parser


def parse_args():
    """コマンドライン引数をパースして返す"""
    parser = create_parser()
    return parser.parse_args()
