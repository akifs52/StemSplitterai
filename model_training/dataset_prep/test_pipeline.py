"""Quick test of the V3 splitter on existing guitar stems."""
import sys, os, shutil, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.guitar_splitter import split_guitar

sep = os.path.join(os.path.dirname(__file__), '..', '..', 'separated')
guitar_files = []
for root, dirs, files in os.walk(sep):
    for f in files:
        if f == 'guitar.wav':
            guitar_files.append(os.path.join(root, f))

print(f'Found {len(guitar_files)} guitar stems')

if guitar_files:
    src = guitar_files[0]
    print(f'Using: {src} ({os.path.getsize(src)/1e6:.1f}MB)')
    
    tmpdir = tempfile.mkdtemp()
    tmp_file = os.path.join(tmpdir, 'test_guitar.wav')
    shutil.copy2(src, tmp_file)
    
    result = split_guitar(tmp_file)
    print(f'Result entries: {len(result)}')
    for item in result:
        size_mb = os.path.getsize(item['path']) / 1e6
        print(f'  {item["name"]}: {size_mb:.1f}MB -> {item["path"]}')

print('Test completed successfully')
