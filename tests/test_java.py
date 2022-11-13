'''test for Java parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import JavaParser
from src.utils import parse_code

ROOT_PATH = str(Path(__file__).parents[1])

class Test_JavaParser(unittest.TestCase):
    def setUp(self) -> None:        
        with open('tests/test_sample/java_test_sample.java', 'r') as file:
            self.code_sample = file.read()
            
        tree = parse_code(self.code_sample, 'java')
        self.root_node = tree.root_node

        return super().setUp()

    def test_get_function_list(self):
        root = self.root_node
        
        function_list = JavaParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 2)

    def test_get_class_list(self):
        root = self.root_node
        
        class_list = JavaParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 1)

    def test_get_docstring(self):
        code_sample = """
        public class SaveFileController {
            /**
            * Adds new user and saves to file.
            *
            * @param context instance of Context
            * @param user instance of User
            * @see User
            */
            public void addNewUser(Context context, User user){
                    loadFromFile(context);
                this.allUsers.add(user);
                saveToFile(context);
            }
        }
        """
        tree = parse_code(code_sample, 'java')
        root = tree.root_node
        
        fn = list(JavaParser.get_function_list(root))[0]

        docs = JavaParser.get_docstring(fn, code_sample)
        
        self.assertEqual(docs, '\nAdds new user and saves to file.\n\n@param context instance of Context\n@param user instance of User\n@see User\n')
        

    def test_get_function_metadata(self):
        root = self.root_node
        
        function = list(JavaParser.get_function_list(root))[0]
        metadata = JavaParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['parameters'], {'context': 'Context', 'userIndex': 'int'})
        self.assertEqual(metadata['identifier'], 'getHabitList')
        self.assertEqual(metadata['type'], 'HabitList')

    def test_get_class_metadata(self):
        root = self.root_node
        
        classes = list(JavaParser.get_class_list(root))[0]
        metadata = JavaParser.get_class_metadata(classes, self.code_sample)

        self.assertEqual(metadata['parameters'], ['SudoUser', 'FileController'])
        self.assertEqual(metadata['identifier'], 'SaveFileController')

    def test_extract_docstring(self):
        pass
        

if __name__ == '__main__':
    unittest.main()
