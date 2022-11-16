trait Quack {
    fn quack(&self);
}

struct Duck ();

fn long_string(x: &str) -> &str {
    if x.len() > 10 {
        "too long"
    } else {
        x
    }

}

impl Quack for Duck {
    fn quack(&self) {
        println!("quack!");
    }
}

mod my_mod {
    // Items in modules default to private visibility.
    fn private_function() {
        println!("called `my_mod::private_function()`");
    }
}

fn quack_everyone <I> (iter: I)
where I: Iterator<Item=Box<Quack>> {
    for d in iter {
        d.quack();
    }
}

let ducks: Vec<Box<Quack>> = vec![Box::new(duck1),Box::new(duck2),Box::new(parrot),Box::new(int)];
