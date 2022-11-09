import os
from typing import List, Dict, Any

from tree_sitter import Language, Parser
from src.utils.parser.go_parser import GoParser
from src.utils.parser.php_parser import PhpParser
from src.utils.parser.ruby_parser import RubyParser
from src.utils.parser.java_parser import JavaParser
from src.utils.parser.javascript_parser import JavascriptParser
from src.utils.parser.python_parser import PythonParser
from src.utils.parser.cpp_parser import CppParser
from src.utils.parser.c_sharp_parser import CsharpParser


def extract_raw_code(raw_code, language, language_path='languages/my-languages.so') -> List[Dict[str, Any]]:
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
    
    # print("root node", root.children)
 
    # for child in root.children:
    #     # print(child.type, child.text)
    #     if child.type == 'module':
    #         for i in child.children:
    #         # print(child.children)
    #             print(i.type, i.text, '\n\n')
    #     else:
    #         print(child.type, child.text, '\n')
        
    
    if language == 'python':
        function_list = PythonParser.get_function_definitions(root)
        return PythonParser.process_functions(function_list, raw_code)

    elif language == 'java':
        return JavaParser.get_definition(tree, raw_code)
    
    elif language == 'javascript':
        return JavascriptParser.get_definition(tree, raw_code)
    
    elif language == 'ruby':
        return RubyParser.get_definition(tree, raw_code)

    elif language == 'go':
        return GoParser.get_definition(tree, raw_code)
    
    elif language == 'php':
        return PhpParser.get_definition(tree, raw_code)
