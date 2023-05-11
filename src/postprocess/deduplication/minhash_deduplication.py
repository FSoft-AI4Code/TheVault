from argparse import ArgumentParser
import json
import multiprocessing as mp
import re
from collections import defaultdict
from functools import partial
from typing import Dict, List, Optional, Set, Tuple, Type

from datasets import Dataset
from tqdm import tqdm

from datasketch import MinHash, MinHashLSH
# from dpu_utils.utils.iterators import ThreadedIterator


NON_ALPHA = re.compile("[^A-Za-z_0-9]")
# parameters used in DuplicationIndex
MIN_NUM_TOKENS = 10
NUM_PERM = 256

def get_min_hash(tokens: List[str]) -> Optional[MinHash]:
    """Compute the MinHash of a code snippet."""
    if len(tokens) < MIN_NUM_TOKENS:
        return None
    min_hash = MinHash(num_perm=NUM_PERM)
    for token in set(tokens):
        min_hash.update(token.encode())
    return min_hash


def get_tokens(code: str) -> Set[str]:
    """Tokenize a code snippet."""
    return set([t for t in NON_ALPHA.split(code) if len(t.strip()) > 0])


class DuplicationIndex:
    def __init__(
        self,
        *,
        duplication_jaccard_threshold: float = 0.85,
    ):
        self._duplication_jaccard_threshold = duplication_jaccard_threshold
        self._num_perm = NUM_PERM
        self._index = MinHashLSH(threshold=self._duplication_jaccard_threshold, num_perm=self._num_perm)

        self._duplicate_clusters = defaultdict(set)

    def add(self, code_key: Tuple, min_hash: MinHash) -> None:
        """Add a key to _index (MinHashLSH)
        the min_hash is used to query closest matches based on the jaccard_threshold.
        The new key is either added to a existing cluster of one close match,
        or a new cluster is created. The clusters created in this way, depend on the order of add.

        Args:
            code_key (Tuple of (index, repo_name, path)):
                Theoritically any hasbale key. Here we use a tuple to retrieve the information later.
            min_hash: MinHash of the code_key.
        """
        close_duplicates = self._index.query(min_hash)
        # print(self._index.keys)
        # print(code_key)
        if code_key in self._index.keys:
            return

        self._index.insert(code_key, min_hash)
        if len(close_duplicates) > 0:

            for base_duplicate in close_duplicates:
                if base_duplicate in self._duplicate_clusters:
                    self._duplicate_clusters[base_duplicate].add(code_key)
                    break
            else:
                self._duplicate_clusters[close_duplicates[0]].add(code_key)

    def get_duplicate_clusters(self) -> List[List[Dict]]:
        """Export the duplicate clusters.
        For each cluster, the first element is the base element of the cluster.
        The base element has an estimation jaccard similarity higher than the threshold with all the other elements.

        Returns:
            duplicate_clusters (List[List[Dict]]):
                List of duplicate clusters.
        """
        duplicate_clusters = []
        for base, duplicates in self._duplicate_clusters.items():
            cluster = [base] + list(duplicates)
            # reformat the cluster to be a list of dict
            cluster = {"cluster_index": cluster[0], "original_index": cluster[1:]}
            duplicate_clusters.append(cluster)
        return duplicate_clusters

    def save(self, filepath) -> None:
        duplicate_clusters = self.get_duplicate_clusters()
        with open(filepath, "w") as f:
            json.dump(duplicate_clusters, f)


# def _compute_min_hash(element):
#     index, data = element
#     min_hash = get_min_hash(data)
#     if min_hash is not None:
#         return (index, data), min_hash


# def minhash_iter(dataset_iterator: Type[Dataset]):
#     with mp.Pool() as pool:
#         for data in pool.imap_unordered(
#             _compute_min_hash,
#             ThreadedIterator(dataset_iterator, max_queue_size=10000),
#             chunksize=100,
#         ):
#             if data is not None:
#                 yield data


def make_duplicate_clusters(dataset_iterator: Type[Dataset], jaccard_threshold: float):
    """Find duplicate clusters in the dataset in two steps:
    1. Compute MinHash for each code snippet. MinHash is a tool for fast jaccard similarity estimation.
    This step is computed using an asynchronous multiprocessing pool, minhash_iter
    2. Find duplicate clusters. The computed MinHash is added sequentially to the DuplicationIndex.
    This step cannot be parallelized. So using asynchronous thread in the previous step helps to speed up the process.
    """
    di = DuplicationIndex(duplication_jaccard_threshold=jaccard_threshold)

    for filename, min_hash in tqdm(ThreadedIterator(minhash_iter(enumerate(dataset_iterator)), max_queue_size=100)):
        di.add(filename, min_hash)

    # Returns a List[Cluster] where Cluster is List[str] with the filenames.
    return di.get_duplicate_clusters()


def jaccard_similarity(code1: str, code2: str) -> float:
    """Compute the Jaccard similarity of two code snippets."""
    tokens1 = get_tokens(code1)
    tokens2 = get_tokens(code2)
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


def deduplicate_dataset(
    dataset: Type[Dataset], jaccard_threshold: float = 0.85
) -> Tuple[Type[Dataset], List[List[Dict]]]:
    """Deduplicate the dataset using minhash and jaccard similarity.
    This function first generate duplicate clusters, then each cluster
    is reduced to the extremes that are similar to the other elements in the cluster.
    Codes are called similar if their Jaccard similarity is greater than jaccard_threshold (0.85 default).

    Args:
        dataset (Type[Dataset]):
            The dataset to deduplicate.
        jaccard_threshold (float, default=0.85):
            jaccard threshold to determine if two codes are similar

    Returns:
        ds_dedup (Type[Dataset]):
            The deduplicated dataset.
        duplicate_clusters (List[List[Dict]]):
            The list of duplicate clusters.
            Each cluster is a list of dicts with the following keys:
            - base_index : int
                The index of the code in the original dataset.
            - repo_name : str
            - path : str
            - copies : int
                The number of copies of the code in the cluster. (find_cluster_extremes)
            - is_extreme : bool
                Whether the code is an extreme in the cluster.
            All the codes in the cluster are removed from the dataset except the extremes.

    Example:
        >>> from datasets import load_dataset
        >>> from minhash_deduplication import deduplicate_dataset
        >>> ds = load_dataset("lvwerra/codeparrot-clean", split="train")
        >>> ds_dedup, duplicate_clusters = deduplicate_dataset(ds, jaccard_threshold=0.85)
    """
    duplicate_clusters = make_duplicate_clusters(dataset, jaccard_threshold)
    duplicate_indices = set(x["base_index"] for cluster in duplicate_clusters for x in cluster)
    extreme_dict = {}
    extremes_clusters = find_extremes(duplicate_clusters, dataset, jaccard_threshold)
    for extremes in extremes_clusters:
        for element in extremes:
            extreme_dict[element["base_index"]] = element
    remove_indices = duplicate_indices - set(extreme_dict.keys())
    ds_filter = dataset.filter(lambda x, idx: idx not in remove_indices, with_indices=True)

    # update duplicate_clusters
    for cluster in duplicate_clusters:
        for element in cluster:
            element["is_extreme"] = element["base_index"] in extreme_dict
            if element["is_extreme"]:
                element["copies"] = extreme_dict[element["base_index"]]["copies"]

    print(f"Original dataset size: {len(dataset)}")
    print(f"Number of duplicate clusters: {len(duplicate_clusters)}")
    print(f"Files in duplicate cluster: {len(duplicate_indices)}")
    print(f"Unique files in duplicate cluster: {len(extreme_dict)}")
    print(f"Filtered dataset size: {len(ds_filter)}")

    return ds_filter, duplicate_clusters


def _compute_min_hash(element):
    index, value = element
    value = json.loads(value)
    code = value['code_tokens']
    
    sample_id = None
    if 'id' in value:
        sample_id = value['id']
    
    min_hash = get_min_hash(code)
    if min_hash is not None:
        return (index, sample_id, code), min_hash


def minhash_iter(dataset_iterator):
    with mp.Pool() as pool:
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
        "--threshold",
        "-t",
        type=float,
        default=0.85,
        help="Jaccard Threshold",
    )
    return parser.parse_args()


if __name__ == '__main__':
    opt = parse_args()
    
    idx_mapping = {}
    di = DuplicationIndex(duplication_jaccard_threshold=opt.threshold)
    
    # First load all data in target path into 
    with open(opt.target_path, 'r') as file:
        dataset = list(file)
        for meta, min_hash in tqdm(minhash_iter(enumerate(dataset)), total=len(dataset)):
            idx, _, code =  meta
            di.add(idx, min_hash)
            
    with open(opt.data_path, 'r') as file:
        dataset = list(file)
        for meta, min_hash in tqdm(minhash_iter(enumerate(dataset)), total=len(dataset)):
            idx, sample_index, code =  meta
            di.add(idx, min_hash)
            idx_mapping[idx] = sample_index

    # Returns a List[Cluster] where Cluster is List[str] with the filenames.
    res = di.get_duplicate_clusters()
    with open('./deduplicate.jsonl', "w") as f:
        for item in res:
            for idx, val in enumerate(item["original_index"]):
                item["original_index"][idx] = idx_mapping[val]
            json.dump(item, f)
            f.write('\n')
    
