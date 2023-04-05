import pandas as pd
import json
from json.decoder import JSONDecodeError
import os
from path import Path
import pickle
import logging
from analysis.analyser import Analyser , repeat
from utils.decorators import timing_decorator
from multiprocessing import Queue, Pool, Process
import multiprocessing
from typing import List
from tqdm import tqdm


logger = logging.getLogger()

process_colors = ["#117a59",
    "#96928a",
    "#a367b2",
    "#78c98a",
    "#51684c",
    "#24c948",
    "#4b5b52",
    "#55b2a3",
    "#8e3bd6",
    "#fcdbba",
    "#2b603c",
    "#c66592",
    "#ba7891",
    "#2cc159",
    "#181916",
    "#0a0a08"
]

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
        self.parallel = args.parallel
        self.do_analyze = args.do_analyze
        self.license_only = args.license_only

        self.docstring_tokens_range = range(6, 500)
        self.code_tokens_range = range(6, 1000)
        self.special_char_thres = 0.1
        self.docstring_line_thres = 50
        # self.code_line_thres = 50
        
        
        self.conditions = ["has_valid_license", 
                           "valid_docstring_tokens_num",
                        #    "valid_docstring_lines_num", 
                           "valid_code_tokens_num", 
                        #    "valid_special_char_len", 
                        #    "valid_nodes"
                           ]
        if self.parallel:
            self.queue = Queue()
            self.multi_threads_vars = {"num_original": multiprocessing.Value("i", 0)}
            for condition in self.conditions:
                if hasattr(self, condition):
                    mutual_var = multiprocessing.Value("i", 0)
                    self.multi_threads_vars.update({condition: mutual_var})
        else:
            self.single_thread_vars = {"num_original": 0}
            for condition in self.conditions:
                if hasattr(self, condition):
                    self.single_thread_vars.update({condition: 0})
        
        self.non_valid_detected = []

    def load_dataset(self, file_name: str):
        filename = self.root_dir/file_name
        with open(filename, 'r', encoding="utf-8") as f:
            lines = f.readlines()
        return lines

    def has_valid_license(self, data):
        non_valid = [x for x in data["license"] if x not in self.valid_licenses]
        if non_valid:
            return False
        return True
    
    def valid_docstring_tokens_num(self, data):
        total_docs_tokens_num = len(data["docstring_tokens"])
        return total_docs_tokens_num in self.docstring_tokens_range
    
    def valid_code_tokens_num(self, data): 
        return len(data["code_tokens"])in self.code_tokens_range

    def valid_special_char_len(self, data):  
        return 

    def not_a_valid_sample(self, line):
        try:
            data = json.loads(line)
            try:
                methods = [getattr(self, condition) for condition in self.conditions]
                return any([not method(data) for method in methods])
            except KeyError as e :
                print(e)
                return False
        except json.decoder.JSONDecodeError as e:
            print(e)
            return False

    def filter_without_analysis(self, lines):
        if self.parallel:
            self.multi_threads_vars["num_original"].value += len(lines)
        else:
            self.single_thread_vars["num_original"] += len(lines)
        return list(filter(lambda x: not self.not_a_valid_sample(x) , lines))
    
    def filter_with_analysis(self, lines):
        filtered_lines = []
        for line in lines:
            if self.parallel:
                self.multi_threads_vars["num_original"].value += 1
            else:
                self.single_thread_vars["num_original"] += 1
            try:
                data = json.loads(line)
            except json.decoder.JSONDecodeError as e:
                print(e)
            
            is_valid_sample = True
            for condition in self.conditions:
                try:
                    method = getattr(self, condition)
                    if method(data):
                        # print("I am here")
                        if self.parallel:
                            self.multi_threads_vars[condition].value += 1
                        else:
                            self.single_thread_vars[condition] += 1
                    else:
                        is_valid_sample = False
                except KeyError as e :
                    print(e)
                
            if is_valid_sample:
                filtered_lines.append(line)
        
        return filtered_lines

    def not_valid_license(self, line):
        try:
            data = json.loads(line)
            try:
                non_valid = [x for x in data["license"] if x not in self.valid_licenses]
                if non_valid:
                    if self.parallel:
                        self.queue.put(non_valid)
                    else:
                        self.non_valid_detected.extend(non_valid)
                    return True
                else:
                    return False
            except KeyError as e :
                print(e)
                return True
        except json.decoder.JSONDecodeError as e:
            print(e)
            return True

    def filter_nonvalid_license(self, lines: List[str])->List[str]:
        return list(filter(self.not_valid_license, lines))
    
    def analysing(self, lines: List[str]) -> List[str]:
        if self.license_only:
            # print("I am here")
            return self.filter_nonvalid_license(lines)
        else:
            if not self.do_analyze:
                return  self.filter_without_analysis(lines)
            return self.filter_with_analysis(lines)
        
    def write_data(self, lines: List[str], file_name: str):
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        filename = Path(self.save_path) / f"{file_name}"
        with open(filename, "w") as f:
            f.writelines(lines)

    def process_single_file(self, file_name: str):
        original_lines = self.load_dataset(file_name=file_name)
        filtered_lines = self.analysing(lines=original_lines)
        self.num_original += len(original_lines)
        self.num_filtered += len(filtered_lines)
        self.write_data(filtered_lines, file_name=file_name)


    @timing_decorator
    def process_multi(self, filenames):
        for filename in tqdm(filenames):
            self.process_single_file(filename)

        if not self.parallel and self.license_only:
            self.non_valid_detected = list(dict.fromkeys(self.non_valid_detected))
        
    # num_original = multiprocessing.Value("i", 0)
    def process_single_file_with_queue(self, filenames: str, position: int, 
                                       num_original: multiprocessing.Value, 
                                       num_filtered: multiprocessing.Value):

        for file_name in tqdm(filenames, position=position, total=len(filenames), colour=process_colors[position]):
            original_lines = self.load_dataset(file_name=file_name)
            filtered_lines = self.analysing(lines=original_lines)
            self.write_data(filtered_lines, file_name=file_name)
            
            if self.license_only:
                num_original.value += len(original_lines)
                num_filtered.value += len(filtered_lines)

                while not self.queue.empty():
                    # print("Extracting non valid licenses from queue")
                    non_valid_detected = self.queue.get(timeout=5)
                    self.non_valid_detected.extend(non_valid_detected)

    @timing_decorator
    def process_multi_parallel(self, filenames):
        indices = list(range(len(filenames)))
        chunk_size = len(filenames)//self.core
        jobs = [filenames[x:x+chunk_size] for x in range(0, len(filenames), chunk_size)]
        logger.info(f"Analyzing {Path(self.data_path).name} in total {len(jobs)} processes")
        
        processes = []
        for (i, job) in enumerate(jobs):
            if self.license_only:
                p = Process(target=self.process_single_file_with_queue, args=(job,i, self.num_original, self.num_filtered))
            else:
                p = Process(target=self.process_single_file_with_queue, args=(job,i, self.num_original, self.num_filtered))
            
            p.start()
            processes.append(p)

        for p in processes:
           p.join()

        self.non_valid_detected = list(dict.fromkeys(self.non_valid_detected))
        if self.license_only:
            self.num_original = self.NUM_ORIGINAL.value
            self.num_filtered = self.NUM_FILTERED.value
    
    def make_detailed_report(self):
        self.result_dict = dict.fromkeys(self.conditions)

        if not self.parallel:
            self.result_dict = self.single_thread_vars
        else:
            for k, v in self.multi_threads_vars.items():
                self.result_dict[k] = v.value

        save_json = Path(self.save_path) / "results" / f"{self.language}.json"
        with open(save_json, "w") as f_json:
            f_json.write(json.dumps(self.result_dict))


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

    parser.add_argument(
        "--license_only",
        action='store_true',
        help="Filter only non valid licenses or not",
    )

    parser.add_argument(
        "--do_analyze",
        action='store_true',
        help="Do analysis for each condition",
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
    if args.license_only:
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
    else:
        l_filter.make_detailed_report()
    # batch_size = 1024
    # num_parallel_calls= 16
