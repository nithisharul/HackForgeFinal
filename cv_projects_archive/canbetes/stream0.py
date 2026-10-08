# %%
import streamlit as st
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import StandardScaler

# %%
# Loading the CSV file
def load_data():
    df = pd.read_csv('cancer.csv')
    return df

data = load_data()

st.title("Cancer Diagnosis Prediction")

features = data.drop(columns=['diagnosis(1=m, 0=b)'])  # Removing the target variable


# %%
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


# %%
# Initializing input fields in session state
if 'input_data' not in st.session_state:
 st.session_state['input_data'] = {}
 for feature_name, _ in column_ranges.items():
    st.session_state['input_data'][feature_name] = float(column_ranges[feature_name][0])

# %%
# Randomizing button
if st.button("Randomize Values"):
 for feature_name, (min_range, max_range) in column_ranges.items():
     st.session_state['input_data'][feature_name] = np.random.uniform(float(min_range), float(max_range))

# %%
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

# %%
# Loading the trained model
model = tf.keras.models.load_model('cancer_model.h5')
scaler = StandardScaler()
scaler.fit(features)  # Fitting the scaler to the training data

# %%
# Remove the target variable from the input data
input_data.pop('diagnosis(1=m, 0=b)', None)

# %%
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


# %%
# Reset button to clear input values
if st.button("Reset"):
    input_data.clear()
    for feature_name, (min_range, max_range) in column_ranges.items():
        input_data[feature_name] = float(min_range)

# %%
# Show the input data
st.subheader("Input Data")
input_df = pd.DataFrame.from_dict(st.session_state['input_data'], orient='index', columns=['Value'])
st.write(input_df)



