# Tree-sitter function/class type

## C/C++
Node type - Sample

- with C
```c
// function_definition
void reverseSentence(int random_seed) {
    char c;
    scanf("%c", &c);
    if (c != '\n') {
        reverseSentence();
        printf("%c", c);
    }
}
```

- with C++
```c++
// function_definition
double plusFuncDouble(double x, double y) {
  return x + y;
}

// function_definition
int main() {
  int myNum1 = plusFuncInt(8, 5);
  double myNum2 = plusFuncDouble(4.3, 6.26);
  cout << "Int: " << myNum1 << "\n";
  cout << "Double: " << myNum2;
  return 0;
}

// class_specifier
class Animal {
  public:
    // function_definition
    void animalSound() {
      cout << "The animal makes a sound \n";
    }
};

// class_specifier
class Pig : public Animal {
  public:
    // function_definition
    void animalSound() {
      cout << "The pig says: wee wee \n";
    }
};
```

## C#

```c#
// local_function_statement
private static string GetText(string path, string filename)
{
    // local_declaration_statement
    var reader = File.OpenText($"{AppendPathSeparator(path)}{filename}");
    var text = reader.ReadToEnd();
    return text;

    // local_function_statement
    string AppendPathSeparator(string filepath)
    {
        return filepath.EndsWith(@"\") ? filepath : filepath + @"\";
    }
}

using System;

// class_declaration
public class Dog : Animal {
 
    String name;
    String breed;
    int age;
    String color;
 
    // constructor_declaration
    public Dog(String name, String breed,
                  int age, String color)
    {
        this.name = name;
        this.breed = breed;
        this.age = age;
        this.color = color;
    }
    
    // method_declaration
    static void Main(string[] args)
    {
      Car myObj = new Car();
      Console.WriteLine(myObj.color);
    }
}
```

## Java

```Java
// class_declaration
public class SaveFileController extends SudoUser implements FileController {
    // field_declaration
    private ArrayList<User> allUsers;
    private String saveFile = "test_save_file4.sav";

    // constructor_declaration
    public SaveFileController(){
        this.allUsers = new ArrayList<User>();
    }

    // method_declaration
    public HabitList getHabitList(Context context, int userIndex){
        loadFromFile(context);
        return this.allUsers.get(userIndex).getHabitList();
    }
}
```

## Python
```python
# class_definition
class Person:
    # function_definition
    def __init__(self, name, age):
        self.name = name
        self.age = age

    # function_definition
    def say_my_name(self):
        print(self.name)

# function_definition
def create_a_person(name, age):
    new_person = Person(name, age)
```

## JavaScript
```JavaScript
// function_declaration
export function loadSongs() {
    return {
        type: LOAD_SONGS,
    };
}

// class_declaration
class Model extends Car {
    // method_definition
    constructor(brand, mod) {
        super(brand);
        this.model = mod;
    }

    // method_definition
    show() {
        return this.present() + ', it is a ' + this.model;
    }
}
```

## PHP

```PHP
// function_definition
function familyName($fname) {
  echo "$fname Refsnes.<br>";
}

// class_declaration
final class Driver extends AbstractSQLServerDriver
{
    // method_declaration
    public function connect(array $params)
    {
        $driverOptions = $dsnOptions = [];
        if (isset($params['driverOptions'])) {
            foreach ($params['driverOptions'] as $option => $value) {
                if (is_int($option)) {
                    $driverOptions[$option] = $value;
                } else {
                        $dsnOptions[$option] = $value;
                }
            }
        }
    }
}
```

## GO

```GO
// function_declaration
func add(x int, y int) int {
	return x + y
}

// function_declaration
func main() {
	fmt.Println(add(42, 13))
}

// method_declaration
func (e TypeError) Error() string {
		msg := e.Type1.String()
		if e.Type2 != nil {
			msg += " and " + e.Type2.String()
	}
	msg += " " + e.Extra
	return msg
}

```

## Ruby

```Ruby
# class
class Customer
   @@no_of_customers = 0
   
   # method
   def initialize(id, name, addr)
      @cust_id = id
      @cust_name = name
      @cust_addr = addr
   end
end

# method
def test(a1 = "Ruby", a2 = "Perl")
   puts "The programming language is #{a1}"
   puts "The programming language is #{a2}"
end

# module
module RedditKit
    # class
    class Client < API
        # method
        def search(query, options = {})
            path = "%s/search.json" % ('r/' + options[:subreddit] if options[:subreddit])
            parameters = { :q => query,
                            :restrict_sr => options[:restrict_to_subreddit],
                            :limit       => options[:limit],
                            :count       => options[:count],
                            :sort        => options[:sort],
                            :before      => options[:before],
                            :after       => options[:after],
                            :syntax      => options[:syntax],
                            :t           => options[:time]
            }

            objects_from_response(:get, path, parameters)
        end
    end
end
    
```

## Rust

```Rust
// trait_item
trait Quack {
    // function_signature_item <- This is function declaration
    fn quack(&self);
}

// struct_item
struct Duck ();

// function_item
fn long_string(x: &str) -> &str {
    if x.len() > 10 {
        "too long"
    } else {
        x
    }

}

// impl_item
impl Quack for Duck {
    // function_item
    fn quack(&self) {
        println!("quack!");
    }
}

// mod_item
mod my_mod {
    // function_item
    fn private_function() {
        println!("called `my_mod::private_function()`");
    }
}

// function_item
fn quack_everyone <I> (iter: I)
where I: Iterator<Item=Box<Quack>> {
    for d in iter {
        d.quack();
    }
}
```