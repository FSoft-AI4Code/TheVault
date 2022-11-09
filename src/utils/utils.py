import os
import subprocess
import logging
from pathlib import Path

import tree_sitter
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
        
        assert os.path.exists(ts_lang_path)==True, f"Unable to find {language} tree-sitter"
        
    lang_path = os.path.join(save_path, 'tree-sitter', f'{language}.so')
    if not os.path.exists(lang_path):
        logger.info(
            f"Attempt to build Tree-sitter Language for {language} and store in {lang_path}"
        )
        Language.build_library(lang_path, [ts_lang_path])
        assert os.path.exists(lang_path)==True
        
    
def parse_code(raw_code: str, language: str) -> tree_sitter.Tree:
    """
    Auto parse raw code into `tree_sitter.Tree`
    
    Args:
        raw_code (str): Raw source code need to parse
        language (str): Language to load parser
    """
    # TODO: auto detect language
    
    language = str(language).lower()
    if language == 'c#':
        language = 'c_sharp'
    elif language == 'c++':
        language = 'cpp'
            
    ts_lang_path = os.path.join(ROOT_PATH, 'tree-sitter', f'{language}.so')
    if not os.path.exists(ts_lang_path):
        build_language(language)
        
    parser = Parser()
    language = Language(ROOT_PATH + f"/tree-sitter/{language}.so", language)
    parser.set_language(language)
    
    if isinstance(raw_code, str):
        tree = parser.parse(bytes(raw_code, 'utf8'))
        return tree
    else:
        return
        

if __name__ == '__main__':
    lang_list = ['python', 'cpp', 'java', 'c-sharp', 'ruby', 'rust', 'javascript', 'php', 'go']
    
    for lang in lang_list:
        build_language(lang)


    