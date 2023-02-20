# This file sets various parameters used in train_and_eval.py.


log_path = "result.csv"  #where to store the result
plot_result = False  #
BO = False #Whether to use Bayesian optimization to search for hyperparameters
earlystopping = True # whether  to use earlystopping
es_patience = 10
train_whole_dataset_again=True  #Whether to store the confidence of all data when training and predicting
test_model=False  #Whether to train a model or load a trained model
params_deep4_60=['deep42022-08-22_08-28-46params.pt','deep42022-08-22_13-33-59params.pt','deep42022-08-22_20-08-07params.pt','deep42022-08-23_02-52-32params.pt','deep42022-08-23_07-31-26params.pt']
params_deep4_600=['deep42022-08-23_12-11-41params.pt','deep42022-08-23_15-52-28params.pt','deep42022-08-23_16-51-15params.pt','deep42022-08-24_01-08-18params.pt','deep42022-08-24_05-00-21params.pt','deep42022-08-24_10-58-14params.pt','deep42022-08-24_11-04-58params.pt']
params_deep4_300=['deep42022-08-25_19-30-09params.pt','deep42022-08-26_01-36-44params.pt','deep42022-08-26_06-51-30params.pt','deep42022-08-26_12-31-27params.pt','deep42022-08-26_18-57-53params.pt','deep42022-08-26_20-46-02params.pt','deep42022-08-27_04-37-34params.pt']
params_deep4_180=['deep42022-08-27_10-45-50params.pt','deep42022-08-27_16-24-18params.pt','deep42022-08-27_20-36-19params.pt','deep42022-08-28_02-09-57params.pt','deep42022-08-28_06-06-26params.pt','deep42022-08-28_10-17-49params.pt']
params_tcn1_900=['tcn_12022-08-30_15-53-05params.pt','tcn_12022-08-30_22-48-56params.pt','tcn_12022-08-31_05-29-42params.pt','tcn_12022-08-31_10-36-47params.pt','tcn_12022-08-31_17-31-53params.pt']
params_tcn1_300=['tcn_12022-09-04_11-55-13params.pt','tcn_12022-09-04_22-29-55params.pt','tcn_12022-09-05_09-25-52params.pt','tcn_12022-09-05_20-26-47params.pt','tcn_12022-09-06_07-21-07params.pt']
params_tcn1_180=['tcn_12022-09-06_22-35-51params.pt','tcn_12022-09-07_13-45-03params.pt','tcn_12022-09-08_06-01-55params.pt','tcn_12022-09-08_16-48-06params.pt','tcn_12022-09-10_02-01-38params.pt','tcn_12022-09-10_13-57-31params.pt','tcn_12022-09-10_17-10-35params.pt']
params_tcn1_60=['tcn_12022-09-12_07-34-49params.pt','tcn_12022-09-15_14-31-46params.pt','tcn_12022-09-16_15-11-31params.pt','tcn_12022-09-18_18-09-03params.pt','tcn_12022-09-20_05-59-27params.pt']


# Set verbosity of outputs from MNE library.
# Options: DEBUG, INFO, WARNING, ERROR, or CRITICAL.
# WARNING or higher avoids messages printing every time a window is extracted.
mne_log_level = 'ERROR'

test_on_brainvision = False
brainvision_path = 'D:\\phd\\sleep\\data\\Fastball'

# model specific hyperparameters

# tcn
tcn_kernel_size = 11
tcn_n_blocks = 5 # 8 from Bai. 5 from Gemein et al.
tcn_n_filters = 55 # Was 2. Gemein et al said they used 55 'channels' for each block.
tcn_add_log_softmax = True
tcn_last_layer_type = 'max_pool'
tcn_dropout = 0.05270154233150525

deep4_n_filters_time=25
deep4_n_filters_spat=25
deep4_filter_time_length=10
deep4_pool_time_length=3
deep4_pool_time_stride=3
deep4_n_filters_2=50
deep4_filter_length_2=10
deep4_n_filters_3=100
deep4_filter_length_3=10
deep4_n_filters_4=200
deep4_filter_length_4=10
deep4_first_pool_mode="max"
deep4_later_pool_mode="max"
deep4_double_time_convs=False
deep4_split_first_layer=True
deep4_batch_norm=True
deep4_batch_norm_alpha=0.1
deep4_stride_before_pool=False

shallow_n_filters_time=40
shallow_filter_time_length=25
shallow_n_filters_spat=40
shallow_pool_time_length=75
shallow_pool_time_stride=15
shallow_split_first_layer=True
shallow_batch_norm=True
shallow_batch_norm_alpha=0.1

vit_patch_size = 10
vit_dim = 64
vit_depth = 6
vit_heads = 16
vit_mlp_dim = 64
vit_emb_dropout = 0.1
