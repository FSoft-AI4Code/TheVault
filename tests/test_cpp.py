'''test for C++ parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import CppParser

ROOT_PATH = str(Path(__file__).parents[1])

class Test_CppParser(unittest.TestCase):
    def setUp(self) -> None:
        parser = Parser()
        language = Language(ROOT_PATH + "/tree-sitter/cpp.so", 'cpp')
        parser.set_language(language)
        
        with open('tests/test_sample/cpp_test_sample.cpp', 'r') as file:
            self.code_sample = file.read()
        
        self.parser = parser
        return super().setUp()

    def test_get_function_list(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        function_list = CppParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 3)
        
    def test_get_class_list(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        class_list = CppParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 2)

    def test_get_function_metadata(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        function = list(CppParser.get_function_list(root))[0]
        metadata = CppParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['parameters'], {'a': 'int', 'b': 'int'})
        self.assertEqual(metadata['identifier'], 'sum2number')
        self.assertEqual(metadata['type'], 'int')
    
    def test_get_class_metadata(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        classes = list(CppParser.get_class_list(root))[0]
        metadata = CppParser.get_class_metadata(classes, self.code_sample)

        self.assertEqual(metadata['argument_list'], ['Vehicle', 'B'])
        self.assertEqual(metadata['identifier'], 'Car')

    def test_get_docstring(self):
        pass

    def test_extract_docstring(self):
        pass


if __name__ == '__main__':
    unittest.main()
