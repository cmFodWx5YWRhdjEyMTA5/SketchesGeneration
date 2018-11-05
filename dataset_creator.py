import random

DATASET_SIZE = 72219
TEST_SET_SIZE = 7222

TEST_SHUFFLE_PATH = "./data/test_shuffle.lst"
INDEX_LINE_MAP_PATH = "./data/index_map.lst"

if __name__ == '__main__':
    test_indexes = random.sample(range(DATASET_SIZE), TEST_SET_SIZE)
    index_map = {}
    with open(INDEX_LINE_MAP_PATH, "r") as f:
        for line in f:
            index, line_no = [int(x) for x in line.split()]
            index_map[index] = line_no

    with open(TEST_SHUFFLE_PATH, 'w') as f:
        for index in test_indexes:
            # f.write(str(index) + ".png " + str(index_map[index]) + "\n")
            f.write(str(index) + ".png " + str(index) + "\n")