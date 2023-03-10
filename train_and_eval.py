from itertools import product
import time
import pandas as pd
from bayes_opt import BayesianOptimization
from bayes_opt import SequentialDomainReductionTransformer
import torch
from braindecode.datasets import TUHAbnormal,TUH,BaseConcatDataset
from braindecode.preprocessing import create_fixed_length_windows
from braindecode.models import ShallowFBCSPNet, Deep4Net,EEGNetv4,EEGNetv1,EEGResNet,TCN,SleepStagerBlanco2020,USleep,\
                                TIDNet,get_output_shape,HybridNet, SleepStagerChambon2018
from braindecode.preprocessing import (
    exponential_moving_standardize, preprocess, Preprocessor, scale)
from braindecode.datautil import load_concat_dataset
from tcn_1 import TCN_1
from hybrid_1 import HybridNet_1
from vit import ViT
from util import *
from train_and_eval_config import *
from batch_test_hyperparameters import *


from torch.nn.functional import elu,relu,gelu




import warnings
warnings.filterwarnings("once")

pd.set_option('display.max_columns', 10)


# import ctypes
# ctypes.windll.msvcrt._setmaxstdio(2048)
# print(ctypes.windll.msvcrt._getmaxstdio())

# import globalvar as gl
# gl._init()
#
# gl.set_value('val_a',0 )


with open(log_path,'a') as f:
    writer=csv.writer(f, delimiter=',',lineterminator='\n',)
    writer.writerow([time.strftime('%Y-%m-%d_%H:%M:%S',time.localtime(time.time()))])
    writer.writerow(['train_loss', 'valid_loss',  'train_accuracy',  'valid_accuracy','etl_time','model_training_time',\
     'test_acc','test_precision','test_recall',\
     'n_repetition','random_state','tuab','tueg','n_tuab','n_tueg','n_load','preload','window_len_s',\
     'tuab_path','tueg_path','saved_data','saved_path','saved_windows_data','saved_windows_path',\
     'load_saved_data','load_saved_windows','bandpass_filter','low_cut_hz','high_cut_hz',\
     'standardization','factor_new','init_block_size','n_jobs','n_classes','lr','weight_decay',\
     'batch_size','n_epochs','tmin','tmax','multiple','sec_to_cut','duration_recording_sec','max_abs_val',\
     'sampling_freq','test_on_eval','split_way','train_size','valid_size','test_size','shuffle',\
     'model_name','final_conv_length','window_stride_samples','relabel_dataset','relabel_label',\
     'channels','dropout','precision_per_recording','recall_per_recording',\

     'acc_per_recording','mcc','mcc_per_recording','activation','remove_attribute'])



# Iterate over data/preproc parameters
for (random_state,tuab,tueg,n_tuab,n_tueg,n_load,preload,window_len_s,\
     tuab_path,tueg_path,saved_data,saved_path,saved_windows_data,saved_windows_path,\
     load_saved_data,load_saved_windows,bandpass_filter,low_cut_hz,high_cut_hz,\
     standardization,factor_new,init_block_size,n_jobs,tmin,tmax,multiple,sec_to_cut,duration_recording_sec,max_abs_val,\
     sampling_freq,test_on_eval,split_way,train_size,valid_size,test_size,shuffle,window_stride_samples,\
     relabel_dataset,relabel_label,channels,remove_attribute,activation) in product(
            RANDOM_STATE,TUAB,TUEG,N_TUAB,N_TUEG,N_LOAD,PRELOAD,\
            WINDOW_LEN_S,TUAB_PATH,TUEG_PATH,SAVED_DATA,SAVED_PATH,SAVED_WINDOWS_DATA,\
            SAVED_WINDOWS_PATH,LOAD_SAVED_DATA,LOAD_SAVED_WINDOWS,BANDPASS_FILTER,\
            LOW_CUT_HZ,HIGH_CUT_HZ,STANDARDIZATION,FACTOR_NEW,INIT_BLOCK_SIZE,N_JOBS,\
            TMIN,TMAX,MULTIPLE,SEC_TO_CUT,\
            DURATION_RECORDING_SEC,MAX_ABS_VAL,SAMPLING_FREQ,TEST_ON_VAL,SPLIT_WAY,\
            TRAIN_SIZE,VALID_SIZE,TEST_SIZE,SHUFFLE,WINDOW_STRIDE_SAMPLES,RELABEL_DATASET,RELABEL_LABEL,CHANNELS,REMOVE_ATTRIBUTE,ACTIVATION):
    print(random_state, tuab, tueg, n_tuab, n_tueg, n_load, preload, window_len_s, \
    tuab_path, tueg_path, saved_data, saved_path, saved_windows_data, saved_windows_path, \
    load_saved_data, load_saved_windows, bandpass_filter, low_cut_hz, high_cut_hz, \
    standardization, factor_new, init_block_size, n_jobs, \
    tmin, tmax, multiple, sec_to_cut, duration_recording_sec, max_abs_val, \
    sampling_freq, test_on_eval, split_way, train_size, valid_size, test_size, shuffle, \
    relabel_dataset, relabel_label, \
    channels,remove_attribute)

    cuda = torch.cuda.is_available()  # check if GPU is available, if True chooses to use it
    device = 'cuda' if cuda else 'cpu'
    print('device:',device)
    if cuda:
        torch.backends.cudnn.benchmark = True
    # torch.backends.cudnn.benchmark = True  # Enables automatic algorithm optimizations
    torch.set_num_threads(n_jobs)  # Sets the available number of threads

    mne.set_log_level(mne_log_level)

    data_loading_start = time.time()


    window_len_samples = window_len_s*sampling_freq #Count how many data points are in a window
    if load_saved_windows:   # load preprocessed windows
        load_ids = list(range(n_load)) if n_load else None
        windows_ds = load_concat_dataset(
            path=saved_windows_path,
            preload=False,
            ids_to_load=load_ids,
            target_name='pathological',
            n_jobs=1,
        )
    else:
        if load_saved_data:  # load preprocessed recordings
            load_ids=list(range(n_load)) if n_load else None
            ds=load_concat_dataset(
            path=saved_path,
            preload=preload,
            ids_to_load=load_ids,
            target_name='pathological',
        )
        else:
            tuab_ids = list(range(n_tuab)) if n_tuab else None
            ds_tuab= TUHAbnormal(     #load tuab
                tuab_path, recording_ids=tuab_ids,target_name='pathological',
                preload=preload)
            print(ds_tuab.description)

            if tueg:  #load tueg
                tueg_ids=list(range(n_tueg)) if n_tueg else None
                ds_tueg=TUH(tueg_path,recording_ids=tueg_ids,target_name='pathological',
                    preload=preload)
                if tuab:   # remove the overlap between tuab and tueg if loading both
                    ds_tueg = remove_tuab_from_dataset(ds_tueg, tuab_path)

                print('tueg:',ds_tueg.description)

            ds=BaseConcatDataset(([i for i in ds_tuab.datasets] if tuab else [])+([j for j in ds_tueg.datasets] if tueg else []))
            print('concate:',ds.description)

            ds=select_by_duration(ds,tmin,tmax)  #select the recording with the lenth we want
            print('select_duration:',ds.description)

            for i in range(len(relabel_label)):  #label the data without labels
                ds.set_description(relabel(ds,relabel_label[i],relabel_dataset[i]),overwrite=True)
            print('labeled:',ds.description)

            ds=select_labeled(ds)   # removed unlabeled data
            print('select_labeled:',ds.description)

            ds=select_by_channel(ds,channels)  # removed the data that do not have all the channels we want
            print('select_channel:',ds.description)


            preprocessors = [  #preprocessing list
                Preprocessor('pick_types', eeg=True, meg=False, stim=False),# Keep EEG sensors
                Preprocessor('pick_channels',ch_names = channels,ordered=True),  #select the channels we want
                Preprocessor(fn='resample', sfreq=sampling_freq),  # resampling the data
                Preprocessor(custom_crop, tmin=sec_to_cut, tmax=duration_recording_sec+sec_to_cut, include_tmax=False,
                             apply_on_array=False),  #select desired segment of recordings
                Preprocessor(scale, factor=1e6, apply_on_array=True),  # Convert from V to uV
                Preprocessor(np.clip, a_min=-max_abs_val, a_max=max_abs_val, apply_on_array=True),  #Clip the data within the specified range
            ]
            if multiple: #scaling
                preprocessors.append(Preprocessor(scale, factor=multiple,apply_on_array=True))
            if bandpass_filter: #filtering
                preprocessors.append(Preprocessor('filter', l_freq=low_cut_hz, h_freq=high_cut_hz))
            if standardization:
                preprocessors.append(Preprocessor(exponential_moving_standardize,  # Exponential moving standardization
                             factor_new=factor_new, init_block_size=init_block_size))

            preprocess(ds, preprocessors, save_dir=saved_path,overwrite=False,n_jobs=n_jobs)# preprocess and save the data,  please note that here is a bug that if set n_jobs=1, there is a risk of memory explosion. So please don't set n_jobs larger than 1 when using the whole dataset.


        fs = ds.datasets[0].raw.info['sfreq']
        window_len_samples = int(fs * window_len_s)  # calculate window lengths
        if not window_stride_samples:  # set the stride between windows
            window_stride_samples = window_len_samples

        # window_stride_samples = int(fs * window_len_s)
        windows_ds = create_fixed_length_windows(  # windowing the data
            ds, start_offset_samples=0, stop_offset_samples=None,
            window_size_samples=window_len_samples,
            window_stride_samples=window_stride_samples, drop_last_window=True,
            preload=preload, drop_bad_windows=True)

        # Drop bad epochs
        # XXX: This could be parallelized.
        # XXX: Also, this could be implemented in the Dataset object itself.
        for ds in windows_ds.datasets:
            ds.windows.drop_bad()
            assert ds.windows.preload == preload

        if saved_windows_data:
            windows_ds.save(saved_windows_path,True)

    # print(windows_ds.description)

    # Split the data:
    train_set, valid_set, test_set = split_data(windows_ds, split_way, train_size, valid_size, test_size, shuffle, random_state,remove_attribute)
    print('len_valid_train',len(train_set.description.loc[:, ['path']])+len(valid_set.description.loc[:, ['path']]))
    print('len_test',len(test_set.description.loc[:, ['path']]))
    etl_time = time.time() - data_loading_start

    n_channels = windows_ds[0][0].shape[0]

    print("n_channels:",n_channels)
    # n_times = windows_ds[0][0].shape[1]


    # Iterate over model/training hyperparameters
    for (i, n_classes, lr, weight_decay, batch_size, n_epochs, model_name, final_conv_length,dropout) \
      in product(range(N_REPETITIONS), N_CLASSES, LR, WEIGHT_DECAY, BATCH_SIZE, N_EPOCHS, MODEL_NAME, \
      FINAL_CONV_LENGTH,DROPOUT):
        print(i, random_state, tuab, tueg, n_tuab, n_tueg, n_load, preload, window_len_s, \
              tuab_path, tueg_path, saved_data, saved_path, saved_windows_data, saved_windows_path, \
              load_saved_data, load_saved_windows, bandpass_filter, low_cut_hz, high_cut_hz, \
              standardization, factor_new, init_block_size, n_jobs, n_classes, lr, weight_decay, \
              batch_size, n_epochs, tmin, tmax, multiple, sec_to_cut, duration_recording_sec, max_abs_val, \
              sampling_freq, test_on_eval, split_way, train_size, valid_size, test_size, shuffle, \
              model_name, final_conv_length, window_stride_samples, relabel_dataset, relabel_label, \
              channels)
        if shuffle and i>0:
            # Re-split the data to ensure each repetition uses a different split:
            train_set, valid_set, test_set = split_data(windows_ds, split_way, train_size, valid_size, test_size,
                                                        shuffle, random_state+i)


        mne.set_log_level(mne_log_level)
        def exp(dropout=0.2):
            if activation=='elu':  #choose the activation function
                nonlin=elu
            elif activation=='relu':
                nonlin=relu
            elif activation=='gelu':
                nonlin=gelu

            #select the model(first-stage)
            if model_name=='deep4':
                model = Deep4Net(
                            n_channels, n_classes, input_window_samples=window_len_samples,
                            final_conv_length=final_conv_length, n_filters_time=deep4_n_filters_time, n_filters_spat=deep4_n_filters_spat,
                            filter_time_length=deep4_filter_time_length, pool_time_length=deep4_pool_time_length, pool_time_stride=deep4_pool_time_stride,
                            n_filters_2=deep4_n_filters_2, filter_length_2=deep4_filter_length_2, n_filters_3=deep4_n_filters_3,
                            filter_length_3=deep4_filter_length_3, n_filters_4=deep4_n_filters_4, filter_length_4=deep4_filter_length_4,
                            first_pool_mode=deep4_first_pool_mode, later_pool_mode=deep4_later_pool_mode, drop_prob=dropout,
                            double_time_convs=False, split_first_layer=True, batch_norm=True,
                            batch_norm_alpha=0.1, stride_before_pool=False,first_nonlin=nonlin,later_nonlin=nonlin)

            elif model_name=='shallow_smac':
                model = ShallowFBCSPNet(
                    n_channels, n_classes, input_window_samples=window_len_samples,
                    n_filters_time=shallow_n_filters_time, filter_time_length=shallow_filter_time_length, n_filters_spat=shallow_n_filters_spat,
                    pool_time_length=shallow_pool_time_length, pool_time_stride=shallow_pool_time_stride, final_conv_length=final_conv_length,
                    split_first_layer=shallow_split_first_layer, batch_norm=shallow_batch_norm, batch_norm_alpha=shallow_batch_norm_alpha,
                    drop_prob=dropout)
            elif model_name=='eegnetv4':
                model=EEGNetv4(n_channels, n_classes, input_window_samples=window_len_samples, final_conv_length=final_conv_length,
                                            pool_mode='mean', F1=8, D=2, F2=16, kernel_length=64, third_kernel_size=(8, 4),
                                            drop_prob=dropout)
            elif model_name=='eegnetv1':
                model=EEGNetv1(n_channels, n_classes, input_window_samples=window_len_samples, final_conv_length=final_conv_length, pool_mode='max', second_kernel_size=(2, 32), third_kernel_size=(8, 4), drop_prob=dropout)
            elif model_name=='eegresnet':
                model=EEGResNet(n_channels, n_classes, window_len_samples, final_conv_length, n_first_filters=10, n_layers_per_block=2, first_filter_length=3, split_first_layer=True, batch_norm_alpha=0.1, batch_norm_epsilon=0.0001)
            elif model_name=='tcn':
                model=TCN(n_channels, n_classes, n_blocks=8, n_filters=2, kernel_size=12, drop_prob=dropout, add_log_softmax=False)
            elif model_name=='sleep2020':
                model=SleepStagerBlanco2020(n_channels, sampling_freq, n_conv_chans=20, input_size_s=60, n_classes=2, n_groups=3, max_pool_size=2, dropout=dropout, apply_batch_norm=False, return_feats=False)
            elif model_name=='sleep2018':
                model=SleepStagerChambon2018(n_channels, sampling_freq, n_conv_chs=8, time_conv_size_s=0.5, max_pool_size_s=0.125, pad_size_s=0.25, input_size_s=60, n_classes=n_classes, dropout=dropout, apply_batch_norm=False, return_feats=False)
            elif model_name=='usleep':
                model=USleep(in_chans=n_channels, sfreq=sampling_freq, depth=12, n_time_filters=5, complexity_factor=1.67, with_skip_connection=True, n_classes=2, input_size_s=60, time_conv_size_s=0.0703125, ensure_odd_conv_size=False, apply_softmax=False)
            elif model_name=='tidnet':
                model=TIDNet(n_channels, n_classes, window_len_samples, s_growth=24, t_filters=32, drop_prob=dropout, pooling=15, temp_layers=2, spat_layers=2, temp_span=0.05, bottleneck=3, summary=- 1)
            elif model_name=='tcn_1':
                model=TCN_1(n_channels, n_classes, n_blocks=tcn_n_blocks, n_filters=tcn_n_filters, kernel_size=tcn_kernel_size, drop_prob=dropout, add_log_softmax=tcn_add_log_softmax,input_window_samples=window_len_samples,last_layer_type=tcn_last_layer_type)
            elif model_name=='hybridnet':
                model=HybridNet(n_channels,n_classes,window_len_samples)
            elif model_name == 'hybridnet_1':
                model = HybridNet_1(n_channels, n_classes, window_len_samples)
            elif model_name == 'vit':
                model = ViT(num_channels=n_channels,input_window_samples = window_len_samples,patch_size = vit_patch_size,num_classes = n_classes,dim = vit_dim,depth = vit_depth,heads = vit_heads,mlp_dim = vit_mlp_dim,dropout = dropout,emb_dropout = vit_emb_dropout)




            if cuda:
                model.cuda()
            training_setup_end = time.time()

            # Start training loop
            model_training_start = time.time()

            from skorch.callbacks import LRScheduler
            from skorch.helper import predefined_split
            from braindecode import EEGClassifier
            from skorch.callbacks import Checkpoint,EarlyStopping

            # set the learning rate scheduler
            monitor = lambda net: all(net.history[-1, ('train_loss_best', 'valid_loss_best')])
            cp = Checkpoint(monitor=monitor,dirname='', f_criterion=None, f_optimizer=None, load_best=False)
            callbacks=["accuracy", ("lr_scheduler", LRScheduler('CosineAnnealingLR' ,T_max=n_epochs - 1)),("cp",cp)] #'CosineAnnealingWarmRestarts', T_0=10 'CosineAnnealingLR' ,T_max=n_epochs - 1
            if earlystopping:
                es_patience=n_epochs//3
                es=EarlyStopping(threshold=0.001, threshold_mode='rel', patience=es_patience)
                callbacks.append(('es',es))

            #Set various parameters for training
            clf = EEGClassifier(
                model,
                criterion=torch.nn.NLLLoss(weight_function(train_set.get_metadata().target,device)),
                optimizer=torch.optim.AdamW,
                train_split=predefined_split(valid_set) if test_on_eval else None,  # using valid_set for validation
                optimizer__lr=lr,
                optimizer__weight_decay=weight_decay,
                batch_size=batch_size,
                callbacks=callbacks,
                device=device,
            )


            # Prevent GPU memory fragmentation
            torch.cuda.empty_cache()

            # Model training for a specified number of epochs. `y` is None as it is already supplied
            # in the dataset.
            global i
            if not test_model: # Choose to load a model or train a model
                clf.fit(train_set, y=None, epochs=n_epochs)
                clf.save_params('./saved_models/'+model_name+time.strftime('%Y-%m-%d_%H-%M-%S',time.localtime(time.time()))+'params.pt')

            else:
                clf.initialize()
                clf.load_params('./saved_models/'+params[i])
            model_training_time = time.time() - model_training_start

            import matplotlib.pyplot as plt
            from matplotlib.lines import Line2D
            if not test_model:
                # Extract loss and accuracy values for plotting from history object
                results_columns = ['train_loss', 'valid_loss', 'train_accuracy', 'valid_accuracy']
                # print(clf.history)

                df = pd.DataFrame(clf.history[:, results_columns], columns=results_columns,
                                  index=clf.history[:, 'epoch'])
                # get percent of misclass for better visual comparison to loss
                df = df.assign(train_misclass=100 - 100 * df.train_accuracy,
                               valid_misclass=100 - 100 * df.valid_accuracy)
                print(df)
                if plot_result: # whether plot the result
                    plt.style.use('seaborn')
                    fig, ax1 = plt.subplots(figsize=(8, 3))
                    df.loc[:, ['train_loss', 'valid_loss']].plot(
                        ax=ax1, style=['-', ':'], marker='o', color='tab:blue', legend=False, fontsize=14)

                    ax1.tick_params(axis='y', labelcolor='tab:blue', labelsize=14)
                    ax1.set_ylabel("Loss", color='tab:blue', fontsize=14)

                    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

                    df.loc[:, ['train_misclass', 'valid_misclass']].plot(
                        ax=ax2, style=['-', ':'], marker='o', color='tab:red', legend=False)
                    ax2.tick_params(axis='y', labelcolor='tab:red', labelsize=14)
                    ax2.set_ylabel("Misclassification Rate [%]", color='tab:red', fontsize=14)
                    ax2.set_ylim(ax2.get_ylim()[0], 85)  # make some room for legend
                    ax1.set_xlabel("Epoch", fontsize=14)

                    # where some data has already been plotted to ax
                    handles = []
                    handles.append(Line2D([0], [0], color='black', linewidth=1, linestyle='-', label='Train'))
                    handles.append(Line2D([0], [0], color='black', linewidth=1, linestyle=':', label='Valid'))
                    plt.legend(handles, [h.get_label() for h in handles], fontsize=14)
                    plt.tight_layout()
                    plt.show()

            from sklearn.metrics import confusion_matrix
            from braindecode.visualization import plot_confusion_matrix

            # test on the testset
            print('test:',test_set.description)
            y_true = test_set.get_metadata().target
            starts=find_all_zero(test_set.get_metadata()['i_window_in_trial'].tolist())
            y_pred = clf.predict(test_set)
            y_pred_proba=clf.predict_proba(test_set)
            print('diff:',sum((np.exp(np.array(y_pred_proba[:,1]))>0.5)!=y_pred))

            # generate confusion matrices
            confusion_mat_per_recording=con_mat(starts,y_true,y_pred)
            confusion_mat_per_recording_proba=con_mat(starts,y_true,y_pred,True,y_pred_proba)
            print(confusion_mat_per_recording)
            print(confusion_mat_per_recording_proba)


            confusion_mat = confusion_matrix(y_true, y_pred)
            print(confusion_mat)


            # generate various evaluation index
            precision=confusion_mat[0,0]/(confusion_mat[0,0]+confusion_mat[1,0])
            recall=confusion_mat[0,0]/(confusion_mat[0,0]+confusion_mat[0,1])
            acc=(confusion_mat[0,0]+confusion_mat[1,1])/(confusion_mat[0,0]+confusion_mat[0,1]+confusion_mat[1,1]+confusion_mat[1,0])
            mcc=MCC(confusion_mat)
            precision_per_recording=confusion_mat_per_recording[0,0]/(confusion_mat_per_recording[0,0]+confusion_mat_per_recording[1,0])
            recall_per_recording=confusion_mat_per_recording[0,0]/(confusion_mat_per_recording[0,0]+confusion_mat_per_recording[0,1])
            acc_per_recording=(confusion_mat_per_recording[0,0]+confusion_mat_per_recording[1,1])/(confusion_mat_per_recording[0,0]+confusion_mat_per_recording[0,1]+confusion_mat_per_recording[1,1]+confusion_mat_per_recording[1,0])
            mcc_per_recording=MCC(confusion_mat_per_recording)
            end=time.time()
            print('precision:',precision)
            print('recall:',recall)
            print('acc:',acc)
            print('mcc:',mcc)
            print('precision_per_recording:', precision_per_recording)
            print('recall_per_recording:', recall_per_recording)
            print('acc_per_recording:', acc_per_recording)
            print('mcc:',mcc_per_recording)
            print('etl_time:',etl_time)
            print('model_training_time:',model_training_time)

            with open(log_path, 'a') as f: # save the results
                writer = csv.writer(f, delimiter=',', lineterminator='\n', )
                if not test_model:
                    his_len=len(df)
                    for i2 in range(his_len-1):
                        writer.writerow([df.loc[i2+1][0],df.loc[i2+1][1],df.loc[i2+1][2],df.loc[i2+1][3]])


                    writer.writerow([df.loc[his_len][0],df.loc[his_len][1],df.loc[his_len][2],df.loc[his_len][3],etl_time,\
                 model_training_time,acc,precision,recall,i,random_state,tuab,tueg,n_tuab,n_tueg,n_load,preload,\
                 window_len_s,tuab_path,tueg_path,saved_data,saved_path,saved_windows_data,saved_windows_path,\
                 load_saved_data,load_saved_windows,bandpass_filter,low_cut_hz,high_cut_hz,\
                 standardization,factor_new,init_block_size,n_jobs,n_classes,lr,weight_decay,\
                 batch_size,n_epochs,tmin,tmax,multiple,sec_to_cut,duration_recording_sec,max_abs_val,\
                 sampling_freq,test_on_eval,split_way,train_size,valid_size,test_size,shuffle,\
                 model_name,final_conv_length,window_stride_samples,relabel_dataset,relabel_label,\
                 channels,dropout, precision_per_recording,recall_per_recording,acc_per_recording,mcc,mcc_per_recording,activation,remove_attribute])
                else:
                    writer.writerow(['test_model','test_model','test_model','test_model',etl_time,\
                 model_training_time,acc,precision,recall,i,random_state,tuab,tueg,n_tuab,n_tueg,n_load,preload,\
                 window_len_s,tuab_path,tueg_path,saved_data,saved_path,saved_windows_data,saved_windows_path,\
                 load_saved_data,load_saved_windows,bandpass_filter,low_cut_hz,high_cut_hz,\
                 standardization,factor_new,init_block_size,n_jobs,n_classes,lr,weight_decay,\
                 batch_size,n_epochs,tmin,tmax,multiple,sec_to_cut,duration_recording_sec,max_abs_val,\
                 sampling_freq,test_on_eval,split_way,train_size,valid_size,test_size,shuffle,\
                 model_name,final_conv_length,window_stride_samples,relabel_dataset,relabel_label,\
                 channels,dropout, precision_per_recording,recall_per_recording,acc_per_recording,mcc,mcc_per_recording,activation,remove_attribute])


            if plot_result:
                labels=['normal','abnormal']
                # plot the basic conf. matrix
                plot_confusion_matrix(confusion_mat, class_names=labels) #if there is something wrong, change the version of matplotlib to 3.0.3, or find the result in confusion_mat
                # plot_confusion_matrix(confusion_mat)
                plt.show()
                plot_confusion_matrix(confusion_mat_per_recording, class_names=labels)
                plt.show()

            if train_whole_dataset_again: #Store all the information needed for the second stage model
                with open('./training_detail.csv', 'a') as f1:
                    print('len_train_valid',len(train_set)+len(valid_set))
                    print('len_test',len(test_set))

                    writer1 = csv.writer(f1, delimiter=',', lineterminator='\n', )
                    writer1.writerow([time.strftime('%Y-%m-%d_%H:%M:%S',time.localtime(time.time()))])

                    windows_true =list(train_set.get_metadata().target)+list(valid_set.get_metadata().target)+list(test_set.get_metadata().target) #save labels
                    len_true=len(windows_true)
                    for i in range(len_true//16384):
                        writer1.writerow(windows_true[i*16384:(i+1)*16384])
                    writer1.writerow(windows_true[(len_true)//16384 * 16384:])

                    windows_pred=np.exp(np.concatenate((np.array(clf.predict_proba(train_set)[:,1]),np.array(clf.predict_proba(valid_set)[:,1]),np.array(clf.predict_proba(test_set)[:,1])))) #Store predicted probabilities for all data

                    for i in range(len_true//16384):
                        writer1.writerow(windows_pred[i*16384:(i+1)*16384])
                    writer1.writerow(windows_pred[(len_true)//16384 * 16384:])


                    #Store how many windows each recording has
                    len_train=len(list(train_set.get_metadata().target))
                    len_valid_train=len(list(valid_set.get_metadata().target))+len_train
                    writer1.writerow(find_all_zero(train_set.get_metadata()['i_window_in_trial'].tolist())+[x+len_train for x in find_all_zero(valid_set.get_metadata()['i_window_in_trial'].tolist())]+[y+len_valid_train for y in find_all_zero(test_set.get_metadata()['i_window_in_trial'].tolist())])


                    #Store the session and patient to which each recording belongs
                    paths = np.array(train_set.description.loc[:, ['path']]).tolist()+np.array(valid_set.description.loc[:, ['path']]).tolist()+np.array(test_set.description.loc[:, ['path']]).tolist()
                    patients = []
                    sessions = []
                    for i in range(len(paths)):
                        splits = paths[i][0].split('\\')
                        patients.append(splits[-3])
                        sessions.append(splits[-2])
                    print('patients', patients)
                    print('sessions', sessions)
                    writer1.writerow(patients)
                    writer1.writerow(sessions)


            return acc


        exp(dropout=dropout)
