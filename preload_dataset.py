import os
import sys
import multiprocessing as mp
import zipfile

path = sys.argv[1]
print("PATH: ", path)

fnames = [
    'train2017.zip',
    'val2017.zip',
    'annotations/instances_train2017.json',
    'annotations/instances_val2017.json',
]

LOAD_DICT = dict()

def register(ext):
    def wrapper(fn):
        global LOAD_DICT
        def F(fname):
            print("Ready to Load: ", fname)
            try:
                fn(fname)
                print(f"Load {fname} Okay")
            except Exception as e:
                print(f"Load {fname} fail: {e}")
        LOAD_DICT[ext] = F 
    return wrapper

@register('.zip')
def load_zip(fname):
    zipfile.ZipFile(fname)

@register('.json')
def load_txt(fname):
    open(fname).read()

def preload_data(fname):
    ext = os.path.splitext(fname)[-1]
    fn = LOAD_DICT.get(ext, None)
    if fn is not None:
        fn(fname)
    else:
        print("Skip: ", fname)

print("Ready to pre load datasets")

ps = []
for fname in fnames:
    fname = os.path.join(path, fname)
    p = mp.Process(target=preload_data, args=(fname, ))
    ps.append(p)

for p in ps:
    p.start()
for p in ps:
    p.join()

print("Pre read over")
