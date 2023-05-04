import os
import argparse
import logging
from pathlib import Path

import multiprocessing

from utils import create_logger
from analysis.analyser import Analyser




def analysis(args) -> str:
    create_logger(filepath=None, rank=0)
    logger = logging.getLogger()
    
    assert type(args.data_path) == str and args.data_path != '', "Error `data_path`"
    if os.path.isfile(args.data_path):
        args.is_file = True
        logger.info(f"Analysis data from file: {args.data_path}")
    else:
        logger.info(f"Analysis data from directory: {args.data_path}")
    
    if not args.save_path and not args.is_file:
        args.save_path = args.data_path
    # else:
        
    #     args.save_path = Path(args.data_path).parent
    
    analyser = Analyser(args)
    if args.merge:
        assert args.is_file != True, "Can not merge single file, error `data_path`"
        analyser.merge()
    
    if args.split:
        analyser.split()
    
    
    analyser.analysing()


if __name__ == '__main__':
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
    
    # run = neptune.init_run(project='nmd2000/AI4Code-Dataset')
    # run["Languages"] = args.language
    # run["Data path"] = args.data_path
    # run["Core"] = args.core
    
    # args.tracker = run
    analysis(args)
    # run.stop()