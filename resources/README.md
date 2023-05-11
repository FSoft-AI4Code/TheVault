## Downloading Data from Azure blob storage

The Azure download link follow this pattern:
> https://ai4code.blob.core.windows.net/thevault/v1/{function, class, inline}/{python,java,javascript,go,cpp,c_sharp,c, rust, ruby, php}.zip

For example, download *class* of *Python*:
> https://ai4code.blob.core.windows.net/thevault/v1/class/python.zip

Or download using the script [`download_dataset.py`](./download_dataset.py):
```bash
python download_dataset.py "<path/to/destination>" --set "function" # or class/inline
```

The dataset is approximately ~xxGB.