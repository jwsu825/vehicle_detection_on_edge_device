import os
import threading
import time
from datetime import datetime

import numpy as np
import tensorflow as tf

import constants
from configuration.configuration import configuration

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


class MobileNetClassifier:
    def __init__(self, input_q, output_q, model_dir='./'):
        # load model and label
        self.sess = None
        self.graph = self.load_graph(self.model_file)
        self.label = self.load_labels(self.label_file)
        self.status = constants.Status.NOT_STARTED
        self.run_thread = threading.Thread(target=self.classification_thread)
        self.in_q = input_q
        self.output_q = output_q

        self.input_operation = self.graph.get_operation_by_name("import/input")
        self.output_operation = self.graph.get_operation_by_name("import/final_result")

        self.tmp_fps = 0.0

    @property
    def fps(self):
        return self.tmp_fps

    @property
    def model_file(self):
        return configuration.get_value('vehicle_detection', 'pb_file')

    @property
    def label_file(self):
        return configuration.get_value('vehicle_detection', 'labels_file')

    def load_graph(self, model_file):
        graph = tf.Graph()
        graph_def = tf.GraphDef()

        with open(model_file, "rb") as f:
            graph_def.ParseFromString(f.read())
        with graph.as_default():
            tf.import_graph_def(graph_def)
            self.sess = tf.Session(graph=graph)

        return graph

    def normalized_tensor(self, cv_image, input_height=224, input_width=224,
                          input_mean=128, input_std=128):
        output_name = "normalized"

        #################################################################
        float_caster = tf.cast(cv_image, tf.float32)
        dims_expander = tf.expand_dims(float_caster, 0)
        resized = tf.image.resize_bilinear(dims_expander, [input_height, input_width])
        normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
        sess = tf.Session()
        result = sess.run(normalized)
        return result

    def load_labels(self, label_file):
        label = []
        proto_as_ascii_lines = tf.gfile.GFile(label_file).readlines()
        for l in proto_as_ascii_lines:
            label.append(l.rstrip())
        return label

    # Helper code
    def load_image_into_numpy_array(self, image):
        (im_width, im_height) = image.size
        return np.array(image.getdata()).reshape(
            (im_height, im_width, 3)).astype(np.uint8)

    def classify(self, image):
        t = self.normalized_tensor(image)

        with self.graph.as_default():
            results = self.sess.run(self.output_operation.outputs[0],
                                    {self.input_operation.outputs[0]: t})
        results = np.squeeze(results)
        results = results.argsort()[-5:][::-1]
        return self.label[results[0]]

    def classification_thread(self):
        while self.status == constants.Status.RUNNING:
            try:
                image = self.in_q.get()
                start_time = time.time()
                classification = self.classify(image)
                self.output_q.put({'category': classification, 'time': datetime.now().timestamp()})
                end_time = time.time()
                self.tmp_fps = 1.0 / (end_time - start_time)
            except Exception as e:
                print(e)
                self.status = constants.Status.ERRORED

    def start(self):
        self.status = constants.Status.RUNNING
        self.run_thread.start()

    def stop(self):
        self.status = constants.Status.STOPPED
        self.run_thread.join()
