# Data Fields

## Function and Class level

- **repo** the owner/repo's name
- **path** the full path to the original file
- **identifier** the function/method's name
- **license** repo's license
- **stars_count** number of repo’s star (nullable)
- **issues_count** number of repo’s issue (nullable)
- **forks_count** number of repo’s fork (nullable)
- **original_string** original code snippet version of function/class node
- **original_docstring** the raw string before tokenization or parsing
- **language** the source programming language
- **code** the part of the "original_string" that is code
- **code_tokens** tokenized version of "code"
- **docstring** the top-level comment or docstring (docstring version without param’s doc, return, exception, etc)
- **docstring_tokens** tokenized version of `docstring`
- **short_docstring** first line of the "docstring"
- **short_docstring_tokens** tokenized version of "short_docstring"
- **comment** List of comment (line) inside the function/class node
- **parameters** Dict of parameter `identifier` and its `type` (`type` is nullable)
- **docstring_params**
    - **params** List of dictionary of param's docstring that are describe inside the "docstring". Fields: contains `identifier`, `docstring`, `docstring_tokens`, `type` (nullable), `default` (nullable), `is_optional` (nullable).
    - **outlier_params** List of the params which don’t belong to the function declaration*. The syntax is similar with "params".
    - **returns** List of returns. Field: `type`, `docstring`, `docstring_tokens`.
    - **raises** List of raise/throw. Field: `type`, `docstring`, ` docstring_tokens`.
    - **others** List of other type of docstring params (e.g `version`, `author`, etc). The field's name will be equal to their type's key.

**Notes: Outlier param for example `def cal_sum(a, b):`, if param `c` is describe in docstring, then it is called outlier params.*


## Inline level

- **repo** the owner/repo
- **path** full path to the original file
- **language** the programming language
- **license** repo's license
- **parent_name** name of the method/class parent node
- **original_string** full version of code snippet
- **code** the part of "original_string" that is code
- **code_tokens** tokenized version of code
- **prev_context** the (code) block above the comment
- **next_context** the (code) block below the comment
- **start_point** position of start line, position of start character
- **end_point** position of last line, position of last character
- **original_comment** the original comment before cleaning
- **comment** the cleaned comment
- **comment_tokens** tokenized version of comment