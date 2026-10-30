"""Descarga explícita de motores/modelos oficiales para preparar el paquete offline."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile
import os
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
from huggingface_hub import hf_hub_download, snapshot_download, HfApi

ROOT=Path(__file__).resolve().parent


def download_model(url,target,size,digest):
    if target.exists() and target.stat().st_size==size:
        with target.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()==digest:return
    temporary=target.with_suffix(target.suffix+'.partial')
    print(f'Descarga HTTPS: {target.name} ({size//1_000_000} MB)',flush=True)
    with urllib.request.urlopen(url,timeout=120) as source,temporary.open('wb') as output:
        total=0;last=0
        while chunk:=source.read(1024*1024):
            output.write(chunk);total+=len(chunk)
            if total-last>=100_000_000:
                print(f'  {total//1_000_000} / {size//1_000_000} MB',flush=True);last=total
    with temporary.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if temporary.stat().st_size!=size or actual!=digest:raise ValueError('El modelo no se descargó íntegro.')
    temporary.replace(target)


def prepare():
    cache=ROOT/'.model_cache';cache.mkdir(exist_ok=True)
    models=ROOT/'models';models.mkdir(exist_ok=True)
    runtime=ROOT/'runtime'/'llama';runtime.mkdir(parents=True,exist_ok=True)
    url='https://github.com/ggml-org/llama.cpp/releases/download/b11838/llama-b11838-bin-win-cpu-x64.zip'
    digest='45462c0f6b0e9f9b841e3d2bc2a086b29925a9691d866458bbbf90cf564ae2b7'
    archive=cache/'llama-b11838-bin-win-cpu-x64.zip'
    if not archive.exists():
        print('Descargando motor CPU portátil...',flush=True)
        with urllib.request.urlopen(url,timeout=120) as source,archive.open('wb') as dest:shutil.copyfileobj(source,dest)
    with archive.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=digest:raise ValueError('La huella del motor no coincide con la publicación oficial.')
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            target=(runtime/info.filename).resolve()
            if not target.is_relative_to(runtime.resolve()):raise ValueError('Ruta inválida en el paquete del motor.')
        package.extractall(runtime)
    if not (runtime/'llama-server.exe').exists():raise ValueError('No se encontró llama-server.exe en el paquete.')
    print('Descargando Qwen3 4B Q4_K_M (aprox. 2,5 GB)...',flush=True)
    api=HfApi()
    model_info=api.model_info('Qwen/Qwen3-4B-GGUF',files_metadata=True)
    files=api.list_repo_files('Qwen/Qwen3-4B-GGUF',revision=model_info.sha)
    model_name=next(f for f in files if f.lower().endswith('q4_k_m.gguf'))
    entry=next(s for s in model_info.siblings if s.rfilename==model_name)
    download_model(f'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/{model_info.sha}/{model_name}?download=true',
        models/'Qwen3-4B-Q4_K_M.gguf',entry.lfs.size,entry.lfs.sha256)
    print('Descargando modelo de transcripción multilingüe...',flush=True)
    speech_info=api.model_info('Systran/faster-whisper-tiny')
    snapshot_download('Systran/faster-whisper-tiny',revision=speech_info.sha,
        local_dir=models/'whisper-tiny',allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.*','preprocessor_config.json'])
    notices=ROOT/'licenses';notices.mkdir(exist_ok=True)
    for name,url in {
        'Qwen3-LICENSE.txt':'https://huggingface.co/Qwen/Qwen3-4B/resolve/main/LICENSE',
        'llama.cpp-LICENSE.txt':'https://raw.githubusercontent.com/ggml-org/llama.cpp/b11838/LICENSE',
        'faster-whisper-LICENSE.txt':'https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/LICENSE',
        'Whisper-LICENSE.txt':'https://raw.githubusercontent.com/openai/whisper/main/LICENSE',
    }.items():
        with urllib.request.urlopen(url,timeout=60) as response:(notices/name).write_bytes(response.read())
    manifest={'llama.cpp':'b11838','llama_sha256':digest,'qwen_repo':'Qwen/Qwen3-4B-GGUF','qwen_revision':model_info.sha,
              'qwen_file':model_name,'whisper_repo':'Systran/faster-whisper-tiny','whisper_revision':speech_info.sha}
    (ROOT/'modelos_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Modelos y motor preparados. La inferencia ya no necesita Internet.',flush=True)


if __name__=='__main__':prepare()
