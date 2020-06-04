import os
import threading
import time

import cv2

import constants
from configuration import configuration
import queue


class ImageAcquisition:
    # Image Acquisition module for Jetson TX2
    #   - will pull images from the onboard camera
    #   - spawns a new thread that constantly gathers new images
    #   - user can call get_new_image which will return the newest opencv image

    def __init__(self, out_queue):
        self.__most_recent_image = None
        self.status = constants.Status.NOT_STARTED
        self.__video_capture = None
        self.__output_resolution = ()
        self.__acq_thread = None
        self.__num_images = 0
        self.output_queue = out_queue
        self.tmp_fps = 0.0
        self.timer = None
        self.save_interval = 1

    @property
    def fps(self):
        return self.tmp_fps

    @property
    def running(self):
        return self.status == constants.Status.RUNNING

    @property
    def output_size(self):
        cols = configuration.configuration.get_value('img_acquisition', 'cols')
        rows = configuration.configuration.get_value('img_acquisition', 'rows')

        if cols is None:
            cols = 640
        if rows is None:
            rows = 360
        return (cols, rows)

    @property
    def debug(self):
        return configuration.configuration.get_value('general', 'debug')

    @property
    def source(self):
        if self.debug:
            return configuration.configuration.get_value('img_acquisition', 'load_from_file')
        return "nvcamerasrc ! video/x-raw(memory:NVMM), " \
                          "width=(int)2592, height=(int)1944,format=(string)I420, " \
                          "framerate=(fraction)30/1 " \
                          "! nvvidconv flip-method=0 ! video/x-raw, format=(string)BGRx " \
                          "! videoconvert ! video/x-raw, format=(string)BGR ! appsink"

    def print_status(self):
        print("ImageAcquisition: Acquired %d images" % (self.__num_images))

    def debug_statement(self, message):
        if self.debug:
            print(message)

    def save_image(self):
        cv2.imwrite(os.path.join(constants.TMP_DIRECTORY, 'preview.jpg'), self.__most_recent_image)

    def __error(self, message):
        self.status = constants.Status.ERRORED
        print("Error in Image Acquisition: %s" % message)

    def __acquisition_thread(self):
        if not self.__video_capture.isOpened():
            time.sleep(1)
            if not self.__video_capture.isOpened():
                self.__error('Could not open the video source')
                return

        self.status = constants.Status.RUNNING

        self.timer = time.time()

        while self.status == constants.Status.RUNNING:
            start_time = time.time()
            _, self.__most_recent_image = self.__video_capture.read()
            if self.__most_recent_image is not None:
                self.__most_recent_image = cv2.resize(self.__most_recent_image, self.output_size)
                self.__num_images += 1

                if (time.time() - self.timer) > self.save_interval:
                    self.save_image()
                    self.timer = time.time()

            try:
                if self.debug:
                    self.output_queue.put(self.__most_recent_image)
                else:
                    self.output_queue.put_nowait(self.__most_recent_image)
                end_time = time.time()
                self.tmp_fps = 1.0 / (end_time - start_time)
            except queue.Full:
                continue

    def reset(self):
        self.stop_acquiring()
        self.start_acquiring()

    def start_acquiring(self):
        self.__video_capture = cv2.VideoCapture(self.source)
        self.__acq_thread = threading.Thread(target=self.__acquisition_thread)
        self.__acq_thread.start()

    def stop_acquiring(self):
        self.status = constants.Status.STOPPED
        self.__acq_thread.join()
