import pandas as pd
import matplotlib.pyplot as plt

def analyse(ff):

    # load data from results.csv
    results = pd.read_csv(ff)

    # drop rows with fewer than 5 entries
    results = results.dropna(thresh=5)

    # Replace all entries in 'channels' column with 'with A1/A2' if 'channels' column contains 'A1' or 'A2'. Otherwise
    # replace with 'without A1/A2':
    chan_str_1 = "['EEG A1-REF', 'EEG A2-REF', 'EEG FP1-REF', 'EEG FP2-REF', 'EEG F3-REF', 'EEG F4-REF', 'EEG C3-REF', 'EEG C4-REF', 'EEG P3-REF', 'EEG P4-REF', 'EEG O1-REF', 'EEG O2-REF', 'EEG F7-REF', 'EEG F8-REF', 'EEG T3-REF', 'EEG T4-REF', 'EEG T5-REF', 'EEG T6-REF', 'EEG FZ-REF', 'EEG CZ-REF', 'EEG PZ-REF']"
    chan_str_2 = "['EEG FP1-REF', 'EEG FP2-REF', 'EEG F3-REF', 'EEG F4-REF', 'EEG C3-REF', 'EEG C4-REF', 'EEG P3-REF', 'EEG P4-REF', 'EEG O1-REF', 'EEG O2-REF', 'EEG F7-REF', 'EEG F8-REF', 'EEG T3-REF', 'EEG T4-REF', 'EEG T5-REF', 'EEG T6-REF', 'EEG FZ-REF', 'EEG CZ-REF', 'EEG PZ-REF']"
    results['channels'] = results['channels'].replace([chan_str_1], 'with A1/A2')
    results['channels'] = results['channels'].replace([chan_str_2], 'without A1/A2')

    # create box plots of 'accuracy', grouping by 'model_name' and 'channels'
    results.boxplot(column='acc_per_recording', by=['model_name', 'channels'])
    plt.show()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    analyse('/home/david/Downloads/result (2).csv')