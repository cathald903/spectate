def find_internal_nodes_num(tree):
    """
        Any number that appears in the tree is an internal node, therefore we just need to get the count of distinct numbers in the input
        As the root doesn't count we -1
    """
    if len(tree)>= 1:
        return len(set(tree))-1
    else:
        return 0

my_tree = [4, 4, 1, 5, -1, 4, 5]
print(find_internal_nodes_num(my_tree))