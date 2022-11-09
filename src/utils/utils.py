import os
import subprocess
import logging
from pathlib import Path

from tree_sitter import Language, Parser


ROOT_PATH = str(Path(__file__).parents[2])

logger = logging.getLogger('utils')
logging.basicConfig(level = logging.INFO)

def build_language(language: str, save_path: str=ROOT_PATH):
    """
    Build tree-sitter language
    
    Args:
        language (str): java, python, cpp, c_sharp, etc
        save_path (str): save path (default to /tree-sitter/)
    """
    ts_path = os.path.join(save_path, 'tree-sitter')
    ts_lang_path = os.path.join(ts_path, 'tree-sitter-'+language)
    if not os.path.exists(ts_path):
        logger.info(
            f"Not found tree-sitter folder, create new one in {ts_path}"
        )
        os.mkdir(ts_path)
    if not os.path.exists(ts_lang_path):
        logger.info(
            f"Not found tree-sitter-{language}, attempt clone from github"
        )
        command = f"cd tree-sitter; git clone https://github.com/tree-sitter/tree-sitter-{language}.git"
        subprocess.Popen(command ,shell=True).wait()
        
    lang_path = os.path.join(save_path, 'tree-sitter', f'{language}.so')
    if not os.path.exists(lang_path):
        logger.info(
            f"Attempt to build Tree-sitter Language for {language} and store in {lang_path}"
        )
        Language.build_library(lang_path, [ts_lang_path])
        assert os.path.exists(lang_path)==True
        

if __name__ == '__main__':
    lang_list = ['python', 'cpp', 'java', 'c-sharp', 'ruby', 'rust', 'javascript', 'php', 'go']
    
    for lang in lang_list:
        build_language(lang)


    