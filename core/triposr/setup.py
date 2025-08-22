from setuptools import setup, find_packages

setup(
    name="triposr",
    version="1.0.0",
    description="TripoSR: Fast 3D Object Generation from Images",
    url="https://github.com/VAST-AI-Research/TripoSR",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "omegaconf==2.3.0",
        "Pillow>=11.3.0",
        "einops==0.8.1",
        "torchmcubes @ git+https://github.com/tatsy/torchmcubes.git@3381600ddc3d2e4d74222f8495866be5fafbace4",
        "transformers>=4.55.0",
        "trimesh>=4.7.1",
        "rembg>=2.0.67",
        "huggingface-hub>=0.34.3",
        "imageio[ffmpeg]>=2.37.0",
        "xatlas==0.0.9",
        "moderngl>=5.10.0",
        "onnxruntime-gpu>=1.22.0",
        "torch>=2.0.0",
        "torchvision",
        "numpy",
    ],
    extras_require={
        "dev": [
            "gradio>=5.41.1",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
)