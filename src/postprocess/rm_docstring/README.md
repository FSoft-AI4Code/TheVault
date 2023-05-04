# Remove docstring 

Run the script to remove the docstring/comments remains in side `code` field:
```bash
python -m rm_docstring --data_path "<path/to/dir>" --multiprocess

```

_Note: `multiprocess` tag will init individual process to handle certain jsonl file. Otherwise, 1 process will take care all jsonl file_

For example, an `code` field like this:
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

After go through `remove_docstring()` will result:
```python
def cal_sum(a: int, b: int):
    assert str(a).isdigit() == True, ValueError()
    assert str(b).isdigit() == True, ValueError()
    return a + b
```