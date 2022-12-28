'''test for C++ parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.codetext.utils.parser import GoParser
from src.codetext.utils.utils import parse_code

class Test_GoParser(unittest.TestCase):
    def setUp(self) -> None:
        with open('tests/test_sample/go_test_sample.go', 'r') as file:
            self.code_sample = file.read()
            
        tree = parse_code(self.code_sample, 'go')
        self.root_node = tree.root_node
        return super().setUp()

    def test_get_function_list(self):
        root = self.root_node
        
        function_list = GoParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 1)

    def test_get_function_metadata(self):
        root = self.root_node
        
        function = GoParser.get_function_list(root)[0]
        metadata = GoParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['parameters'], {'e': 'TypeError'})
        self.assertEqual(metadata['identifier'], 'Error')
        self.assertEqual(metadata['type'], 'string')

    def test_get_docstring(self):
        code_sample = """
        type TypeError struct {
            Type1, Type2 reflect.Type
            Extra        string
        }
        // Something must not include as docstring
        
        // The path package should only be used for paths separated by forward
        // slashes, such as the paths in URLs. This package does not deal with
        // Windows paths with drive letters or backslashes; to manipulate
        // operating system paths, use the [path/filepath] package.
        func (e TypeError) Error() string {
                msg := e.Type1.String()
                if e.Type2 != nil {
                    msg += " and " + e.Type2.String()
            }
            msg += " " + e.Extra
            return msg
        }
        """
        tree = parse_code(code_sample, 'go')
        root = tree.root_node
        
        fn = GoParser.get_function_list(root)[0]

        docs = GoParser.get_docstring(fn, code_sample)
        self.assertEqual(docs, '// The path package should only be used for paths separated by forward\n// slashes, such as the paths in URLs. This package does not deal with\n// Windows paths with drive letters or backslashes; to manipulate\n// operating system paths, use the [path/filepath] package.')
        

    def test_extract_docstring(self):
        pass


if __name__ == '__main__':
    unittest.main()
