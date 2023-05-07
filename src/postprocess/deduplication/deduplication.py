import os
import re
from argparse import ArgumentParser
import json
from tqdm import tqdm
from typing import List, Optional, Set

from .minhash_deduplication import DuplicationIndex
from datasketch import MinHash, MinHashLSH

NON_ALPHA = re.compile("[^A-Za-z_0-9]")
# parameters used in DuplicationIndex
MIN_NUM_TOKENS = 10
NUM_PERM = 256

# column name of file paths, we add as file identifiers
PATH_COLUMN = "original_path"
# name of the "text" column used in deduplication
CONTENT = "content"

def get_min_hash(tokens: List[str]) -> Optional[MinHash]:
    """Compute the MinHash of a code snippet."""
    if len(tokens) < MIN_NUM_TOKENS:
        return None
    min_hash = MinHash(num_perm=NUM_PERM)
    for token in set(tokens):
        min_hash.update(token.encode())
    return min_hash


def _compute_min_hash(element):
    index, data = element
    min_hash = get_min_hash(data)
    if min_hash is not None:
        return (index, data), min_hash


def parse_args():
    parser = ArgumentParser(description='merge dataset')
    parser.add_argument(
        "--path1",
        "-P1",
        type=str,
        help="path to dataset #1",
    )
    parser.add_argument(
        "--path2",
        "-P2",
        type=str,
        help="path to dataset #2",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.85,
        help="Jaccard Threshold",
    )
    # parser.add_argument(
    #     "--multiprocess",
    #     action='store_true',
    #     help="multiprocessing",
    # )
    return parser.parse_args()


if __name__ == '__main__':
    opt = parse_args()
    
    di = DuplicationIndex(duplication_jaccard_threshold=opt.threshold)
    idx_mapping = {}
    with open(opt.path1, 'r') as file:
        data = list(file)
        
        for idx, item in enumerate(data):
            item = json.loads(item)
        
            # idx = item['id']
            code = item['code_tokens']
            idx_mapping[idx] = item['id']
            element, _hash = _compute_min_hash((idx, code))
            di.add(idx, _hash)

    # Returns a List[Cluster] where Cluster is List[str] with the filenames.
    res = di.get_duplicate_clusters()
    with open('./deduplicate.jsonl', "w") as f:
        for item in res:
            for idx, val in enumerate(item["original_index"]):
                item["original_index"][idx] = idx_mapping[val]
            json.dump(item, f)
            f.write('\n')
    

    