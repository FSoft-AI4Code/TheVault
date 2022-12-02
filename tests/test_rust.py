'''test for Ruby parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import RustParser
from src.utils import parse_code

ROOT_PATH = str(Path(__file__).parents[1])

class Test_RustParser(unittest.TestCase):
    def setUp(self) -> None:
        with open('tests/test_sample/rust_test_sample.rs', 'r') as file:
            self.code_sample = file.read()
            
        tree = parse_code(self.code_sample, 'rust')
        self.root_node = tree.root_node

        return super().setUp()

    def test_get_function_list(self):
        root = self.root_node
        
        function_list = RustParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 4)

    def test_get_class_list(self):
        root = self.root_node
        
        class_list = RustParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 2)

    def test_get_docstring(self):
        code_sample = """
        // Comment something
        mod my_mod {
            /// Creates a new rendering surface.
            ///
            /// # Arguments
            ///
            /// Initialization of surfaces happens through the types provided by
            /// [`drm-rs`](drm).
            ///
            /// - [`crtcs`](drm::control::crtc) represent scanout engines of the device pointing to one framebuffer. \\
            ///     Their responsibility is to read the data of the framebuffer and export it into an "Encoder". \\
            ///     The number of crtc's represent the number of independent output devices the hardware may handle.
            fn private_function() {
                println!("called `my_mod::private_function()`");
            }

            /**  - Outer block doc (exactly) 2 asterisks */
            pub fn function() {
                println!("called `my_mod::function()`");
            }

            // Items can access other items in the same module,
            // even when private.
            pub fn indirect_access() {
                print!("called `my_mod::indirect_access()`, that\n> ");
                private_function();
            }
        }
        """

        tree = parse_code(code_sample, 'rust')
        root = tree.root_node
        
        fn1 = RustParser.get_function_list(root)[0]
        fn2 = RustParser.get_function_list(root)[1]
        clas = RustParser.get_class_list(root)[0]
        
        docs1 = RustParser.get_docstring(fn1, code_sample)
        docs2 = RustParser.get_docstring(fn2, code_sample)
        docs3 = RustParser.get_docstring(clas, code_sample)
        
        self.assertEqual(docs1, '/// Creates a new rendering surface.\n///\n/// # Arguments\n///\n/// Initialization of surfaces happens through the types provided by\n/// [`drm-rs`](drm).\n///\n/// - [`crtcs`](drm::control::crtc) represent scanout engines of the device pointing to one framebuffer. \\\n///     Their responsibility is to read the data of the framebuffer and export it into an "Encoder". \\\n///     The number of crtc\'s represent the number of independent output devices the hardware may handle.')
        self.assertEqual(docs2, '/**  - Outer block doc (exactly) 2 asterisks */')
        self.assertEqual(docs3, '// Comment something')

    def test_get_function_metadata(self):
        root = self.root_node
        
        function = RustParser.get_function_list(root)[0]
        metadata = RustParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['identifier'], 'long_string')
        self.assertEqual(metadata['parameters'], {'x': '&str'})

    def test_get_class_metadata(self):
        root = self.root_node
        
        classes = RustParser.get_class_list(root)[0]
        metadata = RustParser.get_class_metadata(classes, self.code_sample)
        
        self.assertEqual(metadata['identifier'], 'Quack')
        self.assertEqual(metadata['parameters'], ['Duck'])

    def test_extract_docstring(self):
        pass
        

if __name__ == '__main__':
    unittest.main()
