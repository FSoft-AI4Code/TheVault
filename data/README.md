# Data format

## Function-level and Class-level
- **repo** the owner/repo
- **path** the full path to the original file
- **identifier** the function or method name
- **license** repo license
- **original_string** the raw string before tokenization or parsing
- **language** the programming language
- **code** the part of the `original_string` that is code
- **code_tokens** tokenized version of `code`
- **docstring** the top-level comment or docstring (docstring version without param’s doc, return, exception, etc)
- **comment**
    - List of comment (line) inside the function/class
- **docstring_tokens** tokenized version of `docstring`
- **docstring_params**
    - **params**
        List of param's docstring (which actually is paramerter of the function). Each item in the list is a dictionary, sample example:
        - *identifier* (str): "a"
        - *docstring* (str): "this is a comment"
        - *docstring_tokens* (List): ['this', 'is', 'a', 'comment']
        - *default* (bool or None): null
        - *is_optional* (bool or None): null
        - [Optional field] *type* (str): 'int'    
    - **outlier_params** 
        The params which don’t list in the function declaration (e.g. `def cal_sum(a, b):`, if a param `c` is describe in docstring, then it is called outlier params). The syntax is similar with *params*
    - **returns** 
        List of returns. Example:
        - *type* (str): "int"
        - *docstring* (str): "sum of 2 value"
        - *docstring_tokens* (List): ['sum', 'of', '2', 'value']
    - **raises**
        List of raise/throw. Example:
        - *type* (str): "ValueError"
        - *docstring* (str): "raise if `ValueError` if a or b is not digit"
        - *docstring_tokens* (List): ['raise', 'if', '`', 'ValueError', '`', 'if', 'a', 'or', 'b', 'is', 'not', 'digit']
    - **others**
        List of other type of docstring params (e.g `version`, `author`, etc). Example:
        - *identifier* (str): "author"
        - *docstring* (str): "Dung Manh Nguyen"
        - *docstring_tokens* (List): ['Dung', 'Manh', 'Nguyen']

See the example below:
```python
def cal_sum(a: int, b: int):
    """
    This is demo function

    Args:
        a (int): this is a comment
        b (int): this is another comment
        c (int): this is a comment, but `c` is not `cal_sum`'s paramerter
    
    Returns:
        int: sum of 2 value
    
    Raise:
        ValueError: raise if `ValueError` if a or b is not digit
    """
    assert str(a).isdigit() == True, ValueError()
    assert str(b).isdigit() == True, ValueError()
    # return sum of `a` and `b`
    return a + b
```

Extract results:
```json
{
  "identifier": "plotpoints",
  "parameters": {
    "a": "int",
    "b": "int"
  },
  "repo": "",
  "path": "",
  "language": "Python",
  "license": "",
  "size": 10,
  "code": "",
  "code_tokens": [],
  "original_docstring": "This is demo function\n\n    Args:\n        a (int): this is a comment\n        b (int): this is another comment\n        c (int): this is a comment, but `c` is not `cal_sum`'s paramerter\n\n    Returns:\n        int: sum of 2 value\n\n    Raise:\n        ValueError: raise if `ValueError` if a or b is not digit",
  "docstring_tokens": [...],
  "comment": [
    "# return sum of `a` and `b`",
  ],
  "docstring": "This is demo function",
  "docstring_params": {
    "returns": [
      {
        "docstring": "sum of 2 value",
        "docstring_tokens": ["sum", "of", "2", "value"],
        "type": "int"
      }
    ],
    "raises": [
      {
        "docstring": "raise if `ValueError` if a or b is not digit",
        "docstring_tokens": ["raise", "if", "`", "ValueError", "`", "if", "a", "or", "b", "is", "not", "digit"],
        "type": "int"
      }
    ],
    "params": [
      {
        "identifier": "a",
        "docstring": "this is another comment",
        "type": "int",
        "docstring_tokens": ["this", "is", "another", "comment"]
      },
      {
        "identifier": "b",
        "docstring": "this is a comment",
        "type": "int",
        "docstring_tokens": ["this", "is", "a", "comment"]
      },
    ],
    "outlier_params": [
      {
        "identifier": "c",
        "docstring": "this is a comment, but `c` is not `cal_sum`'s paramerter",
        "type": "int",
        "docstring_tokens": ["this", "is", "a", "comment", ",", "but", "`", "c", "`", "'", "s", "parameter"]
      }
    ],
    "others": []
  }
}

```

## Inline-level
- **repo** the owner/repo
- **path** full path to the original file
- **language** the programming language
- **license** repo license
- **parent_name** method/class parent node name
- **code** the part of `original_string` that is code
- **code_tokens** tokenized version of code
- **prev_context** the (code) block above the comment
- **next_context** the (code) block below the comment
- **original_comment** the original comment before cleaning
- **start_point** (position of start line, position of start character)
- **end_point** (position of last line, position of last character)
- **comment** the cleaned comment
- **comment_tokens** tokenized version of comment

See the example below:
```python
def fix_init_kwarg(self, sender, args, kwargs, **signal_kwargs):
  # Anything passed in as self.name is assumed to come from a serializer and
  # will be treated as a json string.
  if self.name in kwargs:
    value = kwargs.pop(self.name)
    # Hack to handle the xml serializer's handling of "null"
    if value is None:
      value = 'null'
      kwargs[self.attname] = value
```

After extracting, we result:
```json
{
  "repo": "ithinksw/philo",
  "path": "philo/models/fields/__init__.py",
  "language": "Python",
  "code": "def fix_init_kwarg(self, sender, args, kwargs, **signal_kwargs):\n\t\t# Anything passed in as self.name is assumed to come from a serializer and\n\t\t# will be treated as a json string.\n\t\tif self.name in kwargs:\n\t\t\tvalue = kwargs.pop(self.name)\n\t\t\t\n\t\t\t# Hack to handle the xml serializer's handling of \"null\"\n\t\t\tif value is None:\n\t\t\t\tvalue = 'null'\n\t\t\t\n\t\t\tkwargs[self.attname] = value",
  "prev_context": null,
  "next_context": {
    "code": "if self.name in kwargs:\n\t\t\tvalue = kwargs.pop(self.name)\n\t\t\t\n\t\t\t# Hack to handle the xml serializer's handling of \"null\"\n\t\t\tif value is None:\n\t\t\t\tvalue = 'null'\n\t\t\t\n\t\t\tkwargs[self.attname] = value",
    "start_point": [3, 2],
    "end_point": [10, 31]
  },
  "original_comment": "# Anything passed in as self.name is assumed to come from a serializer and\n# will be treated as a json string.",
  "start_point": [1, 2],
  "end_point": [2, 2],
  "comment": "  Anything passed in as self.name is assumed to come from a serializer and \n  will be treated as a json string.",
  "comment_tokens": [
    "Anything",
    "passed",
    "in",
    "as",
    "self",
    ".",
    "name",
    "is",
    "assumed",
    "to",
    "come",
    "from",
    "a",
    "serializer",
    "and",
    "will",
    "be",
    "treated",
    "as",
    "a",
    "json",
    "string",
    "."
  ]
}
```