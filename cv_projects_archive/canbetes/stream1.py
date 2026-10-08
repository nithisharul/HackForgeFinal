# %%
import streamlit as st
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn import svm
from sklearn.metrics import accuracy_score
import joblib

# %%
# Load the CSV file
def load_data():
    df = pd.read_csv('diabetes.csv')
    return df

diabetes_dataset = load_data()

# %%
# Separate data and labels
X = diabetes_dataset.drop(columns='Outcome', axis=1)
Y = diabetes_dataset['Outcome']

# %%
# Standardize the data
scaler = StandardScaler()
scaler.fit(X)
X = scaler.transform(X)

# %%
# Load the trained model using joblib
classifier = joblib.load('svm_diabetes_model.joblib')

st.title("Diabetes Prediction")

# %%
# Initialize input fields
if 'Pregnancies' not in st.session_state:
   st.session_state['Pregnancies'] = 0
if 'Glucose' not in st.session_state:
   st.session_state['Glucose'] = 0
if 'BloodPressure' not in st.session_state:
   st.session_state['BloodPressure'] = 0
if 'SkinThickness' not in st.session_state:
   st.session_state['SkinThickness'] = 0
if 'Insulin' not in st.session_state:
   st.session_state['Insulin'] = 0
if 'BMI' not in st.session_state:
   st.session_state['BMI'] = 0.0
if 'DiabetesPedigreeFunction' not in st.session_state:
   st.session_state['DiabetesPedigreeFunction'] = 0.078
if 'Age' not in st.session_state:
   st.session_state['Age'] = 21

# %%
# Randomizer button
if st.button("Value Randomizer"):
    st.session_state['Pregnancies'] = np.random.randint(0, 18)
    st.session_state['Glucose'] = np.random.randint(0, 200)
    st.session_state['BloodPressure'] = np.random.randint(0, 123)
    st.session_state['SkinThickness'] = np.random.randint(0, 100)
    st.session_state['Insulin'] = np.random.randint(0, 847)
    st.session_state['BMI'] = np.random.uniform(0.0, 67.1)
    st.session_state['DiabetesPedigreeFunction'] = np.random.uniform(0.078, 2.42)
    st.session_state['Age'] = np.random.randint(21, 82)

# %%
# Input fields
st.markdown("### Input Fields")
Pregnancies = st.number_input("Pregnancies", min_value=0, max_value=17, value=st.session_state['Pregnancies'], step=1)
Glucose = st.number_input("Glucose", min_value=0, max_value=199, value=st.session_state['Glucose'], step=1)
BloodPressure = st.number_input("Blood Pressure", min_value=0, max_value=122, value=st.session_state['BloodPressure'], step=1)
SkinThickness = st.number_input("Skin Thickness", min_value=0, max_value=99, value=st.session_state['SkinThickness'], step=1)
Insulin = st.number_input("Insulin", min_value=0, max_value=846, value=st.session_state['Insulin'], step=1)
BMI = st.number_input("BMI", min_value=0.0, max_value=67.1, value=st.session_state['BMI'], step=0.1)
DiabetesPedigreeFunction = st.number_input("Diabetes Pedigree Function", min_value=0.078, max_value=2.42, value=st.session_state['DiabetesPedigreeFunction'], step=0.001)
Age = st.number_input("Age", min_value=21, max_value=81, value=st.session_state['Age'], step=1)

# %%
# Update session state with new input values
st.session_state['Pregnancies'] = Pregnancies
st.session_state['Glucose'] = Glucose
st.session_state['BloodPressure'] = BloodPressure
st.session_state['SkinThickness'] = SkinThickness
st.session_state['Insulin'] = Insulin
st.session_state['BMI'] = BMI
st.session_state['DiabetesPedigreeFunction'] = DiabetesPedigreeFunction
st.session_state['Age'] = Age

# %%
# Prediction button
if st.button("Predict"):
    input_data = np.array([[st.session_state['Pregnancies'], st.session_state['Glucose'], st.session_state['BloodPressure'], st.session_state['SkinThickness'], st.session_state['Insulin'], st.session_state['BMI'], st.session_state['DiabetesPedigreeFunction'], st.session_state['Age']]])
    std_data = scaler.transform(input_data)
    prediction = classifier.predict(std_data)

    if prediction[0] == 0:
        prediction_text = "The person is not diabetic."
    else:
        prediction_text = "The person is diabetic."

    st.subheader("Prediction Result:")
    st.write(prediction_text)

# %%
# Reset values button
if st.button("Reset Values"):
    # Resetting input field values to their initial values
    st.session_state['Pregnancies'] = 0
    st.session_state['Glucose'] = 0
    st.session_state['BloodPressure'] = 0
    st.session_state['SkinThickness'] = 0
    st.session_state['Insulin'] = 0
    st.session_state['BMI'] = 0.0
    st.session_state['DiabetesPedigreeFunction'] = 0.078
    st.session_state['Age'] = 21


