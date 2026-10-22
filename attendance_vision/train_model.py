import tensorflow as tf
from tensorflow.keras import layers, models #type: ignore
import os


DATASET_PATH = 'dataset'
IMG_SIZE = (128, 128)


train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_PATH,
    label_mode='int',
    color_mode='grayscale',
    image_size=IMG_SIZE,
    shuffle=True
)

model = models.Sequential([
    layers.Input(shape=(128, 128, 1)),
    layers.Rescaling(1./255),
    layers.Conv2D(32, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(64, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(128, 3, activation='relu'),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(len(train_ds.class_names), activation='softmax')
])

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(train_ds, epochs=15)
model.save('face_id_deep.h5')
print("Deep Model Saved.")