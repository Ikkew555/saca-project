import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

# โหลดข้อมูลต้นฉบับ
df = pd.read_csv("symptom_to_disease.csv")

# รวม symptom ตาม disease
grouped = df.groupby("disease")["symptom"].apply(list).reset_index()

# One-hot encode (แปลงเป็น 0/1)
mlb = MultiLabelBinarizer()
X = mlb.fit_transform(grouped["symptom"])

# รวมเป็น dataframe พร้อม label
train_df = pd.DataFrame(X, columns=mlb.classes_)
train_df["disease"] = grouped["disease"]

# บันทึกไว้ใช้เทรน
train_df.to_csv("training_data.csv", index=False)
print("✅ Training data saved → training_data.csv")
