import sys
from copy import copy
from random import shuffle
from multiprocessing.pool import Pool

from matrix import Matrix
from stats import mean, mode, regression_score


MINIMUM_GAIN = 0.1


class TreeNode():
    """A class to represent a Node in the Regression Tree"""
    def __init__(self):
        self.left = self.right = None
        self.column = None
        self.value = None
        self.classification = None

    def train(self, matrix, columns):
        """Train the regression tree on a matrix of data using features
        in columns"""
        assert(len(matrix) > 0)
        if len(columns) <= 0:
            self.classification = mode(matrix.column(-1))
            return
        # Decide which column to split on
        min_error = 1000000000
        min_index = columns[0]
        error = min_error
        for col_index in columns:
            error = regression_score(matrix, col_index)
            #print(col_index, error)
            if error < min_error:
                min_index = col_index
                min_error = error
        # Split on lowest-error column
        value = mean(matrix.column(min_index))
        left, right = matrix.split(min_index, value)
        if len(left) <= 0 or len(right) <= 0:
            self.classification = mode(matrix.column(-1))
            return
        left_error = regression_score(left, min_index)
        right_error = regression_score(right, min_index)
        gain = error-(left_error+right_error)
        # Stop recursing if below threshhold
        if gain < MINIMUM_GAIN:
            self.classification = mode(matrix.column(-1))
            return
        #print(gain, min_index, min_error)
        # Set self values
        self.column = min_index
        self.value = value
        # Create new child nodes
        new_columns = copy(columns)
        new_columns.remove(min_index)
        self.left = TreeNode()
        self.left.train(left, new_columns)
        self.right = TreeNode()
        self.right.train(right, new_columns)

    def classify(self, row):
        """Classify a vector of data using this regression tree"""
        if self.classification is not None:
            return self.classification
        if row[self.column] < self.value:
            return self.left.classify(row)
        else:
            return self.right.classify(row)


class Forest():
    """A forest contains a collection of trees with partial
    feature sets.  These trees vote on a classification
    to determine the final class."""
    def __init__(self, n_trees=100, n_features=10):
        self.n_trees = n_trees
        self.n_features = n_features
        self.trees = []
        for i in range(n_trees):
            tree = TreeNode()
            self.trees.append(tree)

    def train(self, matrix):
        all_columns = list(range(matrix.columns()-1))
        for tree in self.trees:
            shuffle(all_columns)
            columns = all_columns[0:self.n_features]
            tree.train(matrix, columns)

    def classify(self, row):
        votes = []
        for tree in self.trees:
            vote = tree.classify(row)
            votes.append(vote)
        return mode(votes)


def parallel_train(state):
    """function to train trees in another process
    state is (matrix, columns) because we cannot use
    a starmap in Python < 3.3 """
    matrix, columns = state
    #m = Matrix()
    #m.load(matrix_filename)
    m = matrix
    root = TreeNode()
    root.train(m, columns)
    return root


def column_set(columns, number):
    """returns a random subset of columns of size number.
    Note: modifies columns"""
    shuffle(columns)
    return columns[:number]


class ParallelForest(Forest):
    """A parallel implementation of Random Forest.
    It starts a Pool of processes, then uses map to create a
    set of trees.  Classification is still done in serial:
    inherits Forest's classify method."""
    def __init__(self, n_trees=100, n_features=10, n_processes=2):
        self.n_trees = n_trees
        self.n_features = n_features
        self.pool = Pool(n_processes)
        self.trees = []

    def train(self, matrix):
        all_columns = list(range(matrix.columns()-1))
        star = [(matrix, column_set(all_columns, self.n_features)) for _ in range(self.n_trees)]
        self.trees = self.pool.map(parallel_train, star)


def evaluate(matrix, classifier):
    right = wrong = 0
    for i in range(len(matrix)):
        row_class = classifier.classify(matrix[i])
        expected_class = matrix[i][-1]
        if row_class == expected_class:
            right += 1
        else:
            wrong += 1
    return right, wrong


def main():
    if len(sys.argv) < 2:
        print('usage: python cart.py training_file')
        exit(1)
    # Load Matrices0
    train = Matrix()
    train.load(sys.argv[1])
    #test = Matrix()
    #test.load(sys.argv[2])
    # Train a single regression tree
    root = TreeNode()
    cols = list(range(train.columns()-1))
    root.train(train, cols)
    # Evaluate results against original training set
    right, wrong = evaluate(train, root)
    percent = right * 100.0 / len(train)
    print('training set recovered: %f%%' % percent)
    # Evaluate Random Forest Method
    forest = ParallelForest(1000, train.columns()-1, 16)
    forest.train(train)
    right, wrong = evaluate(train, forest)
    percent = right * 100.0 / len(train)
    print('training set recovered: %f%%' % percent)


if __name__ == '__main__':
    main()