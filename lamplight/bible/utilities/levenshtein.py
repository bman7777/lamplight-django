def distance(str1, str2):
    """
    Calculate the Levenshtein distance between two strings.

    The Levenshtein distance is a metric for measuring the difference between two strings.
    It represents the minimum number of single-character edits (insertions, deletions, or
    substitutions) required to change one string into the other.

    Args:
        str1 (str): First string
        str2 (str): Second string

    Returns:
        int: The Levenshtein distance between the two strings
    """
    # Create a matrix of size (len(str1)+1) x (len(str2)+1)
    rows = len(str1) + 1
    cols = len(str2) + 1

    # Initialize the matrix with default values
    matrix = [[0 for _ in range(cols)] for _ in range(rows)]

    # Initialize the first row and column with incremental values
    for i in range(rows):
        matrix[i][0] = i

    for j in range(cols):
        matrix[0][j] = j

    # Fill in the rest of the matrix
    for i in range(1, rows):
        for j in range(1, cols):
            if str1[i - 1] == str2[j - 1]:
                # Characters match, no additional cost
                cost = 0
            else:
                # Characters don't match, add substitution cost
                cost = 1

            # Calculate the minimum edit distance
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,  # Deletion
                matrix[i][j - 1] + 1,  # Insertion
                matrix[i - 1][j - 1] + cost,  # Substitution
            )

    # The bottom-right cell contains the final distance
    return matrix[rows - 1][cols - 1]
