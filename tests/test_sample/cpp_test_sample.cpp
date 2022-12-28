// Derived class
class Car: public Vehicle, private B {
  public:
    string model = "Mustang";
};

// A static function
int sum2number (int a, int b) {
  return a + b;
}

// Base class
class Vehicle {
  public:
    string brand = "Ford";
    void honk() {
      cout << "Tuut, tuut! \n" ;
    }
};

int main() {
  Car myCar;
  myCar.honk();
  cout << myCar.brand + " " + myCar.model;
  return 0;
}

