# EEGScopeAndArbitration

This repository is used to test the effect of the second stage model (arbitration) and window length (scope) on the EEG abnormal classification task.

# Document Description
[batch_test_hyperparameters.default.py](batch_test_hyperparameters.default.py): A template for hyperparameters that need to be tested in batches   
[train_and_eval_config.default.py](train_and_eval_config.default.py): Template for hyperparameters tested individually   
[train_and_eval.py](train_and_eval.py): Train and test the first-stage model   
[final_decision.py](final_decision.py): Train and test the second-stage model     
[util.py](util.py): Helper functions   
[vit.py](vit.py), [hybrid_1.py](hybrid_1.py), [tcn_1.py](tcn_1.py): model file  
[tueg_labels.csv](tueg_labels.csv): labels of TUEG
[results_boxplot.py](results_boxplot.py) Plot results
# Use steps
1, Download the TUAB dataset https://isip.piconepress.com/projects/tuh_eeg/downloads/tuh_eeg_abnormal/  
2, Create batch_test_hyperparameters.py and train_and_eval_config.py based on [batch_test_hyperparameters.default.py](batch_test_hyperparameters.default.py) and [train_and_eval_config.default.py](train_and_eval_config.default.py)   
3, Run the [train_and_eval.py](train_and_eval.py) to generate result.csv and training_detail.csv   
4, Run the [final_decision.py](final_decision.py) to generate decision_result.csv
