import os
from braindecode.datasets import create_from_X_y
import mne
import csv
import numpy as np
import glob
import re
import torch
from sklearn.model_selection import train_test_split
from braindecode.datasets import BaseConcatDataset


def findall(input,value):
    start=0
    res=[]
    while value in input[start:]:
        res.append(input.index(value,start))
        start=res[-1]+1
    return res


def remove_tuab_from_dataset(ds, tuab_loc):
    tuab_list=get_full_filelist(tuab_loc,'.edf')
    for i in range(len(tuab_list)):
        tuab_list[i]= tuab_list[i].split("\\")[-1]
    # print(tuab_list)
    split_ids = []
    for d_i, d in enumerate(ds.description['path']):
        file_name=d.split("\\")[-1]
        if not file_name in tuab_list:
            # print(file_name)
            split_ids.append(d_i)
        # else:
            # print(file_name)
    # print(split_ids)
    splits = ds.split(split_ids)
    split = splits['0']
    return split

def remove_same(ds1, ds2,attribute):
    remove_num=0
    if attribute=='file_name':
        loc=-1
    elif attribute=='patients':
        loc=-3
    elif attribute=='sessions':
        loc=-2
    paths = np.array(ds1.description.loc[:, ['path']]).tolist()
    attributes = []
    for i in range(len(paths)):
        splits = paths[i][0].split('\\')
        attributes.append(splits[loc])
    unique_attributes = list(set(attributes))
    split_ids = []
    for d_i, d in enumerate(ds2.description['path']):
        attributes2=d.split("\\")[loc]
        if not attributes2 in unique_attributes:
            # print(file_name)
            split_ids.append(d_i)
        else:
            # print(attributes2)
            remove_num+=1
    # print(split_ids)
    print('remove_num:',remove_num)
    splits = ds2.split(split_ids)
    split = splits['0']
    return split

def weight_function(targets,device='cpu'):
    # targets = targets.cpu()
    weights = max(np.count_nonzero(targets == 0), np.count_nonzero(targets == 1)) / \
              torch.tensor([np.count_nonzero(targets == 0), np.count_nonzero(targets == 1)],
                        dtype=torch.float,device=device)
    return weights

def MCC(con_matrix):
    sum1=con_matrix[0,0]+con_matrix[0,1]
    sum2 = con_matrix[0, 1] + con_matrix[1, 1]
    sum3 = con_matrix[1, 1] + con_matrix[1, 0]
    sum4 = con_matrix[1, 0] + con_matrix[0, 0]
    if sum1==0 or sum2==0 or sum3==0 or sum4==0:
        return 0
    else:
        return (con_matrix[0,0]*con_matrix[1,1]-con_matrix[1,0]*con_matrix[0,1])/ ((sum1*sum2*sum3*sum4)**0.5)

def get_full_filelist(base_dir='.', target_ext='') -> list:
    fname_list = []


    for fname in os.listdir(base_dir):

        path = os.path.join(base_dir, fname)

        if os.path.isfile(path):

            fname_main, fname_ext = os.path.splitext(fname)

            if fname_ext == target_ext or target_ext == '':

                fname_list.append(path)

        elif os.path.isdir(path):

            temp_list = get_full_filelist(path, target_ext)

            fname_list = fname_list + temp_list
        else:
            pass

    return fname_list
def load_brainvision_as_windows(data_folder):
    paths = get_full_filelist(data_folder, '.vhdr')
    print(paths)

    def channel_processing(raw):
        for c in raw.ch_names:  # they need to have REF_ prefix to be recognised
            raw.rename_channels({c: "EEG " + c.upper() + '-REF'})
        raw.rename_channels({'EEG T7-REF': 'EEG T3-REF'})
        raw.rename_channels({'EEG T8-REF': 'EEG T4-REF'})
        raw.rename_channels({'EEG P7-REF': 'EEG T5-REF'})
        raw.rename_channels({'EEG P8-REF': 'EEG T6-REF'})
        raw.reorder_channels([
            'EEG FP1-REF', 'EEG FP2-REF', 'EEG F3-REF', 'EEG F4-REF', 'EEG C3-REF',
            'EEG C4-REF', 'EEG P3-REF', 'EEG P4-REF', 'EEG O1-REF', 'EEG O2-REF',
            'EEG F7-REF', 'EEG F8-REF', 'EEG T3-REF', 'EEG T4-REF', 'EEG T5-REF',
            'EEG T6-REF', 'EEG FZ-REF', 'EEG PZ-REF', 'EEG FC1-REF', 'EEG FC2-REF', 'EEG CP1-REF', 'EEG CP2-REF'])
        return raw

    parts = [channel_processing(mne.io.read_raw_brainvision(path, preload=True, verbose=False))
             for path in paths]

    def generate_cz(raw_data):
        res = np.row_stack((raw_data[:18], (raw_data[18] + raw_data[19] + raw_data[20] + raw_data[21]) / 4))
        # print(res.shape)
        return res

    X = [generate_cz(raw.get_data()) for raw in parts]
    # print(type(X[0]))
    y = [1 for raw in parts]
    sfreq = parts[0].info["sfreq"]
    ch_names = parts[0].info["ch_names"]
    ch_names = [v.upper() for v in ch_names]
    print(ch_names)
    # channels = [
    #     'A1', 'A2',
    #     'FP1', 'FP2', 'F3', 'F4', 'C3',
    #     'C4', 'P3', 'P4', 'O1', 'O2',
    #     'F7', 'F8', 'T3', 'T4', 'T5',
    #     'T6', 'FZ', 'CZ', 'PZ']
    channels = [
        'EEG FP1-REF', 'EEG FP2-REF', 'EEG F3-REF', 'EEG F4-REF', 'EEG C3-REF',
        'EEG C4-REF', 'EEG P3-REF', 'EEG P4-REF', 'EEG O1-REF', 'EEG O2-REF',
        'EEG F7-REF', 'EEG F8-REF', 'EEG T3-REF', 'EEG T4-REF', 'EEG T5-REF',
        'EEG T6-REF', 'EEG FZ-REF', 'EEG PZ-REF', 'EEG CZ-REF', ]
    windows_dataset = create_from_X_y(
        X, y, drop_last_window=False, sfreq=sfreq, ch_names=channels,
        window_stride_samples=6000,
        window_size_samples=6000,
    )
    # print(windows_dataset.description)
    return windows_dataset
def find_all_zero(input):
    res=[]
    for i in range(len(input)):
        if input[i]==0:
            res.append(i)
    return res


def top1(lst):
    return max(lst, default='empty', key=lambda v: lst.count(v))
def top1_prob(prob):
    normal=sum(prob[:,0])
    abnormal=sum(prob[:,1])
    # print('normal',normal)
    # print('abnormal',abnormal)

    if abnormal>normal:
        return 1
    else:
        return 0
def top1_prob1(prob,predict):
    abnormal=sum(prob[:,1]*predict)
    predict=1-np.array(predict)
    normal=sum(prob[:,0]*predict)
    if abnormal>normal:
        return 1
    else:
        return 0





def con_mat(starts,b,c,use_prob=False,prob=None):
    if use_prob:
        prob=np.exp(np.array(prob))
    b = b.tolist()
    TT = 0
    TF = 0
    FT = 0
    FF = 0

    begin = starts[0]
    if len(starts)>1:
        for end in starts[1:]:
            predict=c[begin:end].tolist()
            # print('predict',predict)
            if use_prob:
                prob_recording=prob[begin:end]
                # print('prob',prob)

                # predict=top1_prob1(prob_recording,predict)
                predict=top1_prob(prob_recording)
            else:
                predict=top1(predict)
            if predict==True:
                if b[begin]==True:
                    TT+=1
                else:
                    TF+=1
            else:
                if b[begin] == True:
                    FT+=1
                else:
                    FF+=1

            # print(predict)
            begin=end
    predict=c[begin:].tolist()
    predict=top1(predict)
    if predict == True:
        if b[begin] == True:
            TT += 1
        else:
            TF += 1
    else:
        if b[begin] == True:
            FT += 1
        else:
            FF += 1
    # print(predict)
    # print(TT,TF,FT,FF)
    return np.array([[FF,TF],[FT,TT]])
def timecost(time_dutation):
    m, s = divmod(time_dutation, 60)
    h, m = divmod(m, 60)
    return "%dh:%dm:%ds" % (h, m, s)
def select_by_duration(ds, tmin=0, tmax=None):
    if tmax is None:
        tmax = np.inf
    # determine length of the recordings and select based on tmin and tmax
    split_ids = []
    for d_i, d in enumerate(ds.datasets):
        duration = d.raw.n_times / d.raw.info['sfreq']
        if tmin <= duration <= tmax:
            split_ids.append(d_i)
    splits = ds.split(split_ids)
    split = splits['0']
    return split

def session_key(file_name):
    """ sort the file name by session """
    return re.findall(r'(s\d{2})', file_name)

def natural_key(file_name):
    """ provides a human-like sorting key of a string """
    key = [int(token) if token.isdigit() else None
           for token in re.split(r'(\d+)', file_name)]
    return key

def time_key(file_name):
    """ provides a time-based sorting key """
    splits = file_name.split(os.path.sep)
    [date] = re.findall(r'(\d{4}_\d{2}_\d{2})', splits[-2])
    date_id = [int(token) for token in date.split('_')]
    # recording_id = natural_key(splits[-1])
    # session_id = session_key(splits[-2])
    [recording_id] = re.findall(r't(\d{3})', splits[-1])
    [session_id] = re.findall(r's(\d{3})', splits[-1])
    return date_id + [session_id] + [recording_id]

def read_all_file_names(path, extension, key="time"):
    """ read all files with specified extension from given path
    :param path: parent directory holding the files directly or in subdirectories
    :param extension: the type of the file, e.g. '.txt' or '.edf'
    :param key: the sorting of the files. natural e.g. 1, 2, 12, 21 (machine 1, 12, 2, 21) or by time since this is
    important for cv. time is specified in the edf file names
    """
    file_paths = glob.glob(path + '**/*' + extension, recursive=True)

    if key == 'time':
        return sorted(file_paths, key=time_key)

    elif key == 'natural':
        return sorted(file_paths, key=natural_key)

    else:
        return file_paths

def relabel(dataset,label_path,dataset_folder):
    des=dataset.description
    des_path=list(des['path'])
    des_file=[]
    for i in des_path:
        des_file.append(os.path.basename(i))
    print('des_file',des_file)
    all_labelled_TUEG_file_names = []
    TUEG_labels = []
    with open(label_path, newline='') as csvfile:
        label_catalog_reader = csv.reader(csvfile, delimiter='\t')

        # Skip the header row (column names)
        next(label_catalog_reader, None)

        for row in label_catalog_reader:
            # Skip blank lines
            if len(row) == 0:
                continue
            id, _ = os.path.splitext(os.path.basename(row[1]))

            p_ab = float(row[2])
            label_from_ML = row[3]
            label_from_rules = row[4]
            # if label_from_ML==label_from_rules and (p_ab>=0.99 or p_ab<=0.01):
            if (p_ab >= 0.99 or p_ab <= 0.01):
                label = label_from_ML
                # print('pass')
            else:
                # print('p_ab',p_ab)
                continue

            full_folder = os.path.join(dataset_folder, row[0][9:])
            # print(full_folder)
            this_file_names = read_all_file_names(full_folder, '.edf', key='time')
            # print(this_file_names)
            [all_labelled_TUEG_file_names.append(ff) for ff in this_file_names if (id in os.path.basename(ff) and os.path.basename(ff) in des_file)]
            [TUEG_labels.append(label) for ff in this_file_names if (id in os.path.basename(ff) and os.path.basename(ff) in des_file)]
    print('all_labelled_TUEG_file_names:',all_labelled_TUEG_file_names)
    # print(len(all_labelled_TUEG_file_names))
    # print(list(des))
    if 'pathological' not in list(des):
        des['pathological']=[2]*len(des['age'])
    for i in range(len(all_labelled_TUEG_file_names)):
        des['pathological'][des_file.index(os.path.basename(all_labelled_TUEG_file_names[i]))]=bool(int(TUEG_labels[i]))
    return des

# Remove unlabeled data
def select_labeled(ds):
    split_ids = []
    for d_i, d in enumerate(ds.description['pathological']):
        if d==True or d==False:
            split_ids.append(d_i)
    splits = ds.split(split_ids)
    split = splits['0']
    return split

def exclude_by_name(ds,names):
    split_ids=[]
    for d_i, d in enumerate(ds.description['path']):
        if not d.split('\\')[-1] in names:
            split_ids.append(d_i)
        else:
            print("a overlap")
    splits = ds.split(split_ids)
    split = splits['0']
    return split

def check_inf(ds):
    for d_i, d in enumerate(ds.datasets):
        print(d.raw.info)

# Ensure that each data has all required channels
def select_by_channel(ds, channels):
    split_ids = []
    for d_i, d in enumerate(ds.datasets):
        include=True
        for chan in channels:
            if chan in d.raw.info['ch_names']:
                continue
            else:
                include=False
                break
        if include:
            split_ids.append(d_i)
    splits = ds.split(split_ids)
    split = splits['0']
    return split

def custom_crop(raw, tmin=0.0, tmax=None, include_tmax=True):
    # crop recordings to tmin – tmax. can be incomplete if recording
    # has lower duration than tmax
    # by default mne fails if tmax is bigger than duration
    tmax = min((raw.n_times - 1) / raw.info['sfreq'], tmax)
    raw.crop(tmin=tmin, tmax=tmax, include_tmax=include_tmax)


def split_data(windows_ds, split_way, train_size, valid_size, test_size, shuffle, random_state,remove_attribute=None):
    if split_way == 'proportion':
        idx_train, idx_valid_test = train_test_split(np.arange(len(windows_ds.description['path'])),
                                                     random_state=random_state,
                                                     train_size=train_size,
                                                     shuffle=shuffle)
        idx_valid, idx_test = train_test_split(idx_valid_test, random_state=random_state, test_size=test_size/(test_size+valid_size),
                                               shuffle=shuffle)
        splits = windows_ds.split(
            {"train": idx_train, "valid": idx_valid, "test": idx_test}
        )
        valid_set = splits["valid"]
        train_set = splits["train"]
        test_set = splits["test"]

        # valid_set = torch.utils.data.Subset(windows_ds, idx_valid)
        # train_set = torch.utils.data.Subset(windows_ds, idx_train)
        # test_set=torch.utils.data.Subset(windows_ds, idx_test)
    elif (split_way == 'folder'):  # this funtion do not create test_set now
        des = windows_ds.description
        if 'train' not in list(des):
            des['train'] = [2] * len(des['path'])
        path = des['path']
        train = des['train']
        for i in range(len(train)):
            if train[i] != True and train[i] != False:
                # print(train[i])
                if 'eval' in path[i]:
                    # print(path[i])
                    des['train'] [i]= False
                else:
                    des['train'][i] = True
        windows_ds.set_description(des, overwrite=True)
        # print(windows_ds.description)
        splits = windows_ds.split('train')
        # print(splits)
        train_valid_set = splits['True']
        test_set = splits['False']

        idx_train, idx_valid = train_test_split(np.arange(len(train_valid_set.description['path'])),
                                                random_state=random_state,
                                                train_size=train_size/(train_size+valid_size),
                                                shuffle=shuffle)
        splits = windows_ds.split(
            {"train": idx_train, "valid": idx_valid}
        )
        valid_set = splits["valid"]
        train_set = splits["train"]
    elif split_way=='patients':
        paths = np.array(windows_ds.description.loc[:, ['path']]).tolist()
        patients = []
        sessions = []
        for i in range(len(paths)):
            splits = paths[i][0].split('\\')
            patients.append(splits[-3])
            sessions.append(splits[-2])
        unique_patients=list(set(patients))
        # print(unique_patients)
        idx_train_patients, idx_valid_test_patients = train_test_split(np.arange(len(unique_patients)),
                                                     random_state=random_state,
                                                     train_size=train_size,
                                                     shuffle=shuffle)
        idx_valid_patients, idx_test_patients = train_test_split(idx_valid_test_patients, random_state=random_state, test_size=test_size/(test_size+valid_size),
                                               shuffle=shuffle)
        idx_train=[]
        for i in idx_train_patients:
            idx_train+=findall(patients,unique_patients[i])
        idx_valid=[]
        for i in idx_valid_patients:
            idx_valid+=findall(patients,unique_patients[i])
        idx_test=[]
        for i in idx_test_patients:
            idx_test+=findall(patients,unique_patients[i])
        splits = windows_ds.split(
            {"train": idx_train, "valid": idx_valid, "test": idx_test}
        )
        valid_set = splits["valid"]
        train_set = splits["train"]
        test_set = splits["test"]
    elif split_way=='sessions':
        paths = np.array(windows_ds.description.loc[:, ['path']]).tolist()
        patients = []
        sessions = []
        for i in range(len(paths)):
            splits = paths[i][0].split('\\')
            patients.append(splits[-3])
            sessions.append(splits[-2]+splits[-3])

        unique_sessions=list(set(sessions))
        # print(unique_sessions)
        idx_train_patients, idx_valid_test_patients = train_test_split(np.arange(len(unique_sessions)),
                                                     random_state=random_state,
                                                     train_size=train_size,
                                                     shuffle=shuffle)
        idx_valid_patients, idx_test_patients = train_test_split(idx_valid_test_patients, random_state=random_state, test_size=test_size/(test_size+valid_size),
                                               shuffle=shuffle)
        idx_train=[]
        for i in idx_train_patients:
            idx_train+=findall(sessions,unique_sessions[i])
        idx_valid=[]
        for i in idx_valid_patients:
            idx_valid+=findall(sessions,unique_sessions[i])
        idx_test=[]
        for i in idx_test_patients:
            idx_test+=findall(sessions,unique_sessions[i])
        splits = windows_ds.split(
            {"train": idx_train, "valid": idx_valid, "test": idx_test}
        )
        valid_set = splits["valid"]
        train_set = splits["train"]
        test_set = splits["test"]
    elif split_way=='train_on_tuab_tueg_test_on_tueg' or split_way=='train_on_tuab_tueg_test_on_tuab':
        des = windows_ds.description
        path = des['path']
        train = des['train']
        for i in range(len(train)):
            if train[i] != True and train[i] != False:
                # print(train[i])
                train[i]='others'
        windows_ds.set_description(des, overwrite=True)
        # print(windows_ds.description)
        splits = windows_ds.split('train')
        # print(splits)
        tuab_train= splits['True']
        tuab_test = splits['False']
        tueg_whole=splits['others']
        paths = np.array(tueg_whole.description.loc[:, ['path']]).tolist()
        patients = []
        sessions = []
        for i in range(len(paths)):
            splits = paths[i][0].split('\\')
            patients.append(splits[-3])
            sessions.append(splits[-2])
        unique_patients = list(set(patients))
        # print(unique_patients)
        idx_train_patients, idx_test_patients = train_test_split(np.arange(len(unique_patients)),
                                                                       random_state=random_state,
                                                                       train_size=train_size+valid_size,
                                                                       shuffle=shuffle)
        idx_train = []
        for i in idx_train_patients:
            idx_train += findall(patients, unique_patients[i])
        idx_test = []
        for i in idx_test_patients:
            idx_test += findall(patients, unique_patients[i])
        splits = tueg_whole.split(
            {"train": idx_train, "test": idx_test}
        )
        tueg_train = splits["train"]
        tueg_test = splits["test"]

        # idx_tueg_train, idx_tueg_test = train_test_split(np.arange(len(tueg_whole.description['path'])),
        #                                         random_state=random_state,
        #                                         train_size=train_size/(train_size+valid_size),
        #                                         shuffle=shuffle)
        # splits = windows_ds.split(
        #     {"train": idx_tueg_train, "valid": idx_tueg_test}
        # )
        # tueg_test = splits["valid"]
        # tueg_train = splits["train"]
        train_valid_set=BaseConcatDataset(([i for i in tueg_train.datasets])+([j for j in tuab_train.datasets]))
        idx_train, idx_valid = train_test_split(np.arange(len(train_valid_set.description['path'])),
                                                     random_state=random_state,
                                                     train_size=train_size/(train_size+valid_size),
                                                     shuffle=shuffle)
        splits = train_valid_set.split(
            {"train": idx_train, "valid": idx_valid}
        )
        valid_set = splits["valid"]
        train_set = splits["train"]
        if split_way=='train_on_tuab_tueg_test_on_tueg':
            test_set=tueg_test
        elif split_way=='train_on_tuab_tueg_test_on_tuab':
            test_set=tuab_test

    if remove_attribute:
        train_set = remove_same(test_set, train_set, remove_attribute)
    print('train_set:')
    print(train_set.description)
    print('valid_set:')
    print(valid_set.description)
    print('test_set:')
    print(test_set.description)
    return train_set, valid_set, test_set