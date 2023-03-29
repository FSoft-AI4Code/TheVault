import pandas as pd
import json
from json.decoder import JSONDecodeError
import os

from path import Path
import pickle
import logging

from analysis.analyser import Analyser , repeat


from datasets import load_dataset

from p_tqdm import p_map

logger = logging.getLogger()

lang= "python"

root_dir = Path(f"/datadrive/dungnm31/data-ai4code/thestack/{lang}")


from tqdm import tqdm

from multiprocessing import Pool

from utils.decorators import timing_decorator

class LicenseFilter(Analyser):
    def __init__(self, args) -> None:
        super().__init__(args)
            
        self.valid_licenses = ["MIT", 
                               "Apache-2.0", 
                               "BSD-3-Clause", 
                               "BSD-2-Clause", 
                               "CC0-1.0", 
                               "CC-BY-4.0",
                               "CC-BY-3.0", 
                            #    "CC-BY-2.0", 
                               "0BSD", 
                               "RSA-MD", 
                               "WTFPL", 
                               "MIT-0"]
        
        self.root_dir = Path(self.data_path)
        self.num_original: int = 0
        self.num_filtered: int = 0
        self.non_valid_detected = []
        self.parallel = args.parallel

    # @timing_decorator
    def load_dataset(self, file_name: str):
        """Read the contents of a file and return a list of its lines"""
        # filename = Path(self.data_path) / "python_merged_data.jsonl"
        filename = self.root_dir/file_name
        with open(filename, 'r', encoding="utf-8") as f:
            lines = []
            lines = f.readlines()
        self.num_original += len(lines)
        return lines


    def not_valid_license(self, line):
        try:
            # print(line)
            data = json.loads(line)
            try:
                # print(data["license"])
                non_valid = [x for x in data["license"] if x not in self.valid_licenses]
                self.non_valid_detected.extend(non_valid)
                if non_valid:
                    return True
                else:
                    return False
            except KeyError as e :
                print(e)
                return True
        except json.decoder.JSONDecodeError as e:
            print(e)
            return True

    def filter_nonvalid_license(self, lines: list)->list:
        return list(filter(self.not_valid_license, lines))
    
    # @timing_decorator
    def analysing(self, lines) -> None:
        filtered_list = self.filter_nonvalid_license(lines)
        self.num_filtered += len(filtered_list)
        # print("Length of filtered list", len(filtered_list))
        return filtered_list

    # @timing_decorator
    def write_data(self, lines, file_name):
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        filename = Path(self.save_path) / f"{file_name}"
        with open(filename, "w") as f:
            # for line in lines:
            f.writelines(lines)

    # @timing_decorator
    def process_single_file(self, file_name: str):
        original_lines = l_filter.load_dataset(file_name=file_name)
        non_valid_lines = l_filter.analysing(lines=original_lines)
        l_filter.write_data(non_valid_lines, file_name=file_name)

    def process_multi(self, filenames):
        for filename in tqdm(filenames):
            self.process_single_file(filename)
        if not self.parallel:
            self.non_valid_detected = list(dict.fromkeys(self.non_valid_detected))
        else:
            return
    def process_multi_parallel(self, filenames):
        indices = list(range(len(filenames)))
        
        chunk_size = len(filenames)//self.core
        jobs = [filenames[x:x+chunk_size] for x in range(0, len(filenames), chunk_size)]
        logger.info(f"Analyzing {Path(self.data_path).name} in total {len(jobs)} processes")
        
        pool  = Pool(processes=self.core)
                
        for result in pool.map(self.process_multi, jobs):
            result = result
        
        pool.close()
        pool.join()
        self.non_valid_detected = list(dict.fromkeys(self.non_valid_detected))

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
    
    # compute config
    parser.add_argument(
        "--parallel",
        action='store_true',
        help="Parallel Multiprocessing or not",
    )
    
    
    args = parser.parse_args()
    args.data_path = os.path.abspath(args.data_path)
    if args.core == -1:
        args.core = multiprocessing.cpu_count()
    multiprocessing.set_start_method("fork")


    l_filter = LicenseFilter(args)
    if l_filter.parallel:
        l_filter.process_multi_parallel(os.listdir(l_filter.root_dir))
    else:
        l_filter.process_multi(os.listdir(l_filter.root_dir))
    if not os.path.exists(Path(l_filter.save_path) / "results"):
        os.mkdir(Path(l_filter.save_path) / "results" )
    
    # save_txt = Path(l_filter.save_path) / "results" / f"{l_filter.language}.txt"
    save_json = save_txt = Path(l_filter.save_path) / "results" / f"{l_filter.language}.json"
     
    with open(save_json, "w") as f_json:
        
        num_filtered = l_filter.num_filtered
        num_original = l_filter.num_original

        filtered_perc = l_filter.num_filtered*100/ l_filter.num_original
        nvl = l_filter.non_valid_detected

        result_dict = {
            "language": l_filter.language,
            "original": num_original,
            "filtered": num_filtered,
            "non_valid_licenses": nvl
        }

        f_json.write(json.dumps(result_dict))
    
    # batch_size = 1024
    # num_parallel_calls= 16
