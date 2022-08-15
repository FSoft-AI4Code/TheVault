import os
import json
import argparse
import logging
from tqdm import tqdm

from datasets import load_dataset


logger = logging.getLogger("logger_name")
logging.basicConfig(format='%(message)s', level=logging.INFO)


def args():
    parser = argparse.ArgumentParser(description='Crawl data arguments')
    parser.add_argument('--save_dir', type=str, default='./data')
    parser.add_argument('-l', '--languages', default=['Python'], nargs='+')
    parser.add_argument('-n', '--n_samples', type=int, default=100)
    parser.add_argument('--licenses', default=None, nargs='+')

    return parser.parse_args()
    

def save_crawed_data(dataset, save_dir, language):
    save_dir = os.path.join(save_dir, 'raw')
    
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    
    save_file = os.path.join(save_dir, f'{str(language).lower()}_data.jsonl')
    
    # for idx, item in enumerate(dataset):
    with open(os.path.join(save_file), "a") as outfile:
        json_object = json.dump(dataset, outfile)
        outfile.write('\n')

    
def crawl_language(languages, n_samples, save_dir, licenses=None):
    for lang in languages:
        logger.info(f'Crawl code from languages: {lang}')
        ds = load_dataset("codeparrot/github-code",
                               streaming=True,
                               languages=[lang],
                               licenses=licenses if licenses is not None else [],
                               split="train")
        
        dataset = iter(ds)
        
        print(next(dataset))
        # for idx in range(n_samples):
            # print('hello', data_point)
            # # data.append(data_point)
                
            # if (lang == "C++"): lang = "Cpp"
            # if (lang == "C#"): lang = "Csharp"
            # save_crawed_data(data_point, save_dir, lang)
            
        # logger.info(f'Done')
        

    
if __name__ == '__main__':
    opt = args()
    save_dir, languages, n_samples, licenses = opt.save_dir, \
        opt.languages, opt.n_samples, opt.licenses
    
    crawl_language(languages, n_samples, save_dir, licenses)
