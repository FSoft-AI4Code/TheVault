import random
import hashlib
import json
from tqdm import tqdm

from argparse import ArgumentParser
import multiprocessing as mp


def jaccard_similarity(code1, code2, num_hash_functions=100) -> float:
    """Compute the Jaccard similarity of two code snippets."""
    num_same = sum(
        [1 for i in range(num_hash_functions) if code1[i] == code2[i]])
    num_total = num_hash_functions
    return float(num_same) / float(num_total)


def minhash_signature(tokens, num_hash_functions=100):
    # Create set of shingles
    shingles = set()
    for i in range(len(tokens)):
        if i < len(tokens) - 2:
            shingles.add((tokens[i], tokens[i+1], tokens[i+2]))
        elif i < len(tokens) - 1:
            shingles.add((tokens[i], tokens[i+1]))
        else:
            shingles.add(tokens[i])

    # Create hash functions
    hash_functions = []
    for i in range(num_hash_functions):
        hash_functions.append(hashlib.sha1(str(i).encode('utf-8')).hexdigest())

    # Generate minhash signature
    signature = [float('inf')] * num_hash_functions
    for shingle in shingles:
        shingle_str = str(shingle).encode('utf-8')
        shingle_hash = hashlib.sha1(shingle_str).hexdigest()
        for i, hf in enumerate(hash_functions):
            hash_val = int(shingle_hash, 16) ^ int(hf, 16)
            signature[i] = min(signature[i], hash_val)
    return signature


def _compute_min_hash(element):
    try:
        value = json.loads(element)
    except Exception:
        print(element)
    code = value['code_tokens']
    
    sample_id = None
    if 'id' in value:
        sample_id = value['id']
    
    min_hash = minhash_signature(code)
    if min_hash is not None:
        return sample_id, min_hash


def minhash_iter(dataset_iterator):
    with mp.Pool(processor=mp.cpu_count()-2) as pool:
        for data in pool.imap_unordered(
            _compute_min_hash,
            dataset_iterator
        ):
            if data is not None:
                yield data


def parse_args():
    parser = ArgumentParser(description='merge dataset')
    parser.add_argument(
        "--data_path",
        "-D",
        type=str,
        help="path to dataset #1",
    )
    parser.add_argument(
        "--target_path",
        "-T",
        type=str,
        help="path to dataset #2",
    )
    parser.add_argument(
        "--save_name",
        type=str,
        default="",
        help="path to save dir",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.85,
        help="Jaccard Threshold",
    )
    return parser.parse_args()


if __name__ == '__main__':
    opt = parse_args()
    
    # First load all data in target path into 
    target_hash = []
    print("Load target set", opt.target_path)
    with open(opt.target_path, 'r') as file:
        dataset = list(file)
        for _, min_hash in tqdm(minhash_iter(dataset), total=len(dataset)):
            target_hash.append(min_hash)
    print("Done load target set | Length:", len(dataset))
            
            
    # Cal minhash and compare
    print("Load dataset")
    chunk_size = 100000
    writer = open(f'./{opt.save_name}_deduplicate.jsonl', "w")
    with open(opt.data_path, 'r') as file:
        dataset = list(file)
        duplicate_list = []
        for index, min_hash in tqdm(minhash_iter(dataset), total=len(dataset)):
            for tgs in target_hash:
                score = jaccard_similarity(min_hash, tgs)
                if score > opt.threshold:
                    duplicate_list.append(index)

    for item in duplicate_list:
        json.dump({'id': item}, writer)
        writer.write('\n')
    