# %%
import streamlit as st
def cancer_diagnosis_app():
   import pandas as pd
   import numpy as np
   import tensorflow as tf
   from sklearn.preprocessing import StandardScaler

   # Load the CSV file
   def load_data():
       df = pd.read_csv('cancer.csv')
       return df

   data = load_data()

   st.title("Cancer Diagnosis Prediction")

   features = data.drop(columns=['diagnosis(1=m, 0=b)']) # Removing the target variable

   # Defining minimum and maximum values for each column
   column_ranges = {
       'radius_mean': (6.981, 28.11),
       'texture_mean': (9.71, 39.28),
       'perimeter_mean': (43.79, 188.5),
       'area_mean': (143.5, 2501),
       'smoothness_mean': (0.05263, 0.1634),
       'compactness_mean': (0.01938, 0.3454),
       'concavity_mean': (0, 0.4268),
       'concave points_mean': (0, 0.2012),
       'symmetry_mean': (0.106, 0.304),
       'fractal_dimension_mean': (0.04996, 0.09744),
       'radius_se': (0.1115, 2.873),
       'texture_se': (0.3602, 4.885),
       'perimeter_se': (0.757, 21.98),
       'area_se': (6.802, 542.2),
       'smoothness_se': (0.001713, 0.03113),
       'compactness_se': (0.002252, 0.1354),
       'concavity_se': (0, 0.396),
       'concave points_se': (0, 0.05279),
       'symmetry_se': (0.007882, 0.07895),
       'fractal_dimension_se': (0.000895, 0.02984),
       'radius_worst': (7.93, 36.04),
       'texture_worst': (12.02, 49.54),
       'perimeter_worst': (50.41, 251.2),
       'area_worst': (185.2, 4254),
       'smoothness_worst': (0.07117, 0.2226),
       'compactness_worst': (0.02729, 1.058),
       'concavity_worst': (0, 1.252),
       'concave points_worst': (0, 0.291),
       'symmetry_worst': (0.1565, 0.6638),
       'fractal_dimension_worst': (0.05504, 0.2075)
   }

   input_data = {}

   # Initialize input fields in session state
   if 'input_data' not in st.session_state:
       st.session_state['input_data'] = {}
       for feature_name, _ in column_ranges.items():
           st.session_state['input_data'][feature_name] = float(column_ranges[feature_name][0])

   # Randomize button
   if st.button("Randomize Values"):
       for feature_name, (min_range, max_range) in column_ranges.items():
           st.session_state['input_data'][feature_name] = np.random.uniform(float(min_range), float(max_range))

   # Display and input fields for all features
   for feature_name, (min_range, max_range) in column_ranges.items():
       feature_value = st.number_input(
           f"Enter {feature_name} ({min_range} - {max_range}):",
           min_value=float(min_range),
           max_value=float(max_range),
           step=0.01,
           key=feature_name,
           value=st.session_state['input_data'].get(feature_name, float(min_range)) # Initialize with random or min value
       )
       st.session_state['input_data'][feature_name] = feature_value

   # Load your trained model
   model = tf.keras.models.load_model('cancer_model.h5')
   scaler = StandardScaler()
   scaler.fit(features) # Fitting the scaler to the training data

   # Remove the target variable from the input data
   input_data.pop('diagnosis(1=m, 0=b)', None)

   # Define a button to make predictions
   if st.button("Predict Diagnosis"):
       # Make predictions
       input_array = np.array([list(st.session_state['input_data'].values())])
       standardized_input = scaler.transform(input_array)
       predictions = model.predict(standardized_input)

       # Display prediction results
       if predictions[0][0] > 0.5:
           st.success("Predicted Diagnosis: Malignant (1)")
       else:
           st.success("Predicted Diagnosis: Benign (0)")

   # Reset button to clear input values
   if st.button("Reset"):
       input_data.clear()
       for feature_name, (min_range, max_range) in column_ranges.items():
           input_data[feature_name] = float(min_range)
   # Show the input data
   st.subheader("Input Data")
   input_df = pd.DataFrame.from_dict(st.session_state['input_data'], orient='index', columns=['Value'])
   st.write(input_df)     
         
           
    
    

# %%
def diabetes_prediction_app():
  import streamlit as st
  import numpy as np
  import pandas as pd
  from sklearn.preprocessing import StandardScaler
  from sklearn.model_selection import train_test_split
  from sklearn import svm
  from sklearn.metrics import accuracy_score
  import joblib

  # Load the CSV file
  def load_data():
      df = pd.read_csv('diabetes.csv')
      return df

  diabetes_dataset = load_data()

  # Separate data and labels
  X = diabetes_dataset.drop(columns='Outcome', axis=1)
  Y = diabetes_dataset['Outcome']

  # Standardizing the data
  scaler = StandardScaler()
  scaler.fit(X)
  X = scaler.transform(X)

  # Load the trained model using joblib
  classifier = joblib.load('svm_diabetes_model.joblib')

  st.title("Diabetes Prediction")

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

  # Updating session state with new input values
  st.session_state['Pregnancies'] = Pregnancies
  st.session_state['Glucose'] = Glucose
  st.session_state['BloodPressure'] = BloodPressure
  st.session_state['SkinThickness'] = SkinThickness
  st.session_state['Insulin'] = Insulin
  st.session_state['BMI'] = BMI
  st.session_state['DiabetesPedigreeFunction'] = DiabetesPedigreeFunction
  st.session_state['Age'] = Age
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

  # Reset values button
  if st.button("Reset Values"):
     # Reset input field values to their initial values
     st.session_state['Pregnancies'] = 0
     st.session_state['Glucose'] = 0
     st.session_state['BloodPressure'] = 0
     st.session_state['SkinThickness'] = 0
     st.session_state['Insulin'] = 0
     st.session_state['BMI'] = 0.0
     st.session_state['DiabetesPedigreeFunction'] = 0.078
     st.session_state['Age'] = 21


# %%
PAGES = {
   "Cancer Diagnosis Prediction": cancer_diagnosis_app,
   "Diabetes Prediction": diabetes_prediction_app
}


# %%
st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", list(PAGES.keys()))

page = PAGES[selection]
page()


