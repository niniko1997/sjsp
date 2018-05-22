import argparse
import os
import random
import numpy
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.LocalEngine as LE


# parse input
parser = argparse.ArgumentParser()
parser.add_argument('filename', type=str)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--num_chains', default=25, type=int)
parser.add_argument('--num_transitions', default=200, type=int)
args = parser.parse_args()

#
filename = args.filename
inf_seed = args.inf_seed
gen_seed = args.gen_seed
num_chains = args.num_chains
num_transitions = args.num_transitions

#
rng = random.Random(gen_seed)
get_next_seed = lambda: rng.randint(1, 2**31 - 1)

#
pkl_filename = 'dha_example_num_transitions_%s.pkl.gz' % num_transitions

def determine_Q(M_c, query_names, num_rows, impute_row=None):
    name_to_idx = M_c['name_to_idx']
    query_col_indices = [name_to_idx[colname] for colname in query_names]
    row_idx = num_rows + 1 if impute_row is None else impute_row
    Q = [(row_idx, col_idx) for col_idx in query_col_indices]
    return Q

def determine_unobserved_Y(num_rows, M_c, condition_tuples):
    name_to_idx = M_c['name_to_idx']
    row_idx = num_rows + 1
    Y = []
    for col_name, col_value in condition_tuples:
        col_idx = name_to_idx[col_name]
        col_code = du.convert_value_to_code(M_c, col_idx, col_value)
        y = (row_idx, col_idx, col_code)
        Y.append(y)
    return Y

# set everything up
T, M_r, M_c = du.read_model_data_from_csv(filename, gen_seed=gen_seed)
num_rows = len(T)
num_cols = len(T[0])
col_names = numpy.array([M_c['idx_to_name'][str(col_idx)] for col_idx in range(num_cols)])

# initialze and transition chains
engine = LE.LocalEngine(inf_seed)
X_L_list, X_D_list = engine.initialize(M_c, M_r, T, get_next_seed(), initialization='from_the_prior', n_chains=num_chains)
X_L_list, X_D_list = engine.analyze(M_c, T, X_L_list, X_D_list, get_next_seed(), n_steps=num_transitions)

# save the progress
to_pickle = dict(X_L_list=X_L_list, X_D_list=X_D_list)
fu.pickle(to_pickle, pkl_filename)

# to_pickle = fu.unpickle(pkl_filename)
# X_L_list = to_pickle['X_L_list']
# X_D_list = to_pickle['X_D_list']

engine = LE.LocalEngine(inf_seed)
# can we recreate a row given some of its values?
query_cols = [2, 6, 9]
query_names = col_names[query_cols]
Q = determine_Q(M_c, query_names, num_rows)
#
condition_cols = [3, 4, 10]
condition_names = col_names[condition_cols]
samples_list = []
for actual_row_idx in [1, 10, 100]:
    actual_row_values = T[actual_row_idx]
    condition_values = [actual_row_values[condition_col] for condition_col in condition_cols]
    condition_tuples = zip(condition_names, condition_values)
    Y = determine_unobserved_Y(num_rows, M_c, condition_tuples)
    samples = engine.simple_predictive_sample(M_c, X_L_list, X_D_list, Y, Q, 10)
    samples_list.append(samples)

round_1 = lambda value: round(value, 2)
# impute some values (as if they were missing)
for impute_row in [10, 20, 30, 40, 50, 60, 70, 80]:
    impute_cols = [31, 32, 52, 60, 62]
    #
    actual_values = [T[impute_row][impute_col] for impute_col in impute_cols]
    # conditions are immaterial
    Y = []
    imputed_list = []
    for impute_col in impute_cols:
        impute_names = [col_names[impute_col]]
        Q = determine_Q(M_c, impute_names, num_rows, impute_row=impute_row)
        #
        imputed = engine.impute(M_c, X_L_list, X_D_list, Y, Q, get_next_seed(), 1000)
        imputed_list.append(imputed)
    print
    print actual_values
    print map(round_1, imputed_list)
