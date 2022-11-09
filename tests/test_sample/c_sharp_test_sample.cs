private static string GetText(string path, string filename)
{
    var reader = File.OpenText($"{AppendPathSeparator(path)}{filename}");
    var text = reader.ReadToEnd();
    return text;

    string AppendPathSeparator(string filepath)
    {
        return filepath.EndsWith(@"\") ? filepath : filepath + @"\";
    }
}

using System;
public class Dog : Animal {
 
    // Instance Variables
    String name;
    String breed;
    int age;
    String color;
 
    // Constructor Declaration of Class
    public Dog(String name, String breed,
                  int age, String color)
    {
        this.name = name;
        this.breed = breed;
        this.age = age;
        this.color = color;
    }
    
    // Docstring of this function
    static void Main(string[] args)
    {
      Car myObj = new Car();
      Console.WriteLine(myObj.color);
    }
  }