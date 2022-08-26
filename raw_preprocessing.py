import os
import json
import argparse
from tqdm import tqdm
import concurrent.futures
from datasets import load_dataset
from tqdm import tqdm

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_file', type=str, default='./data/raw/python_data.jsonl')
    parser.add_argument('--save_path', type=str, default='./data/python/')
    parser.add_argument('-n', '--n_file', type=int, default=10)

    return parser.parse_args()


def save_file_from_raw(data, index, save_dir, thread_id):
    count = 0
    for idx in tqdm(index):
        count += 1
        item = json.loads(data[idx])
        item_id = item['repo_name'] + '/' + item['path']

        print(f'Thread {thread_id} crawling data: {count} samples | Processing: {item_id}')
        if count % 50 == 0:
            os.system('clear')
    
        with open(os.path.join(save_dir, f'{thread_id}_batch.jsonl'), "a") as outfile:
            json_object = json.dump(item, outfile)
            outfile.write('\n')
    
        with open(os.path.join(save_dir, f'_cache_{thread_id}.txt'), "w") as outfile:
            outfile.write(item_id)


# if __name__ == '__main__':
#     opt = args()
#     file, n, save_dir = opt.data_file, opt.n_file, opt.save_path
#     dataset = load_dataset("codeparrot/github-code", languages=['Python'], split='train', cache_dir='./cache')
    
#     dataset_size = len(dataset)
#     chunk_size = dataset_size//n
#     thread_jobs = [dataset[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
    
#     with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
#         futures = []
#         for ids, job in enumerate(thread_jobs):
#             futures.append(executor.submit(save_file_from_raw, data=dataset, index=job, save_dir=save_dir, thread_id=ids))
#         for future in concurrent.futures.as_completed(futures):
#             print(future.result())
    
if __name__ == '__main__':
    opt = args()
    file, n, save_dir = opt.data_file, opt.n_file, opt.save_path
    
    with open(file, 'r') as json_file:
        json_list = list(json_file)
        
        dataset_size = len(json_list)
        index_list = range(dataset_size)
        chunk_size = dataset_size//n
        thread_jobs = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
            futures = []
            for ids, job in enumerate(thread_jobs):
                futures.append(executor.submit(save_file_from_raw, data=json_list, index=job, save_dir=save_dir, thread_id=ids))
            for future in concurrent.futures.as_completed(futures):
                print(future.result())
    