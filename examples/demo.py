"""One-minute demo: a function that works on normal lists but not on edge cases."""

from edgecase_provocateur import provoke


@provoke
def find_max_difference(numbers):
    largest = numbers[0]
    smallest = numbers[0]
    for num in numbers:
        if num > largest:
            largest = num
        if num < smallest:
            smallest = num
    return largest - smallest


print("Result:", find_max_difference([1, 2, 3]))