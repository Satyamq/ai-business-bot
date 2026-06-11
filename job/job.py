import statistics as stats

numbers = list(range(10))

for i in numbers:
    print(i)
    print(i**2)

print(max(numbers))
print(min(numbers))
print(sum(numbers))
print(len(numbers))
print(stats.mean(numbers))
print(stats.median(numbers))
print(stats.mode(numbers))
