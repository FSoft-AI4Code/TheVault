# Split and Merge

## Merge
To merge the dataset (using multiprocessing), prepared a parent dir that contains all subdir (each subdir present a language raw set). It will read all *.jsonl and merge into `merged.jsonl`

For example:

```bash
root/
├── c
├── cpp
├── go
├── java
├── python
└── rust
```

To merge data
```bash
python -m src.analysis.split.merge --data_path "<path/to/dir>" --save_path "<path/to/save/dir>" --multiprocess --gen_id
```

Optional arguments:
```
  -h, --help            show this help message and exit
  --data_path DATA_PATH
                        path to dir contains multiple raw dataset to merge
  --multiprocess
                        multiprocessing
```

