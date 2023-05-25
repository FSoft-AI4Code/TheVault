import json
import argparse
from itertools import tee
from tqdm import tqdm
from typing import List, Iterable, Dict
from datasketch import MinHash, MinHashLSH
import multiprocessing as mp

def ngrams(sequence: List[str], n: int, min_ngram_size: int = 5) -> Iterable:
    """
    Code taken from NLTK, without padding.

    Parameters
    ----------
    sequence : list
        The sequence of items to be converted into n-grams.
    n : int
        The order of the n-grams to be extracted.
    min_ngram_size : int
        The minimum number of items in the sequence to generate n-grams.

    Returns
    -------
    Iterable
        The n-grams generated from the sequence.

    Examples
    --------
    >>> list(ngrams(['a', 'b', 'c', 'd'], 2))
    [('a', 'b'), ('b', 'c'), ('c', 'd')]
    >>> list(ngrams(['a', 'b', 'c', 'd'], 3))
    [('a', 'b', 'c'), ('b', 'c', 'd')]
    """
    if len(sequence) < min_ngram_size:
        return []
    
    iterables = tee(sequence, n)
    for i, sub_iterable in enumerate(iterables):
        for _ in range(i):
            next(sub_iterable, None)
    return zip(*iterables)


def calculate_minhash(idx, tokens, num_perm=128):
    set_token = set(tokens)
    minhash = MinHash(num_perm=num_perm)
    for t in set_token:
        minhash.update(t.encode("utf8"))
    
    return (idx, minhash)


def calculate_minhash_iter(dataset, ngram):
    args = []
    for item in dataset:
        try:
            item = json.loads(item)
        except Exception:
            continue
        
        if 'id' in item:
            idx_name = "id"
        elif 'task_id' in item:
            idx_name = "task_id"
        elif 'problem_id' in item:
            idx_name = "problem_id"
            
        idx = item[idx_name]
        content = item['code_tokens']
        args.append((idx, [" ".join(t) for t in ngrams(content, ngram)]))

    hash_result = []
    with mp.Pool() as p:
        # with tqdm(total=len(args)) as pbar:
        hash_result = p.starmap(calculate_minhash, tqdm(args, total=len(args)))
                # hash_result.append(res)
                # pbar.update()
            # hash_result = p.starmap(calculate_minhash, args)
    
    return hash_result


def insert_minhash_lsh(hash_dict: Dict, threshold: float = 0.7, num_perm: int = 128):
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)

    for idx, val in hash_dict.items():
        lsh.insert(idx, val)
    
    return lsh


def deduplicate(
    set1: List, 
    set2: List, 
    threshold: float, 
    num_perm: int = 128, 
    ngram: int = 3,
    save_name: str = "deduplicate_info.jsonl"):
    """
    Compare duplicate sample in set1 and set2.
    We consider set1 as source set and compare each sample in set1 (which should
    large than the other) and set2 as target set.
    The output is list of duplicated sample of set1 correspond with
    the duplicated sample of set2.
    
    Parameters
    ----------
    set1 : list
        The sequence of items to be converted into n-grams.
    set2 : int
        The order of the n-grams to be extracted.
    num_perm : int
        The number of permutation for minhash function
    ngram: int
        The order of the n-grams to be extracted (for `ngrams` function)
    """
        
    print("Calculate MinHash for Source set")
    set1_hash = calculate_minhash_iter(set1, ngram)
    
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for idx, val in set1_hash:
        lsh.insert(idx, val)
    
    set2_hash = calculate_minhash_iter(set2, ngram)
    duplicate_info = []
    for idx, val in set2_hash:
        res = lsh.query(val)
        if res:
            duplicate_info.append({'tgt': idx, 'src': res})
            # duplicate_info[idx] = res
    
    if len(res) < 1:
        print("Not find any duplicated sample")
    else:
        # TODO: save duplicate_info as 
        with open(f"./{save_name}", 'w') as writer:
            for item in duplicate_info:
                json.dump(item, writer)
                writer.write('\n')


def args_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--set1', '-s1', help='Source set')
    parser.add_argument('--set2', '-s2', help='Target set')
    parser.add_argument('--num_perm', type=int, default=128, help='Number of permutation')
    parser.add_argument('--threshold', type=float, default=0.8, help='Threshold')
    parser.add_argument('--n_gram', type=int, default=3, help='Number of Ngrams')
    parser.add_argument('--save_name', type=str, default="deduplicate_info.jsonl")
    opt = parser.parse_args()
    return opt


if __name__ == '__main__':
    opt = args_parse()
    mp.set_start_method("fork")
    
    print("Deduplication for", opt.set1)
    with open(opt.set1, 'r') as file1:
        src = list(file1)
    with open(opt.set2, 'r') as file2:
        tgt = list(file2)
        
    deduplicate(src, tgt, opt.threshold, opt.num_perm, opt.n_gram, opt.save_name)
