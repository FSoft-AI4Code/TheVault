import os
import json
languages = ["c", 
             "cpp",
             "c_sharp", 
            #  "python", 
             "java", 
             "ruby", 
            #  "javascript",
            #  "go" 
            ]

def aggregate_license():
    licenses = []
    for lang in languages :
        with open(f"/datadrive/minhna4/tmp/non_valid/{lang}/results/{lang}.json", "r") as f:
            licenses.extend()

