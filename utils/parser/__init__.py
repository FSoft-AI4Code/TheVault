import os
from typing import List, Dict, Any

from tree_sitter import Language, Parser

from .java_parser import JavaParser
from .python_parser import PythonParser


def extract_raw_code(raw_code, language, language_path='./my-languages.so') -> List[Dict[str, Any]]:
    """
    Extract information from raw_code though tree
    :param raw_code: raw (correctly syntax) code
    :type raw_code: str
    :param language: language (e.g: java, python, ...)
    :type language: str
    :param language_path: path to my-languages.so for load language, 
    if file not existed -> run build_grammars.py
    :type language_path: str
    
    .. example:
        >>> raw_code =  '''public class GoogleCloudStorageLocation extends DatasetLocation {
                            /**
                             * Get specify the bucketName of Google Cloud Storage. Type: string (or Expression with resultType string).
                             *
                             * @return the bucketName value
                             */
                            public Object bucketName(String[] args, int arg) {
                                return this.bucketName;
                            }
                        }
                        '''
        
        >>> print(extract_raw_code(raw_code, language='java')
        [{'type': 'method_declaration', 
         'identifier': 'GoogleCloudStorageLocation.bucketName', 
         'parameters': '', 
         'function': 'public Object bucketName() {\n        return this.bucketName;\n    }', 
         'function_tokens': ['public', 'Object', 'bucketName', '(', ')', '{', 'return', 'this', '.', 'bucketName', ';', '}'], 
         'docstring': '\nGet specify the bucketName of Google Cloud Storage. Type: string (or Expression with resultType string).\n\n@return the bucketName value\n'
        }]
    """
    parser = Parser()
    if os.path.exists(language_path):
        build_lang = Language(language_path, language)
    else: 
        pass  # build language
    parser.set_language(build_lang)
    
    tree = parser.parse(bytes(raw_code, 'utf8'))
    root = tree.root_node
    
    if language == 'python':
        function_list = PythonParser.get_function_definitions(root)
        return PythonParser.process_functions(function_list, raw_code)

    if language == 'java':
        return JavaParser.get_definition(tree, raw_code)