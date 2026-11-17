"""Download one pinned GGUF; the optional second argument selects a registry key."""
import hashlib, json, shutil, sys, time, urllib.request
from pathlib import Path
from model_registry import MODELS

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    key=sys.argv[2] if len(sys.argv)>2 else 'falcon3-1b-i2v4'
    spec=MODELS[key]
    REPO,REV,FILE,SHA,SIZE=(spec[k] for k in ('repo','revision','file','sha256','size_bytes'))
    root=Path(sys.argv[1]); dest=root/'models'/key; dest.mkdir(parents=True,exist_ok=True)
    final=dest/FILE
    if final.exists():
        if final.stat().st_size!=SIZE or digest(final)!=SHA:
            raise RuntimeError('Existing model failed integrity check; preserved, not overwritten')
        print('Reusing verified GGUF:',final,flush=True)
    else:
        if shutil.disk_usage(dest).free<SIZE+1024**3: raise RuntimeError('Insufficient disk space')
        url=f'https://huggingface.co/{REPO}/resolve/{REV}/{FILE}'
        part=dest/(FILE+'.part')
        for attempt in range(1,5):
            offset=part.stat().st_size if part.exists() else 0
            if offset==SIZE: break
            headers={'User-Agent':'VecLUT-Repro-P3'}
            if offset: headers['Range']=f'bytes={offset}-'
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60) as response:
                    append=offset>0 and response.status==206
                    if append and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                        raise RuntimeError('Unexpected partial response')
                    if not append: offset=0
                    mark=offset//(64*1024**2)
                    with part.open('ab' if append else 'wb') as f:
                        while True:
                            b=response.read(4*1024**2)
                            if not b: break
                            f.write(b); offset+=len(b)
                            if offset//(64*1024**2)>mark:
                                mark=offset//(64*1024**2); print(f'Downloaded {offset}/{SIZE} bytes',flush=True)
                if part.stat().st_size==SIZE: break
            except Exception as exc:
                print(f'Download attempt {attempt} failed: {type(exc).__name__}',flush=True)
                if attempt==4: raise
                time.sleep(2)
        if part.stat().st_size!=SIZE or digest(part)!=SHA: raise RuntimeError('Downloaded GGUF hash/size mismatch; partial file preserved')
        part.rename(final)
    manifest=dict(repo=REPO,revision=REV,file=FILE,sha256=SHA,size_bytes=SIZE,
                  source=f'https://huggingface.co/{REPO}/blob/{REV}/{FILE}',local_file=str(final),verified=True)
    (dest/'model-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest),flush=True)

if __name__=='__main__': main()
