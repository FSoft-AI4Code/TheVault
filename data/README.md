# Data format

## Function-level and Class-level
- **repo:** the owner/repo
- **path:** the full path to the original file
- **func_name/class_name:** the function or method name
- **license:** repo license
- **original_string:** the raw string before tokenization or parsing
- **language:** the programming language
- **code:** the part of the `original_string` that is code
- **code_tokens:** tokenized version of `code`
- **docstring:** the top-level comment or docstring, if it exists in the original string, docstring without param’s doc, return, exception, etc
- **comment**:
    - ['This is first comment', ['This', 'is', 'first', 'comment']]     # 0 is comment, 1 is tokenize version of it
    - ['This is second comment', ['This', 'is', 'second', 'comment']]

    <!-- - **block_comment:** docstring
    - **comment:** docstring -->
- **docstring_tokens:** tokenized version of `docstring`
- **docstring_params:**
    - **param_1_name:**
        - **docstring:** docstring of params_1
        - Optional(**type:** type)
        - **param_tokens**: tokenized version of `param`
    - **param_2_name:**
        - **docstring:** docstring of params_2
        - Optional(**type:** type)
        - **param_tokens**: tokenized version of `param`        
    - …
    - **other_params:** other params which don’t list in the function init
        - List of param string (include param name)
    - **@return:** its documentation
    - **@exception:** its documentation
    - **@….:** ...

## Inline-level
- **repo**: the owner/repo
- **path:** full path to the original file
- **language:** the programming language
- **license:** repo license
- **parent_name:** method/class parent node name
- **code:** the part of `original_string` that is code
- **code_tokens**: tokenized version of code
- **prev_context:** the (code) block above the comment
- **next_context:** the (code) block below the comment
- **original_comment:** the original comment before cleaning
- **start_point:** (position of start line, position of start character)
- **end_point:** (position of last line, position of last character)
- **comment:** the cleaned comment
- **comment_tokens:** tokenized version of comment