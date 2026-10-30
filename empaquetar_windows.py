"""Construye la carpeta distribuible; nunca incluye la base o audios del usuario."""
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent


def archive():
    dest=ROOT/'dist'/'DzoneDemo'
    required=[dest/'DzoneDemo.exe',dest/'runtime'/'llama'/'llama-server.exe',
              dest/'models'/'Qwen3-4B-Q4_K_M.gguf',dest/'models'/'whisper-tiny'/'model.bin',dest/'LEEME_DISTRIBUCION.md']
    if not all(path.is_file() for path in required):raise ValueError('El paquete distribuible está incompleto.')
    output=ROOT/'dist'/'DzoneDemo_Windows_IA_local.zip'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as package:
        for path in sorted(dest.rglob('*')):
            if path.is_file():package.write(path,path.relative_to(dest.parent))
    with zipfile.ZipFile(output) as package:
        if package.testzip() is not None:raise ValueError('Falló la comprobación del ZIP.')
    print(f'ZIP verificado: {output} ({output.stat().st_size/1_000_000_000:.2f} GB)',flush=True)
    return output


def build():
    packages=['reportlab','faster_whisper','ctranslate2','sounddevice','_sounddevice_data','tokenizers','onnxruntime']
    command=[sys.executable,'-m','PyInstaller','--clean','--noconfirm','--onedir','--windowed','--name','DzoneDemo']
    for package in packages:command+=['--collect-all',package]
    subprocess.run(command+['dzone.py'],cwd=ROOT,check=True)
    dest=ROOT/'dist'/'DzoneDemo'
    for folder in ('runtime','models','licenses','samples'):
        source=ROOT/folder
        if not source.exists():raise FileNotFoundError(f'Falta {folder}. Ejecuta preparar_ia.py primero.')
        shutil.copytree(source,dest/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.cache','whisper-base'))
    for filename in ('LEEME_DISTRIBUCION.md','modelos_manifest.json'):
        shutil.copy2(ROOT/filename,dest/filename)
    notices=dest/'licenses'/'dependencias';notices.mkdir(parents=True,exist_ok=True)
    for distribution in importlib.metadata.distributions():
        name=distribution.metadata['Name']
        for filename in distribution.files or ():
            if '.dist-info/' in str(filename).replace('\\','/') and ('license' in str(filename).lower() or 'notice' in str(filename).lower()):
                source=Path(distribution.locate_file(filename))
                if source.is_file():
                    target=notices/name/Path(*Path(filename).parts[1:]);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    print(f'Paquete listo: {dest}. Enviar la carpeta COMPLETA, no solo el EXE.',flush=True)


if __name__=='__main__':build()
