"""Archive explicitly selected run directories without model/binary/credential files.

Usage: archive_evidence.py DEST LABEL=SOURCE [LABEL=SOURCE ...]
All sources must be inside the caller's reproduction results directory.
"""
import hashlib
import shutil
import sys
from pathlib import Path

def main():
    dest=Path(sys.argv[1]).resolve()
    if dest.exists():raise RuntimeError('Evidence destination exists; use a new name')
    allowed={'.json','.jsonl','.csv','.md','.txt','.log','.patch','.sha256','.png'}
    selected=[];labels=set()
    for item in sys.argv[2:]:
        label,source=item.split('=',1)
        if not label or Path(label).name!=label or label in ('.','..'):raise ValueError('Invalid evidence label')
        if label in labels:raise ValueError('Duplicate evidence label')
        labels.add(label)
        root=Path(source).resolve(strict=True)
        if 'results' not in root.parts:raise ValueError('Source must be an experiment result directory')
        for path in sorted(root.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.suffix in allowed:
                selected.append((path,dest/label/path.relative_to(root)))
    if not selected:raise RuntimeError('No evidence selected')
    dest.mkdir(parents=True)
    for source,target in selected:
        target.parent.mkdir(parents=True,exist_ok=True)
        if source.suffix=='.png':shutil.copyfile(source,target)
        else:
            # Preserve log content; normalize text line endings for stable Git hashes.
            raw=source.read_bytes()
            text=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8-sig')
            target.write_text(text.replace('\r\n','\n'),encoding='utf-8',newline='\n')
    lines=[]
    for _,path in selected:
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(dest).as_posix())
    (dest/'evidence.sha256').write_text('\n'.join(lines)+'\n')
    print(f'Archived {len(lines)} evidence files to {dest}')

if __name__=='__main__':main()
