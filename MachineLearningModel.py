# -*- coding: utf-8 -*-
"""
MachineLearningModel using sklearn
"""
#1: Importing the necessary module and dataset.
import sklearn 
from sklearn.datasets import load_breast_cancer 

#2: Loading the dataset to a variable.
data = load_breast_cancer() 

#3: Organizing the data and looking at it.
label_names = data['target_names'] 
labels = data['target'] 
feature_names = data['feature_names'] 
features = data['data'] 

print(label_names) 
print(labels) 
print(feature_names) 
print(features) 


#4: Organizing the data into Sets
# importing the function 
from sklearn.model_selection import train_test_split 
# splitting the data 
train, test, train_labels, test_labels = train_test_split(features, labels, test_size = 0.33, random_state = 42) 

print(train)
print(test)

#5: Building the Model.
# importing the GaussianNB module of the machine learning model 
from sklearn.naive_bayes import GaussianNB

# initializing the classifier - create the object for the class: GaussianNB()
gnb = GaussianNB() 

# training the classifier  #train the model by fitting it to the data in the dataset using the fit() method.
model = gnb.fit(train, train_labels) 

#5: Test the Model & extract the predictors from testset using method:predict()  
#After the training is complete, we can use the trained model to make predictions on our test set that we have prepared before
#To do that, we will use the built-in predict() function which returns an array of prediction values for data instance in the test set

# making the predictions 
predictions = gnb.predict(test) 
# printing the predictions 
print(predictions) 

#6: Evaluating the trained model’s accuracy.
# importing the accuracy measuring function 
from sklearn.metrics import accuracy_score 

# evaluating the accuracy 
print(accuracy_score(test_labels, predictions)) 

#So, we find out that this machine learning classifier based on the Naive Bayes algorithm is 94.15% accurate in predicting whether a tumor is malignant or benign.
