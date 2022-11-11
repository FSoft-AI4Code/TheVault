'''test for C++ parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import CppParser
from src.utils.utils import parse_code

ROOT_PATH = str(Path(__file__).parents[1])

class Test_CppParser_with_C(unittest.TestCase):
    def setUp(self) -> None:
        with open('tests/test_sample/c_test_sample.c', 'r') as file:
            self.code_sample = file.read()
            
        tree = parse_code(self.code_sample, 'c')
        self.root_node = tree.root_node

        return super().setUp()

    def test_get_function_list(self):
        root = self.root_node
        
        function_list = CppParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 2)

    def test_get_function_metadata(self):
        root = self.root_node
        
        function = CppParser.get_function_list(root)[0]
        metadata = CppParser.get_function_metadata(function, self.code_sample)
        

        self.assertEqual(metadata['parameters'], {'random_seed': 'int'})
        self.assertEqual(metadata['identifier'], 'reverseSentence')
        self.assertEqual(metadata['type'], 'void')
        
    def test_get_class_list(self):
        pass
    
    def test_get_class_metadata(self):
        pass

    def test_get_docstring(self):
        code_sample = """
        /**
        * A brief description. A more elaborate class description
        * @param random_seed somearg.
        * @see Test()
        * @return The test results
        */
        void reverseSentence(int random_seed) {
            char c;
            scanf("%c", &c);
            if (c != '\n') {
                reverseSentence();
                printf("%c", c);
            }
        }
        """
        tree = parse_code(code_sample, 'c')
        root = tree.root_node
        
        fn= CppParser.get_function_list(root)[0]

        docs = CppParser.get_docstring(fn, code_sample)
        
        self.assertEqual(docs, '\nA brief description. A more elaborate class description\n@param random_seed somearg.\n@see Test()\n@return The test results\n')
        

    def test_extract_docstring(self):
        pass


if __name__ == '__main__':
    unittest.main()
