import os
import queue
import time

import constants
import management
from classification.mobilenet_interface import MobileNetClassifier
from data_manager.datamanager import DataManager
from img_acquisition import img_acquisition
from vehicle_tracker.vehicle_tracker import VehicleTracker

manager = None


def main_loop():
    global manager
    # this is the main loop that will run as the program continues to run

    os.makedirs(constants.TMP_DIRECTORY, exist_ok=True)

    print('booting up...')
    img_to_tracker_q = queue.Queue(30)
    tracker_to_classifier_q = queue.Queue(30)
    classifier_to_dm_q = queue.Queue(30)

    acqu = img_acquisition.ImageAcquisition(img_to_tracker_q)
    vehicle_tracker = VehicleTracker(img_to_tracker_q, tracker_to_classifier_q)
    classifier = MobileNetClassifier(tracker_to_classifier_q, classifier_to_dm_q, 'classification/')
    data_manager = DataManager(classifier_to_dm_q, 'root', 'password', 'entries', 'vehicle_entries')

    classifier.start()
    vehicle_tracker.start()
    acqu.start_acquiring()

    print('booted up... starting processing')

    while True:
        time.sleep(0.2)
        if acqu.status == constants.Status.RUNNING and \
                        vehicle_tracker.status == constants.Status.RUNNING and \
                        classifier.status == constants.Status.RUNNING and \
                        data_manager.status == constants.Status.RUNNING:
            print('IA: %f \t VT: %f \t IC: %f' % (acqu.fps, vehicle_tracker.fps, classifier.fps), end='\r')

        else:
            print('some component stopped')
            acqu.stop_acquiring()
            vehicle_tracker.stop()
            classifier.stop()
            data_manager.stop()
            break

    print('outside of loop')
    acqu.stop_acquiring()
    manager.stop()
    return


def start_manager():
    global manager
    manager = management.Management()
    manager.start()

if __name__ == '__main__':
    start_manager()
    main_loop()
