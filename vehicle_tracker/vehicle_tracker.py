# import the necessary packages
import math
import threading
import time

import cv2

import constants
from configuration.configuration import configuration


class VehicleTracker:
    MIN_AREA = 1000

    def __init__(self, in_queue, out_queue):
        self.fgbg = cv2.createBackgroundSubtractorKNN()
        self.rows = None
        self.cols = None
        self.in_q = in_queue
        self.out_q = out_queue
        self.run_thread = threading.Thread(target=self.tracker_thread)
        self.fps_lock = threading.Lock()
        self.status = constants.Status.NOT_STARTED
        self.tmp_fps = 0.0
        self.hot_zones = []

    @property
    def p1(self):
        return (configuration.get_value('vehicle_detection', 'point1x'),
                configuration.get_value('vehicle_detection', 'point1y'))

    @property
    def p2(self):
        return (configuration.get_value('vehicle_detection', 'point2x'),
                configuration.get_value('vehicle_detection', 'point2y'))

    @property
    def cool_down(self):
        tmp = configuration.get_value('vehicle_detection', 'cool_down')
        if tmp is None:
            return 4
        return tmp

    @property
    def cool_down_radius(self):
        tmp = configuration.get_value('vehicle_detection', 'cool_down_radius')
        if tmp is None:
            return 4
        return tmp

    @property
    def hot_zone(self):
        tmp = configuration.get_value('vehicle_detection', 'hot_zone')
        if tmp is None:
            return 2
        return tmp

    @property
    def fps(self):
        return self.tmp_fps

    @property
    def dist_two_points(self):
        return math.sqrt((self.p2[0] - self.p1[0]) ** 2 +
                         (self.p2[1] - self.p1[1]) ** 2)

    def check_zones(self, point):
        for zone, _ in self.hot_zones:
            tmp = abs(point[0] - zone[0])**2 + abs(point[1] - zone[1])**2
            if math.sqrt(tmp) < self.cool_down_radius:
                return True

        return False

    def check_zone_age(self, zone):
        if zone[1] > 0:
            return True
        else:
            return False

    def clean_zones(self):
        self.hot_zones = [zone for zone in self.hot_zones if self.check_zone_age(zone)]
        for i, (zone, age) in enumerate(self.hot_zones):
            self.hot_zones[i] = (zone, age - 1)

    def check_distance(self, point):
        val1 = (self.p2[1] - self.p1[1]) * point[0]
        val2 = (self.p2[0] - self.p1[0]) * point[1]
        val3 = self.p2[0] * self.p1[1]
        val4 = self.p2[1] * self.p1[0]
        dist = float(abs(val1 - val2 + val3 - val4)) / self.dist_two_points
        return dist

    def get_middle(self, x1, y1, x2, y2):
        return x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2

    def tracker_thread(self):
        while self.status == constants.Status.RUNNING:
            try:
                frame = self.in_q.get()
                start_time = time.time()
                if frame is None:
                    continue
                objs = self.process_frame(frame)
                self.show_frame(frame)
                self.clean_zones()
                if len(objs) > 0:
                    for obj in objs:
                        self.out_q.put(obj)
                end_time = time.time()
                self.tmp_fps = 1.0 / (end_time - start_time)
            except Exception as e:
                print(e)
                self.status = constants.Status.ERRORED

    def reset(self):
        self.stop()
        self.start()

    def start(self):
        self.status = constants.Status.RUNNING
        self.run_thread.start()

    def stop(self):
        self.status = constants.Status.STOPPED
        self.run_thread.join()

    def show_frame(self, frame):
        tmp = frame
        for zone, age in self.hot_zones:
            cv2.circle(tmp, (int(zone[0]), int(zone[1])), self.cool_down_radius, (255, 0,0), thickness=age)
        cv2.line(tmp, self.p1, self.p2, (0, 255, 255), thickness=2)
        cv2.imshow('vt', tmp)
        cv2.waitKey(1)


    def process_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (25, 25), 0)
        fgmask = self.fgbg.apply(gray)
        thresh = cv2.dilate(fgmask, None, iterations=2)
        (_, cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)

        found_objs = []
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < VehicleTracker.MIN_AREA:
                continue

            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cp = self.get_middle(x, y, x + w, y + h)

            if self.check_distance(cp) < self.hot_zone:
                if not self.check_zones(cp):
                    print('found object')
                    found_objs.append(frame[y:y + h, x:x + w])
                    self.hot_zones.append((cp, self.cool_down))

        return found_objs
