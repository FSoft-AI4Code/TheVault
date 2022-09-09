# Preprocessing code description

## Install dependencies
To getting started with preprocessing step, install dependencies:
```bash
pip install -r requirements.txt
```

## Dataset & Usage
Preprocessed dataset: [Googledrive](https://drive.google.com/drive/u/0/folders/1FGLK7HwP-W3wbFKefwNgV0IGjUvUxkYN)

This dataset was collected by `codeparrot` from open-source project on Github.
(More detail: [codeparrot/github-code](https://huggingface.co/datasets/codeparrot/github-code))

Extract dataset by languages into `.jsonl` file (store in `./data/raw`)
```bash
python crawl_data --n_samples 100 --languages Python C++ C#
```

Extract source code into mutilple file (for multiple thread later)
```bash
python raw_processing.py -n 10 --data_file './data/raw/python_data.jsonl' --save_path './data/python/
```

Extract source code to function-description, class-description (code_line-description) with n threads:
```bash
python parser_processing -n 10 --data_path './data/python' --save_path './data/python'
```

### Parser usage
Each language has it own parser, located in `utils/parser`

Using parser:
```python
from tree_sitter import Language, Parser
from utils.parser.java_parser import JavaParser

parser = Parser()
build_lang = Language('./path/to/my-languages.so', 'java')
parser.set_language(build_lang)

tree = parser.parse(bytes(raw_code, 'utf8'))
root = tree.root_node

print(JavaParser.get_definition(tree, raw_code))
```

Or use `extract_raw_code()` function:
```python
from utils.parser import extract_raw_code
raw_code =  '''public class GoogleCloudStorageLocation extends DatasetLocation {
            /**
                * Get specify the bucketName of Google Cloud Storage. Type: string (or Expression with resultType string).
                *
                * @return the bucketName value
                */
            public Object bucketName(String[] args, int arg) {
                return this.bucketName;
                }
            }
            '''
        
print(extract_raw_code(raw_code, language='java')
>>> [{'type': 'method_declaration', 
    'identifier': 'GoogleCloudStorageLocation.bucketName', 
    'parameters': '', 
    'function': 'public Object bucketName() {\n        return this.bucketName;\n    }', 
    'function_tokens': ['public', 'Object', 'bucketName', '(', ')', '{', 'return', 'this', '.', 'bucketName', ';', '}'], 
    'docstring': '\nGet specify the bucketName of Google Cloud Storage. Type: string (or Expression with resultType string).\n\n@return the bucketName value\n'
}]

```

## Data format
- **repo:** the owner/repo
- **path:** the full path to the original file
- **func_name/class_name:** the function or method name
- **license:** repo license
- **original_string:** the raw string before tokenization or parsing
- **language:** the programming language
- **code:** the part of the `original_string` that is code
- **code_tokens:** tokenized version of `code`

- **docstring:** the top-level comment or docstring, if it exists in the original string, docstring without param’s doc, return, exception, etc
    - **block_comment:** docstring
    - **comment:** docstring
- **docstring_tokens:** tokenized version of `docstring`
- **docstring_params:**
    - **param_1_name:**
        - **docstring:** docstring of params_1
        - Optional(**type:** type)
    - **param_2_name:**
        - **docstring:** docstring of params_2
        - Optional(**type:** type)
    - …
    - **other_params:** other params which don’t list in the function init
        - List of param string (include param name)
    - **@return:** comment
    - **@exception:** comment
    - **@….:** comment
