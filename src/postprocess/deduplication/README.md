# Deduplication

`deduplication` provide each sample an unique IDs using SHA-256 and Jaccard similarities for deduplication (inside the dataset or compare with other dataset)

```bash
python -m src.analysis.deduplication.deduplication --data_path `path/to/dir`
```