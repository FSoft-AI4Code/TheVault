import os
import json
import csv
import glob
from tqdm import tqdm
import multiprocessing as mp


def index_mapping(iterator):
    sets, sample = iterator
    sample = json.loads(sample)
    for set_name, ids in sets.items():
        if sample["id"] in ids:
            return set_name, sample
    return 'train', sample


def index_mapping_iter(sample_iterator):
    with mp.Pool() as pool:
        for res in pool.imap_unordered(
            index_mapping,
            sample_iterator
        ):
            if res is not None:
                yield res


def processing(data_path, _idx):
    language = os.path.basename(os.path.normpath(data_path))
    csv_files = ["medium_train.csv", "small_train.csv", "test.csv", "eval.csv"]
    sets = {}
    writer_list = {}
    for _csv in csv_files:
        path = os.path.join(data_path, f"{language}_{_csv}")
        set_name = _csv.replace('.csv', '')
        writer_list[set_name] = open(os.path.join(data_path, f"{set_name}.jsonl"), 'w')
        with open(path, 'r') as f:
            reader = csv.reader(f)
            ids = [row[0] for row in reader]
            sets[set_name] = ids
    writer_list['train'] = open(os.path.join(data_path, f"full_train.jsonl"), 'w')
    
    with open(os.path.join(data_path, f'{language}_merged.jsonl'), 'r') as file:
        dataset = list(file)
        args = [(sets, item) for item in dataset]
        for set_name, data_point in tqdm(index_mapping_iter(args), desc=data_path, total=len(dataset), position=_idx, leave=False):
            json.dump(data_point, writer_list[set_name])
            writer_list[set_name].write('\n')
            if set_name not in ['eval', 'test', 'train']:
                json.dump(data_point, writer_list['train'])
                writer_list['train'].write('\n')


def main():
    data_path = "/Users/nmd2000/Workspace/codetext/test_mapping"
    languages = glob.glob(os.path.join(data_path, '*'))
    print(languages)

    for idx, _lang in enumerate(languages):
        processing(_lang, idx)


if __name__ == "__main__":
    main()
