<div align="center">

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/115590550?s=200&v=4" width="220px" alt="logo">
</p>

**The Vault: Open source parallel data extractor**
__________________________


<!-- Badge start -->
| Branch 	| Build 	| Unittest 	| Linting 	| Release 	| License 	|
|--------	|-------	|----------	|---------	|---------	|---------	|
| main   	|       	| [![Unittest](https://github.com/AI4Code-Research/CodeText-data/actions/workflows/unittest.yml/badge.svg)](https://github.com/AI4Code-Research/CodeText-data/actions/workflows/unittest.yml) |       	| [![release](https://img.shields.io/pypi/v/codetext)](https://pypi.org/project/codetext/) [![pyversion](https://img.shields.io/pypi/pyversions/codetext)](https://pypi.org/project/codetext/)| [![license](https://img.shields.io/github/license/AI4Code-Research/CodeText-data)](https://github.com/AI4Code-Research/CodeText-data/LICENSE.txt) |
<!-- Badge end -->
</div>

# Relevant Links
[The Vault paper](https://arxiv.org) | [The Vault on HuggingFace datasets](https://huggingface.co/datasets?search) <img alt="Hugging Face Datasets" src="https://img.shields.io/badge/-%F0%9F%A4%97%20datasets-blue"> </a >

__________________
# Table of content
1. [The Vault](#the-vault)
  i. [Data Summary](#data-summary)
  ii. [Data Structure](#data-structure)
  iii. [Data Split](#data-split)
2. [CodeText toolkit](#codetext-toolkit)
  i. [Installation](#installation)
  ii. [Processing Pipeline](#processing-pipeline)
  iii. [Processing Custom Dataset](#processing-custom-dataset)

___________
# The Vault Dataset
## Data Summary
The Vault dataset is a comprehensive, large-scale, multilingual parallel dataset that features high-quality code-text pairs derived from The Stack, the largest permissively-licensed source code dataset.

We design The Vault to extract code snippets from 10 popular programming languages such as Java, JavaScript, Python, Ruby, Rust, Golang, C#, C++, C, and PHP. This dataset provides multiple code-snippet levels, metadata, and 11 docstring styles for enhanced usability and versatility.

![Something something](./assets/Poster_The%20Vault.jpg)
## Data Structure

## Data Split

## Load dataset
We support load our dataset via Huggingface datasets hub:

```python
!pip install datasets

from datasets import load_dataset

# Load full function dataset (40M samples)
ds = load_dataset("NamCyan/thevault", split="function")

# Load function "small" trainset (or "medium", "large") 
ds = load_dataset("NamCyan/thevault", split="function/train_small")

# Load only function testset
ds = load_dataset("NamCyan/thevault", split="function/test")

# specific language (e.g. Golang) 
ds = load_dataset("NamCyan/thevault", split="function/train", languages=['Go'])

# streaming load (that will only download the data as needed)
ds = load_dataset("NamCyan/thevault", split="function/train", streaming=True)

```
# The Vault Toolkit
## Getting Started

To setup environment and install dependencies via `pip`:
```bash
pip -r install requirements.txt
```

Install `codetext` parser to extract code using [tree-sitter](https://tree-sitter.github.io/tree-sitter/), via `pip`:
```bash
pip install codetext
```

Or manually build `codetext` form source, see more at [`Codetext` repo](https://github.com/FSoft-AI4Code/CodeText-parser)
```bash
git clone https://github.com/FSoft-AI4Code/CodeText-parser.git
cd CodeText-parser
pip install -e .
```

## Processing Pipeline

### Extracting raw code

### Filtering extracted code snippet

### Processing Custom Dataset
We create a `.yaml` to define which field to load when processing data. Usually, only source code are needed, but in case there are other additional information about the raw code might be added using the `.yaml`.

For example, `CodeSearchNet` stores their data in structure:

```yaml
# CodeSearchNet jsonline format 
# https://github.com/github/CodeSearchNet#data-details

code: original_string # raw code
repo: repo # additional infor
path: path # additional infor
language: language # additional infor
```

```bash
python -m codetext.processing 
<DATASET_PATH>
--save_path <SAVE_PATH>  # path to save dir

--load_from_file  # load from file instead load from dataset cache
--language Python  # or Java, JavaScript, ...
--data_format './data/format/codeparot-format.yaml'  # load raw data format

--n_split 20  # split original dataset into N subset
--n_core -1  # number of multiple processor (default to 1) (-1 == using all core)
```

Arguments list:
```
positional arguments:
  data_path             data folder contain file.jsonl or huggingface dataset cache

options:
  -h, --help            show this help message and exit
  --save_path SAVE_PATH
                        Processed data save path
  --level LEVEL         Extract function/class/inline level or all
  --language LANGUAGE   Declare processing language (e.g: Python, Java)
  --data_format DATA_FORMAT
                        Path to file .yaml contains data format
  --load_from_file      Load from .json or .jsonl
  --cons_from_raw       Continues from raw .jsonl (pass folder path to data)
  --raw_only
  --filtered_only
  --extracted_only
  --n_split N_SPLIT     Split all the raw data into N file and feed into process pool
  --n_core N_CORE       Number of maximum process to create
  --debug
```

## Technical Report and Citing the Vault
More details can be found in our [technical report](https://arxiv.org/abs/). 

<!-- If you're using The Vault or the toolkit in your research or applications, please cite using this BibTeX:
```bibtex
@misc{,
      title={}, 
      author={},
      year={2022},
      eprint={},
      archivePrefix={},
      primaryClass={}
}
```-->

## Contact us
If you have any questions, comments or suggestions, please do not hesitate to contact us at [email].

## License
[MIT License](LICENSE.txt)
