'''test for PHP parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import PhpParser
from src.utils import parse_code

ROOT_PATH = str(Path(__file__).parents[1])

class Test_PhpParser(unittest.TestCase):
    def setUp(self) -> None:
        with open('tests/test_sample/php_test_sample.php', 'r') as file:
            self.code_sample = file.read()
            
        tree = parse_code(self.code_sample, 'php')
        self.root_node = tree.root_node

        return super().setUp()

    def test_get_function_list(self):
        root = self.root_node
        
        function_list = PhpParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 3)

    def test_get_class_list(self):
        root = self.root_node
        
        class_list = PhpParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 1)

    def test_get_docstring(self):
        code_sample = """
        <?php
        /**
        * Get all image nodes.
        *
        * @param \DOMNode     $node       The \DOMDocument instance
        * @param boolean      $strict     If the document has to be valid
        *
        * @return \DOMNode
        */
        function getImageNodes(\DOMNode $node, $strict = true): \DOMNode
        {
            // ...
            return $node;
        }
        ?>
        """

        tree = parse_code(code_sample, 'php')
        root = tree.root_node
        
        fn = PhpParser.get_function_list(root)[0]

        docs = PhpParser.get_docstring(fn, code_sample)
        
        self.assertEqual(docs, '/**\n        * Get all image nodes.\n        *\n        * @param \\DOMNode     $node       The \\DOMDocument instance\n        * @param boolean      $strict     If the document has to be valid\n        *\n        * @return \\DOMNode\n        */')
        

    def test_get_function_metadata(self):
        root = self.root_node
        
        function = list(PhpParser.get_function_list(root))[1]
        metadata = PhpParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['parameters'], ['params', 'connectionOptions'])
        self.assertEqual(metadata['identifier'], 'constructDsn')
        self.assertEqual(metadata['type'], 'string')

    def test_get_class_metadata(self):
        root = self.root_node
        
        classes = list(PhpParser.get_class_list(root))[0]
        metadata = PhpParser.get_class_metadata(classes, self.code_sample)

        self.assertEqual(metadata['parameters'], ['AbstractSQLServerDriver'])
        self.assertEqual(metadata['identifier'], 'Driver')

    def test_extract_docstring(self):
        pass
        

if __name__ == '__main__':
    unittest.main()
