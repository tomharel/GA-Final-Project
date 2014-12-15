##########################
######## Imports #########
##########################
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import sys
import timeit
import MySQLdb as mdb

from operator import itemgetter
from numba import autojit, double, int_


##########################
# Command Line Arguments #
##########################

# Action
try:
	if sys.argv[1]:
		action = sys.argv[1]

except:
	action = None

# File name
try:
	if sys.argv[2]:
		filename = sys.argv[2]
except:
	filename = 'dataset.csv'

# Number of Features
try:
	if sys.argv[3] > 0:
		num_of_features = int(sys.argv[3])
except:
	num_of_features = 100

# Number of Iterations	
try:
	if sys.argv[4] > 0:
		num_of_iterations = int(sys.argv[4])
except:
	num_of_iterations = 50

# Matrix Factorization Model	
try:
	if sys.argv[5] == 'SGD':
		model = 'SGD'
	elif sys.argv[5] == 'ALS':
		model = 'ALS'

except:
	model = 'ALS'

# Drop Unpopular Items?
try:
	if sys.argv[6] == 'N': 
		keep_all = True
	else:
		keep_all = False
except:
	keep_all = True





##########################
####### Functions ########
##########################

def print_stamp(text):
	# Print with timestamp for use throughout the code.
	print "{0} => {1}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text)
	return None


def train_model(model=model):
	
	# Model
	if model == 'ALS':
		print_stamp("Running ALS Matrix Factorization Model")
		weighted_errors, nP, nQ = ALS(R, P, Q, W, num_of_iterations, num_of_features)
	elif model == 'SGD':
		print_stamp("Running SGD Matrix Factorization Model")
		weighted_errors, nP, nQ, steps = SGD(R, P, Q, W, num_of_features, num_of_iterations)
		model = 'SGD'
	else:
		print_stamp("Something went really wrong...")
	
	# Report Errors for each Iteration
	total_error = get_error(R, nP, nQ, W)
	print_stamp("Total Error: " + str(total_error))
	
	# Plot Errors
	plt.plot(weighted_errors);
	plt.xlabel('Iteration Number');
	plt.ylabel('Mean Squared Error');
	plt.title('Mean Squared Error over Iterations')
	fig_filename = 'fig_' + str(model) + '_errors.png'
	plt.savefig(fig_filename, dpi=200, format='png')
	
	# Return Factorized Matrices
	return nP, nQ
	

def gen_recommendations(user_id, P, Q, R, scalar=5, randomization_low=1.0, randomization_high=1.25, num_of_recs_to_return=500): 	
	# User and Item Lists
	user_list = rp.index.tolist()
	all_items = rp.columns.tolist()
	
	# Check if user_id in User List
	if (user_id in user_list):
		Rhat = np.dot(P, Q.T)
		Rhat -= np.min(Rhat)
		Rhat *= float(scalar) / np.max(Rhat)
		
		upos = user_list.index(user_id)
		
		# Remove ordered items and add randomization.
		random_components = np.random.uniform(low=randomization_low, high=randomization_high, size=Rhat.shape)
		Rhat = (Rhat * random_components) - (scalar * W)
		
		# Get ratings for items
		rating_arr = [list(x) for x in zip(all_items, Rhat[upos])]
		rating_arr.sort(key=itemgetter(1), reverse=True)
		
	else:
		Rhat = np.dot(P.mean(axis=0), Q.T)
		Rhat -= np.min(Rhat)
		Rhat *= float(scalar) / np.max(Rhat)
		
		# Remove ordered items and add randomization.
		random_components = np.random.uniform(low=randomization_low, high=randomization_high, size=Rhat.shape)
		Rhat = (Rhat * random_components)
		
		# Get ratings for items
		rating_arr = [list(x) for x in zip(all_items, Rhat)]
		rating_arr.sort(key=itemgetter(1), reverse=True)
		
	recommendations = rating_arr[0:num_of_recs_to_return] # Top num_of_recs_to_return items for this user

	return recommendations


def db_insert(arr):
	con = mdb.connect('grt-data.grtgroup.de', 'gaeat24', 'YKuDeZRC', 'gaeat24_recsys');
	cursor = con.cursor()
	sql = "INSERT INTO recommendations (client_id, item_id, rating) VALUES (%s, %s, %s)"
	cursor.executemany(sql, arr)
	con.commit()
	cursor.close()
	return None


def update_db(randomization=True, include_generic_user=True):
	user_list = rp.index.tolist()
	
	# Generic User
	if include_generic_user:
		user_list.append(0) # user_id 0 will be a generic user.

	# Randomization
	randomization_low = 1.0
	if randomization:
		randomization_high = 1.25
	else:
		randomization_high = 1.0

	user_count = 0
	row_count = 0
	for u in user_list:
		rows = []

		user_recs = gen_recommendations(user_id=u, P=nP, Q=nQ, R=R, randomization_low=randomization_low,\
							randomization_high=randomization_high,num_of_recs_to_return=100)

		for i, r in user_recs:
			rows.append((u, i, r))
			row_count += 1

		# Insert to DB
		db_insert(rows)
		user_count +=1

	return user_count, row_count


@autojit
def get_error(R, P, Q, W):
	# Weighted Error
    return np.sum((W * (R - np.dot(P, Q.T)))**2)





##########################
####  Training Models ####
##########################

# SGD
@autojit(locals={'step': int_, 'err': double}) 
def SGD(R, P, Q, W, K=num_of_features, num_of_iterations=num_of_iterations):
    steps = num_of_iterations * 10
    weighted_errors = []
    alpha = 0.002
    beta = 0.01
    QT = Q.T
    n, m = R.shape
    step = 0
    err = 0.0
    for step in xrange(steps):
        for i in xrange(n):
            for j in xrange(m):
                if R[i,j] > 0:
                    temp = double(np.dot(P[i,:],QT[:,j]))
                    eij = R[i,j] - temp
                    for k in xrange(K):
                        P[i,k] += 2 * alpha * (eij * QT[k,j] - beta * P[i,k])
                        QT[k,j] += 2 * alpha * (eij * P[i,k] - beta * QT[k,j])
        
		err = get_error(R, P, Q, W)
	    weighted_errors.append(err)
        print_stamp("Step " + str(step) + " done.")
        if err < 0.5:
            break

    return weighted_errors, P, QT.T, step + 1


# ALS
@autojit
def ALS(R, P, Q, W, n_iterations=num_of_iterations, n_factors=num_of_features):
	
	weighted_errors = []
	lambda_ = 0.1
	for ii in range(n_iterations):

		for u, Wu in enumerate(W):
			P[u] = np.linalg.solve(np.dot(Q.T, np.dot(np.diag(Wu), Q)) + lambda_ * np.eye(n_factors),
								   np.dot(Q.T, np.dot(np.diag(Wu), R[u].T))).T
		for i, Wi in enumerate(W.T):
			Q[i] = np.linalg.solve(np.dot(P.T, np.dot(np.diag(Wi), P)) + lambda_ * np.eye(n_factors),
								   np.dot(P.T, np.dot(np.diag(Wi), R[:, i])))
		
		err = get_error(R, P, Q, W)
		weighted_errors.append(err)
		print_stamp(str(ii) + 'th iteration is completed with error = ' + str(err))
	
	return weighted_errors, P, Q	
	




##########################
########  Script #########
##########################



print_stamp("Using {0} with {1} features and {2} iterations.".format(filename, num_of_features, num_of_iterations))	

# Import Dataset
print_stamp("Importing Dataset...")	
df = pd.read_csv(filename).dropna()
df.insert(len(df.columns), 'rating', 1)
#df.drop(['order_id','order_date_ca'], axis=1, inplace=True)
df.drop_duplicates(inplace=True)
print_stamp("Dataset Imported Successfully.")

if (keep_all == False):
	# Drop items with less than 2 purchases
	items_count = df.items_ordered.value_counts()
	keep_items = [x for x in items_count[items_count > 1].index]

	z = []
	for i in df.items_ordered:
		if i in keep_items:
			z.append(True)
		else:
			z.append(False)

	df2 = df[z]
	rp = df2.pivot_table(cols=['items_ordered'],rows=['client_id'],values='rating')
else:
	rp = df.pivot_table(cols=['items_ordered'],rows=['client_id'],values='rating')

# Rating Matrix (R)
rp = rp.fillna(0)
R = rp.values
print_stamp("Ratings Matrix prepared successfully.")

# W, P and Q Matrices
print_stamp("Preparing Weighting, Item-Feature and Client-Feature initial matrices...")

# W Matrix
W = R>=1
W[W == False] = 0
W[W == True] = 1
W = W.astype(np.int8, copy=False)

# Parameters
K = num_of_features
N, M = R.shape
print_stamp("The rating matrix is composed of " + str(N) + " clients and " + str(M) + " items.")

# Starting Random Matrices (P,Q)
P = np.random.rand(N, K)
Q = np.random.rand(M, K)
print_stamp("Initial P & Q Matrices prepared successfully.")

# Start Model Training
tstart = timeit.default_timer()
nP, nQ = train_model()
tstop = timeit.default_timer()
runtime = (tstop - tstart) / 60
print_stamp("Model Training Completed. Total Time = " + str(runtime) + " minutes.")


# Update Database
if action == 'update_db':
	user_cnt, row_cnt = update_db()
	print_stamp("Updated Recommedations for {0} users, and a total of {1} rows.".format(user_cnt, row_cnt))