from PIL import Image

from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen import Hunyuan3DPaintPipeline
from hy3dgen.shapegen.pipelines import export_to_trimesh
from hy3dgen.shapegen.utils import logger
from hy3dgen.shapegen import FaceReducer

from mmgp import offload
import torch
import os
import time
import random
from pathlib import Path
import shutil
import uuid

from runpod import RunPodLogger
from runpod.serverless.utils.rp_cleanup import clean
log = RunPodLogger()


def export_mesh(mesh, save_folder, textured=False, type='glb'):
    """
    メッシュを保存
    """
    if textured:
        path = os.path.join(save_folder, f'textured_mesh.{type}')
    else:
        path = os.path.join(save_folder, f'white_mesh.{type}')
    if type not in ['glb', 'obj']:
        mesh.export(path)
    else:
        mesh.export(path, include_normals=textured)
    return path


def randomize_seed_fn(seed: int, randomize_seed: bool) -> int:
    """
    ランダムなシード値を生成
    """
    MAX_SEED = 10000
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    return seed


def gen_save_folder(save_dir="output", max_size=200):
    """
    uuidの保存先ディレクトリを生成
    """
    
    # 保存先の親ディレクトリを生成（存在しない場合）
    SAVE_DIR = save_dir
    os.makedirs(save_dir, exist_ok=True)

    # 過去ディレクトリの数がmax_sizeよりも大きい場合、古いフォルダから削除
    dirs = [f for f in Path(SAVE_DIR).iterdir() if f.is_dir()]
    if len(dirs) >= max_size:
        oldest_dir = min(dirs, key=lambda x: x.stat().st_ctime)
        shutil.rmtree(oldest_dir)
        print(f"Removed the oldest folder: {oldest_dir}")

    # uuid形式の新規ディレクトリを生成
    new_folder = os.path.join(SAVE_DIR, str(uuid.uuid4()))
    os.makedirs(new_folder, exist_ok=True)
    print(f"Created new folder: {new_folder}")

    return new_folder


def _gen_shape(
    caption=None,
    image=None,
    mv_image_front=None,
    mv_image_back=None,
    mv_image_left=None,
    mv_image_right=None,
    steps=50,
    guidance_scale=7.5,
    seed=1234,
    octree_resolution=256,
    check_box_rembg=False,
    num_chunks=200000,
    randomize_seed: bool = False,
):
    # if not MV_MODE and image is None and caption is None:
    #     raise gr.Error("Please provide either a caption or an image.")
    # if MV_MODE:
    #     if mv_image_front is None and mv_image_back is None and mv_image_left is None and mv_image_right is None:
    #         raise gr.Error("Please provide at least one view image.")
    #     image = {}
    #     if mv_image_front:
    #         image['front'] = mv_image_front
    #     if mv_image_back:
    #         image['back'] = mv_image_back
    #     if mv_image_left:
    #         image['left'] = mv_image_left
    #     if mv_image_right:
    #         image['right'] = mv_image_right

    seed = int(randomize_seed_fn(seed, randomize_seed))

    octree_resolution = int(octree_resolution)
    if caption: print('prompt is', caption)
    save_folder = output_dir #gen_save_folder()
    stats = {
        'model': {
            'shapegen': 'tencent/Hunyuan3D-2mini/hunyuan3d-dit-v2-mini',
            'texgen': 'hunyuan3d-dit-v2-mini',
        },
        'params': {
            'caption': caption,
            'steps': steps,
            'guidance_scale': guidance_scale,
            'seed': seed,
            'octree_resolution': octree_resolution,
            'check_box_rembg': check_box_rembg,
            'num_chunks': num_chunks,
        }
    }
    time_meta = {}

    # if image is None:
    #     start_time = time.time()
    #     try:
    #         image = t2i_worker(caption)
    #     except Exception as e:
    #         raise gr.Error(f"Text to 3D is disable. Please enable it by `python gradio_app.py --enable_t23d`.")
    #     time_meta['text2image'] = time.time() - start_time

    # remove disk io to make responding faster, uncomment at your will.
    # image.save(os.path.join(save_folder, 'input.png'))
    # if MV_MODE:
    #     start_time = time.time()
    #     for k, v in image.items():
    #         if check_box_rembg or v.mode == "RGB":
    #             img = rmbg_worker(v.convert('RGB'))
    #             image[k] = img
    #     time_meta['remove background'] = time.time() - start_time
    # else:
    #     if check_box_rembg or image.mode == "RGB":
    #         start_time = time.time()
    #         image = rmbg_worker(image.convert('RGB'))
    #         time_meta['remove background'] = time.time() - start_time

    # remove disk io to make responding faster, uncomment at your will.
    # image.save(os.path.join(save_folder, 'rembg.png'))


    # 背景画像を削除
    start_time = time.time()
    image = rmbg_worker(image.convert('RGB'))
    time_meta['remove background'] = time.time() - start_time


    # image to white model
    start_time = time.time()

    generator = torch.Generator()
    generator = generator.manual_seed(int(seed))
    outputs = i23d_worker(
        image=image,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        generator=generator,
        octree_resolution=octree_resolution,
        num_chunks=num_chunks,
        output_type='mesh'
    )
    time_meta['shape generation'] = time.time() - start_time
    logger.info("---Shape generation takes %s seconds ---" % (time.time() - start_time))

    tmp_start = time.time()
    mesh = export_to_trimesh(outputs)[0]
    time_meta['export to trimesh'] = time.time() - tmp_start

    stats['number_of_faces'] = mesh.faces.shape[0]
    stats['number_of_vertices'] = mesh.vertices.shape[0]

    stats['time'] = time_meta
    main_image = image# if not MV_MODE else image['front']
    return mesh, main_image, save_folder, stats, seed


def generation_all(
    caption=None,
    image=None,
    mv_image_front=None,
    mv_image_back=None,
    mv_image_left=None,
    mv_image_right=None,
    steps=50,
    guidance_scale=7.5,
    seed=1234,
    octree_resolution=256,
    check_box_rembg=True,
    num_chunks=200000,
    randomize_seed: bool = False,
) -> tuple[str, str]:
    """
    テクスチャ付メッシュを生成
    """
    start_time_0 = time.time()
    
    # 形状を生成
    mesh, image, save_folder, stats, seed = _gen_shape(
        caption,
        image,
        mv_image_front=mv_image_front,
        mv_image_back=mv_image_back,
        mv_image_left=mv_image_left,
        mv_image_right=mv_image_right,
        steps=steps,
        guidance_scale=guidance_scale,
        seed=seed,
        octree_resolution=octree_resolution,
        check_box_rembg=check_box_rembg,
        num_chunks=num_chunks,
        randomize_seed=randomize_seed,
    )
    path = export_mesh(mesh, save_folder, textured=False)

    tmp_time = time.time()
    mesh = face_reduce_worker(mesh)
    logger.info("---Face Reduction takes %s seconds ---" % (time.time() - tmp_time))
    stats['time']['face reduction'] = time.time() - tmp_time

    tmp_time = time.time()
    textured_mesh = texgen_worker(mesh, image)
    logger.info("---Texture Generation takes %s seconds ---" % (time.time() - tmp_time))
    stats['time']['texture generation'] = time.time() - tmp_time
    stats['time']['total'] = time.time() - start_time_0

    textured_mesh.metadata['extras'] = stats
    path_textured = export_mesh(textured_mesh, save_folder, textured=True)

    torch.cuda.empty_cache()
    return path, path_textured


def replace_property_getter(instance, property_name, new_getter):
    # Get the original class and property
    original_class = type(instance)
    original_property = getattr(original_class, property_name)
    
    # Create a custom subclass for this instance
    custom_class = type(f'Custom{original_class.__name__}', (original_class,), {})
    
    # Create a new property with the new getter but same setter
    new_property = property(new_getter, original_property.fset)
    setattr(custom_class, property_name, new_property)
    
    # Change the instance's class
    instance.__class__ = custom_class
    
    return instance


def create_3d_model_hunyuan(input_data: dict):
    """
    画像からGLBファイルを生成する
    
    Returns:
        textured_mesh_path: テクスチャ付メッシュのパス
    """
    global face_reduce_worker, rmbg_worker, texgen_worker, i23d_worker
    
    torch.cuda.empty_cache()

    torch.set_default_device("cpu")

    # 形状生成ワーカを初期化
    modeltype = input_data.get("modeltype", "mini")
    if modeltype == "mini":
        i23d_worker = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            model_path='tencent/Hunyuan3D-2mini',
            subfolder='hunyuan3d-dit-v2-mini-fast',
            use_safetensors=True,
            device='cuda',
        )
    elif modeltype == "full":
        i23d_worker = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            model_path='tencent/Hunyuan3D-2',
            subfolder='hunyuan3d-dit-v2-0',
            use_safetensors=True,
            device='cuda',
        )

    i23d_worker.enable_flashvdm(mc_algo='dmc')
    i23d_worker.compile()

    # モデル以外のワーカーを初期化
    face_reduce_worker = FaceReducer()
    rmbg_worker = BackgroundRemover()
    
    # モデルをオフロード
    profile = input_data.get("vramsettings", 5)
    kwargs = {}
    replace_property_getter(i23d_worker, "_execution_device", lambda self : "cuda")
    pipe = offload.extract_models("i23d_worker", i23d_worker)

    # テクスチャ生成モデルを初期化
    texgen_worker = Hunyuan3DPaintPipeline.from_pretrained('tencent/Hunyuan3D-2')
    pipe.update(  offload.extract_models( "texgen_worker", texgen_worker))
    texgen_worker.models["multiview_model"].pipeline.vae.use_slicing = True

    if profile < 5:
        kwargs["pinnedMemory"] = "i23d_worker/model"
    if profile !=1 and profile !=3:
        kwargs["budgets"] = { "*" : 2200 }
    offload.default_verboseLevel = verboseLevel = 1
    offload.profile(pipe, profile_no = profile, verboseLevel = verboseLevel, **kwargs)

    # 画像を読み込み
    image_path = input_data.get("image_path")

    # 入力検証
    if not image_path:
        raise ValueError("image_path is required")

    # UUID形式の一時ディレクトリを作成
    global output_dir
    output_dir = os.path.join("tmp", str(uuid.uuid4()))
    os.makedirs(output_dir, exist_ok=True)

    # URLの場合は画像をダウンロード
    if image_path.startswith(("http://", "https://")):
        import requests

        # 画像をダウンロード
        response = requests.get(image_path)
        response.raise_for_status()

        # 一時ディレクトリ内に保存
        downloaded_image_path = os.path.join(output_dir, "input_image.png")
        with open(downloaded_image_path, "wb") as f:
            f.write(response.content)
        image_path = downloaded_image_path
        log.info(f"画像をダウンロードしました: {image_path}")

    try:
        image = Image.open(image_path).convert("RGBA")
        mesh_path, textured_mesh_path = generation_all(image=image)
        log.info(mesh_path, textured_mesh_path)
        torch.cuda.empty_cache()
        
        return textured_mesh_path
    except Exception as e:
        if os.path.exists(output_dir):
            clean(folder_list=[output_dir])
        raise e