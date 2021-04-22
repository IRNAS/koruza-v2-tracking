
# CAMERA TEMP
import picamera
import picamera.array
import datetime
import time
import os

# imports for image manhole recognition

import cv2
import numpy as np
import scipy.signal
import os
import shutil

# install OpenCv:
# https://linuxize.com/post/how-to-install-opencv-on-raspberry-pi/
# https://www.pyimagesearch.com/2017/10/09/optimizing-opencv-on-the-raspberry-pi/

# # config
# # https://www.raspberrypi.org/documentation/raspbian/applications/camera.md


class Camera():
    def __init__(self):
        try:
            self.stream = cv2.VideoCapture("http://localhost:8080/?action=stream")  # open a URL stream
            print("Camera initialised.")
        except Exception as e:
            print(e)

    def snapshot(self, filename):
        if self.stream.isOpened():
            # Read a frame from the stream
            ret, img = self.stream.read()
            if ret: # ret == True if stream.read() was successful
                # cv2.imshow('Video Stream Monitor', img)
                cv2.imwrite(filename, img)

    def get_shift(self, im1, im2):
        """Get shift of two images using cross correlation"""

        # get rid of the color channels by performing a grayscale transform
        # the type cast into 'float' is to avoid overflows
        im1_gray = np.sum(im1.astype('float'), axis=2)
        im2_gray = np.sum(im2.astype('float'), axis=2)

        # get rid of the averages, otherwise the results are not good
        im1_gray -= np.mean(im1_gray)
        im2_gray -= np.mean(im2_gray)

        corr_img = scipy.signal.fftconvolve(im1_gray, im2_gray[::-1,::-1], mode='same')
        # calculate the correlation image; note the flipping of onw of the images
        return np.unravel_index(np.argmax(corr_img), corr_img.shape) 


cam = Camera()
# cam.snapshot("./images/-2000_0.jpg")
cam.get_shift("./images/-2000_0.jpg", "./images/0_0.jpg")