import os
import argparse
from datasets import load_dataset

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--languages', default=['Python'], nargs='+')
    parser.add_argument('--cache_dir', type=str, default='./cache')

    return parser.parse_args()


if __name__ == '__main__':
    opt = args()
    data_path, languages = opt.cache_dir, opt.languages
    
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    ds = load_dataset("codeparrot/github-code", languages=languages, cache_dir=data_path)
    print('Download done!')
    print(ds['train'].features)

