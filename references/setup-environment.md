# 转写环境搭建

## 1. Python 虚拟环境
```
python -m venv venv
venv\Scripts\python -m pip install --no-cache-dir "torch==2.6.0" "torchaudio==2.6.0" funasr modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
```
- 用 torch **2.6.x**：新版 torch 的 dist-info 里 license 路径超长，Windows 上 pip 会报
  "文件名或扩展名太长"（WinError 206）
- 加 `--no-cache-dir` 并把 `PIP_CACHE_DIR` 指到项目内，避免写入系统缓存被拦

## 2. GPU 版 PyTorch（可选，有 NVIDIA 卡时）
```
pip install --no-cache-dir <torch-2.6.0+cu124-cp312-cp312-win_amd64.whl> <torchaudio-...>.whl
```
- Windows 的 cu124 wheel 在阿里云镜像：`https://mirrors.aliyun.com/pytorch-wheels/cu124/`
  （该页是平铺列表，用 `--find-links` 或直接下载 wheel 文件后本地安装）
- 验证：`python -c "import torch; print(torch.cuda.is_available())"`

## 3. 语音模型（FunASR / SenseVoice）
需要三个模型（首次会下载，约 1.5GB，可离线）：
- `iic/SenseVoiceSmall`（识别）
- `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`（分段）
- `iic/punc_ct-transformer_cn-en-common-vocab471067-large`（标点）

预下载：
```
MODELSCOPE_HOME=项目/modelscope_home MODELSCOPE_CACHE=项目/models_cache python -c "from modelscope import snapshot_download; [snapshot_download(m) for m in [...] ]"
```
脚本会优先用本地快照（`models_cache/models/<id>/snapshots/...`）加载，避免每次联网。

## 4. 运行依赖
- 网络请求用 `requests`（装 funasr 时已带）
- FFmpeg 用录制器自带的 `ffmpeg.exe`，在 `config.json` 里填路径
