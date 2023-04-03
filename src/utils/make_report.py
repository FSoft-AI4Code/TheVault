import os
import json
import pandas as pd

languages = ["c", 
             "cpp",
             "c_sharp", 
             "python", 
             "java", 
             "ruby", 
            #  "javascript",
            #  "go" 
            ]

def aggregate_license():
    licenses = []
    for lang in languages :
        with open(f"/datadrive/minhna4/tmp/non_valid/{lang}/results/{lang}.json", "r") as f:
            licenses.extend(json.load(f)["non_valid_licenses"])
    licenses = list(dict.fromkeys(licenses))
    pd.DataFrame({"non_valid_licenses": licenses}).to_csv("non_valid.csv")




aggregate_license()
