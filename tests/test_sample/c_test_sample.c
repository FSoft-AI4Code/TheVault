#include <stdio.h>
void reverseSentence();
int main() {
    printf("Enter a sentence: ");
    reverseSentence();
    return 0;
}

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