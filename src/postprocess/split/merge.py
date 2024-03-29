import os
import glob
from tqdm import tqdm
from multiprocessing import Pool
from argparse import ArgumentParser
from codetext.parser.language_parser import tokenize_docstring
from codetext.clean import remove_comment_delimiters

import nltk
import hashlib
import json
import csv

def get_first_sentence(paragraph):
    """
    Returns the first sentence of a given paragraph of text.
    """
    # Tokenize the paragraph into sentences
    paragraph = remove_comment_delimiters(paragraph)
    first_para = paragraph.split('\n\n')[0]
    
    sentences = nltk.sent_tokenize(first_para)
    
    # Iterate over the sentences to find the first one that is not empty
    for sentence in sentences:
        if len(sentence.strip()) > 0:
            return sentence.strip()
    
    # If all sentences are empty, return an empty string
    return ''

def get_sample_id(description: str):
    """
    Generates a unique ID for a sample based on its description string.
    """
    hash_object = hashlib.sha256(description.encode())
    # The hexdigest() method returns a string representation of the hash.
    return hash_object.hexdigest()


def parse_args():
    parser = ArgumentParser(description='merge dataset')
    parser.add_argument(
        "--data_path",
        type=str,
        help="path to dir contains multiple raw dataset to merge",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        help="path to save merge file",
    )
    parser.add_argument(
        "--multiprocess",
        action='store_true',
        help="multiprocessing",
    )
    parser.add_argument(
        "--gen_id",
        action='store_true',
        help="Given SHA-256 IDs for samples",
    )
    return parser.parse_args()


def merge_files(args):
    idx, data_path, save_path = args
    filename = os.path.basename(os.path.normpath(data_path))
    
    # Add path here
    data_path = os.path.join(data_path) #, 'function', 'extracted_2')
    file_list = glob.glob(os.path.join(data_path, '*.jsonl'))
    output_filename = os.path.join(save_path, f'{filename}_merged.jsonl')
    csv_output_filename = os.path.join(save_path, f'{filename}_meta.csv')
    
    metadata = []
    
    with open(output_filename, 'w') as outfile:
        for filename in tqdm(file_list, position=idx, desc=f'Merging files in {data_path}', leave=False):
            with open(filename, 'r') as infile:
                dataset = list(infile)
                for line in dataset:
                    data = json.loads(line)
                    
                    code = data['code']
                    repo = data['repo']
                    docs_len = len(data['docstring_tokens'])
                    code_len = len(data['code_tokens'])
                    idx = get_sample_id(code)
                    data['id'] = idx
                    
                    if 'short_docstring' not in data.keys():
                        short_docstring = get_first_sentence(data['docstring'])
                        data['short_docstring'] = short_docstring
                        data['short_docstring_tokens'] = tokenize_docstring(short_docstring)
                    
                    # for metadata.csv
                    metadata.append([idx, repo, code_len, docs_len])
                    
                    json.dump(data, outfile)
                    outfile.write('\n')
    
    fields = ['ID', 'Repo Name', 'Code Length', 'Docs Length']
    # Open the CSV file and write the data to it
    with open(csv_output_filename, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(fields)
        writer.writerows(metadata)


if __name__ == '__main__':
    opt = parse_args()
    data_path = opt.data_path
    save_path = opt.save_path or opt.data_path
    subdirs = [os.path.join(data_path, d) for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))]
    
    if opt.multiprocess:
        with Pool(processes=len(subdirs)) as pool:
            args = [(idx, subdir, save_path) for idx, subdir in enumerate(subdirs)]
            pool.map(merge_files, args)
    else:
        for subdir in subdirs:
            merge_files(subdir)
