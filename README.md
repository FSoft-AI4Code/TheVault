<div align="center">

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/115590550?s=200&v=4" width="220px" alt="logo">
</p>

**Code-Text data toolkit**
______________________________________________________________________


<!-- Badge start -->
| Branch 	| Build 	| Unittest 	| Linting 	| Release 	| License 	|
|--------	|-------	|----------	|---------	|---------	|---------	|
| main   	|       	| [![Unittest](https://github.com/AI4Code-Research/CodeText-data/actions/workflows/unittest.yml/badge.svg)](https://github.com/AI4Code-Research/CodeText-data/actions/workflows/unittest.yml) |       	| [![release](https://img.shields.io/pypi/v/codetext)](https://pypi.org/project/codetext/) [![pyversion](https://img.shields.io/pypi/pyversions/codetext)](https://pypi.org/project/codetext/)| [![license](https://img.shields.io/github/license/AI4Code-Research/CodeText-data)](https://github.com/AI4Code-Research/CodeText-data/LICENSE.txt) |
<!-- Badge end -->
</div>

______________________________________________________________________

**Code-Text data toolkit** contains multilingual programming language parsers for the extract from raw source code into multiple levels of pair data (code-text) (e.g., function-level, class-level, inline-level). 

# Installation
Setup environment and install dependencies and setup by using `install_env.sh`
```bash
bash -i ./install_env.sh
```
then activate conda environment named "code-text-env"
```bash
conda activate code-text-env
```

*Setup for using parser*
```bash
pip install codetext
```

# Getting started

## Build your language
Auto build tree-sitter into `<language>.so` located in `/tree-sitter/`
```python
from codetext.utils import build_language

language = 'rust'
build_language(language)


# INFO:utils:Not found tree-sitter-rust, attempt clone from github
# Cloning into 'tree-sitter-rust'...
# remote: Enumerating objects: 2835, done. ...
# INFO:utils:Attempt to build Tree-sitter Language for rust and store in .../tree-sitter/rust.so
```

## Language Parser
We supported 10 programming languages, namely `Python`, `Java`, `JavaScript`, `Golang`, `Ruby`, `PHP`, `C#`, `C++`, `C` and `Rust`.

Setup
```python
from codetext.utils import parse_code

raw_code = """
/**
* Sum of 2 number
* @param a int number
* @param b int number
*/
double sum2num(int a, int b) {
    return a + b;
}
"""

root = parse_code(raw_code, 'cpp')
root_node = root.root_node
```

Get all function nodes inside a specific node, use:
```python
from codetext.utils.parser import CppParser

function_list = CppParser.get_function_list(root_node)
print(function_list)

# [<Node type=function_definition, start_point=(6, 0), end_point=(8, 1)>]

```

Get function metadata (e.g. function's name, parameters, (optional) return type)
```python
function = function_list[0]

metadata = CppParser.get_function_metadata(function, raw_code)

# {'identifier': 'sum2num', 'parameters': {'a': 'int', 'b': 'int'}, 'type': 'double'}
```
Get docstring (documentation) of a function
```python
docstring = CppParser.get_docstring(function, code_sample)

# ['Sum of 2 number \n@param a int number \n@param b int number']
```

We also provide 2 command for extract class object
```python
class_list = CppParser.get_class_list(root_node)
# and
metadata = CppParser.get_metadata_list(root_node)
```

# Data collection and Preprocessing
The dataset we used to extract was collected by codeparrot. They host the raw dataset in here [codeparrot/github-code](https://huggingface.co/datasets/codeparrot/github-code).

*You can create your own dataset using Google Bigquery and the [query here](https://huggingface.co/datasets/codeparrot/github-code/blob/main/query.sql)*

## Getting started
### Process custom dataset
For start preprocessing data, define a .yaml file to declare raw data format. (More detail: `/data/format/README.md`)

```bash
python -m codetext.processing 
<DATASET_PATH>
--save_path <SAVE_PATH>  # path to save dir

--load_from_file  # load from file instead load from dataset cache
--language Python  # or Java, JavaScript, ...
--data_format './data/format/codeparot-format.yaml'  # load raw data format

--n_split 20  # split original dataset into N subset
--n_core -1  # number of multiple processor (default to -1 == using all core)
```

*NOTES:*  <DATASET_PATH> dir must contains raw data store in `.jsonl` extension if you pass argument `--load_from_file` or contains huggingface dataset's 

### Analyse and split dataset
The code process is going to save cleaned sample by batch, you can merge it using `postprocess.py`. We also provide analyse tool for get total number of sample, blank_line(\*), comment(\*) and code(\*). You can also split your dataset into `train`, `valid`, `test`.

```bash
python -m codetext.postprocessing 
<DATASET_PATH>  # path to dir contains /extracted, /filered, /raw
--save_path <SAVE_PATH>  # path to save final output

--n_core 10  # number of core for multiprocessing analyzer
--analyze  # Analyze trigger
--split  # Split train/test/valid trigger
--ratio 0.05  # Test and valid ratio (defaul to equal)
--max_sample 20000  # Max size of test set and valid set
```

*NOTES:* (\*) We run `cloc` underneath the program to count blank, comment and code. See more [github.com/AlDanial/cloc](github.com/AlDanial/cloc)