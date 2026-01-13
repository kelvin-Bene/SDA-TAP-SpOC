# -*- coding: utf-8 -*-
"""
Created on Thu Jul  3 15:15:04 2025

@author: Gabriel Lundin
"""

import time

class Timer:
    def __init__(self):
        self.start = time.perf_counter()
        self.checkpoints = []
        self.labels = []

    def mark(self, label):
        now = time.perf_counter()
        self.checkpoints.append(now)
        self.labels.append(label)

    async def mark_async(self, label):
        self.mark(label)

    def report(self):
        times = [self.start] + self.checkpoints
        for i in range(1, len(times)):
            print(f"{self.labels[i-1]}: {times[i] - times[i-1]:.4f} s")
        print(f"Total: {times[-1] - self.start:.4f} s")
