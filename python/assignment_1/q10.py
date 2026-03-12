t=(1,2,[3,4],5)

t[2][0]=10

print(t)

# Explanation
# The tuple itself is immutable.
# But the list inside the tuple is mutable, so its elements can be changed without converting the tuple to a list.