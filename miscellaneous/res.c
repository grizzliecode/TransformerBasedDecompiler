#include <stdio.h>

void print_welcome() {
    puts("Welcome!");
}

int square(int x) {
    return x * x;
}

#include <stdio.h> // Required for printf

// External function declarations (assuming these functions are defined elsewhere)
void print_welcome();
int square(int x);

int main() {
    // The call to __main is typically for C runtime initialization
    // and is not explicitly written in C source code.

    int number = 5; // Corresponds to DWORD PTR -4[rbp]

    print_welcome();

    int squared_value = square(number); // Corresponds to DWORD PTR -8[rbp]

    // The format string ".LC1" is inferred from the arguments passed to __mingw_printf.
    // The arguments are 'number' (5) and 'squared_value' (25).
    // A plausible format string would be "The number is %d and its square is %d\n".
    printf("The number is %d and its square is %d\n", number, squared_value);

    return 0;
}