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

Extract source code to function-description, class-description, code_line-description:
```bash
python parser_processing
```

## Data format
- **repo:** the owner/repo
- **path:** the full path to the original file
- **func_name:** the function or method name
- **original_string:** the raw string before tokenization or parsing
- **language:** the programming language
- **code/function:** the part of the `original_string` that is code
- **code_tokens/function_tokens:** tokenized version of `code`
- **docstring:** the top-level comment or docstring, if it exists in the original string
- **docstring_tokens:** tokenized version of `docstring`

Addition

- **processed_docstring:** docstring without param’s doc, return, exception, etc
- **processed_docstring_tokens:** token
- **docstring_params:**
    - **param_1_name:**
        - **docstring:** docstring of params_1 (`null` if not)
        - Optional(**type:** type)
    - **param_2_name:**
        - **docstring:** docstring of params_2 (`null` if not)
        - Optional(**type:** type)
    - . . .
    - **other_params:** other params which don’t list in the function init
        - List of param string (include param name)
    - **return:** docstring
    - **exception:** docstring
    - **[other_tag]:** docstring
