import os
import glob
from tqdm import tqdm
from multiprocessing import Pool
from argparse import ArgumentParser

import hashlib
import json

def get_sample_id(description: str):
    """
    Generates a unique ID for a sample based on its description string.
    """
    hash_object = hashlib.sha256(description.encode())
    # The hexdigest() method returns a string representation of the hash.
    return hash_object.hexdigest()


def parse_args():
    parser = ArgumentParser(description='merge dataset')
    parser.add_argument(
        "--data_path",
        type=str,
        help="path to dir contains multiple raw dataset to merge",
    )
    parser.add_argument(
        "--multiprocess",
        action='store_true',
        help="multiprocessing",
    )
    parser.add_argument(
        "--gen_id",
        action='store_true',
        help="Given SHA-256 IDs for samples",
    )
    return parser.parse_args()


def merge_files(args):
    idx, data_path, save_path = args
    file_list = glob.glob(os.path.join(data_path, '*.jsonl'))
    output_filename = os.path.join(save_path, 'merged.jsonl')
    with open(output_filename, 'w') as outfile:
        for filename in tqdm(file_list, position=idx, desc=f'Merging files in {data_path}'):
            with open(filename, 'r') as infile:
                dataset = list(infile)
                for line in dataset:
                    data = json.loads(line)
                    
                    code = data['code']
                    idx = get_sample_id(code)
                    data['id'] = idx
                    
                    json.dump(data, outfile)
                    outfile.write('\n')
                    
                #     outfile.write(line)
                # data = infile.read()
                # outfile.write(data + '\n')


if __name__ == '__main__':
    opt = parse_args()
    data_path = opt.data_path
    subdirs = [os.path.join(data_path, d) for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))]
    
    if opt.multiprocess:
        with Pool(processes=len(subdirs)) as pool:
            args = [(idx, subdir) for idx, subdir in enumerate(subdirs)]
            pool.map(merge_files, args)
    else:
        for subdir in subdirs:
            merge_files(subdir)
