import random

import cv2


class ImgScope:
    def __init__(self):
        self.width = 1900
        self.height = 1200

    def run(self, img, labels):
        (rows, cols, _) = img.shape
        for label in labels:
            red = random.randint(0, 255)
            green = random.randint(0, 255)
            blue = random.randint(0, 255)

            cv2.putText(img, label['type'], (int(label['xmax'] * cols), int(label['ymax'] * rows)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (red, green, blue))

        cv2.imshow('display', img)
        cv2.waitKey(10)
