import pandas as pd
import json
import os
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'

from path import Path

import logging

from src.analysis.analyser import Analyser , repeat

logger = logging.getLogger()

root_dir = Path("/datadrive/dungnm31/data-ai4code/thestack")
langs = os.listdir(root_dir)
langs.remove("go")
langs.remove("c")
langs.remove("cpp")


from tqdm import tqdm

from multiprocessing import Pool

from decorators import timing_decorator
def read_file(filename):
    """Read the contents of a file and return a list of its lines"""
    with open(filename, 'r') as f:
        lines = f.readlines()
    return lines



# class LineDataset():



class LicenseFilter(Analyser):
    def __init__(self, args) -> None:
        super().__init__(args)

        self.dataset = []
        self.valid_licenses = ["MIT"]
    
    @timing_decorator
    def load_dataset(self, cores : int):
        print("Loading dataset ... ")
        filenames = []
        for lang in langs:
            src_dir  = root_dir / lang / "extracted"
            for filename in os.listdir(src_dir):
                filenames.append(src_dir / filename)
        # Create a pool of worker processes
        pool = Pool(processes=cores)
        
        # Use the pool to asynchronously read the files
        results = pool.map(read_file, filenames)
        
        # Flatten the list of lists into a single list
        lines = [line for sublist in results for line in sublist]
        
        # Close the pool and wait for the work to finish
        pool.close()
        pool.join()
        print("Done")
        print("Length of the dataset",len(lines))
        return lines
    
    def is_valid_license(self, line):
        data = json.loads(line)
        return data["license"] in self.valid_licenses
    
    def read_json(self, dataset, task):
        # from IPython import embed; embed()
        s = 'Analyzing '
        if not dataset:  # then read from path and processing
            assert type(task) == str
            assert os.path.isfile(task) == True
            s += str('file ' + Path(task).name)
            # with open(task, 'r') as json_file:
            #     dataset = list(json_file)
            task = range(len(dataset))
        else:
            s += f'from {task}'
        
        result = []
        for idx in tqdm(task, desc=s):
            data = dataset[idx]
            data = json.loads(data)
            if  data["license"] not in self.valid_licenses:
                result.append(data["license"])  
        return result
    
    @timing_decorator
    def analysing(self, dataset) -> None:
        if self.core != 0: # multiprocessing
            index_list = range(len(dataset))
            chunk_size = len(dataset)//self.core
            jobs = [index_list[x:x+chunk_size] for x in range(0, len(dataset), chunk_size)]
            logger.info(f"Analyzing {Path(self.data_path).name} in total {len(jobs)} processes")
            
            pool = Pool(processes=self.core)
            results = []
            logger.info("Start processing with {} cores".format(self.core))
            jobs_list = zip(repeat(dataset), jobs)
            for result in pool.starmap(self.read_json, jobs_list):
                results.extend(result)
            pool.close()
            pool.join()

        with open(self.save_path + "/" + "nv_licenses", "a") as f:
            print("Writing non valid results to file")
            f.writelines(results)
            

    @timing_decorator
    def identify(self, cores: int, lines):
        pool = Pool(processes=cores)
        
        # Use the pool to asynchronously read the files
        results = pool.map(self.is_valid_license, lines)
        
        # Flatten the list of lists into a single list
        lines = [line for sublist in results for line in sublist]
        
        # Close the pool and wait for the work to finish
        pool.close()
        pool.join()
        print("Done")
        print("Length of the boolean values",len(lines))
        return lines
 
 

if __name__=="__main__":
    import multiprocessing
    import argparse
    parser = argparse.ArgumentParser(description="Parallel dataset analyser")
    parser.add_argument(
        "data_path", 
        type=str, 
        help="root folder contains .jsonl or file .jsonl itself"
    )
    parser.add_argument(
        "--save_path",
        type=str,
        help="Save path",
    )
    parser.add_argument(
        "--raw",
        action='store_true',
        help="Analysis raw parallel set",
    )
    parser.add_argument(
        "--summary",
        action='store_true',
        help="",
    )
    parser.add_argument(
        "--split_factor",
        type=str,
        help="Consider factor when splitting, e.g. 'attribute,comment_length'",
    )    
    parser.add_argument(
        "--merge",
        action='store_true',
        help="Merge all .jsonl to 1 individual .jsonl",
    )
    parser.add_argument(
        "--deduplicate_factor",
        type=str,
        help="Consider factor when splitting, e.g. 'attribute,code_length'",
    )

    # data config
    parser.add_argument(
        "--language",
        type=str,
        default="python",
        help="",
    )
    parser.add_argument(
        "--load_metadata",
        type=str,
        default=None,
        help="",
    )
    parser.add_argument(
        "--split",
        action='store_true',
        help="",
    )
    parser.add_argument(
        "--deduplicate",
        action='store_true',
        help="Deduplicate",
    ) 
    parser.add_argument(
        "--is_file",
        action='store_true',
        help="Source data path is file or dir",
    )
    
    # compute config
    parser.add_argument(
        "--core",
        type=int,
        default=0,
        help="How many processor to use (-1 if for all)",
    )
    
    args = parser.parse_args()
    args.data_path = os.path.abspath(args.data_path)
    if args.core == -1:
        args.core = multiprocessing.cpu_count()
    multiprocessing.set_start_method("fork")


    filter = LicenseFilter()
    batch_size = 1024
    num_parallel_calls= 16
    lines =     filter.load_dataset(num_parallel_calls)
    filter.analysing(lines)
