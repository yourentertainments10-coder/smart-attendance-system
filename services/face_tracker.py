import numpy as np
from collections import defaultdict
import time

class SimpleFaceTracker:
    def __init__(self, max_distance=75, max_age=2.0, max_disappeared=30):
        """
        Simple centroid-based tracker for faces/persons.
        
        Args:
            max_distance: Max pixel distance for matching
            max_age: Max seconds a track can exist without update
            max_disappeared: Max frames before track deletion
        """
        self.max_distance = max_distance
        self.max_age = max_age
        self.max_disappeared = max_disappeared
        self.next_track_id = 1
        self.tracks = {}  # track_id: {'centroid':(cx,cy), 'bbox':(x,y,w,h), 'disappeared':0, 'last_update':time}
    
    def _centroid(self, bbox):
        """(x,y,w,h) -> (cx,cy)"""
        x, y, w, h = bbox
        return (x + w/2, y + h/2)
    
    def _euclidean_distance(self, pt1, pt2):
        return np.sqrt((pt1[0]-pt2[0])**2 + (pt1[1]-pt2[1])**2)
    
    def update(self, detections):
        """
        detections: list[dict{'bbox':(x,y,w,h), 'face_crop':img}]
        Returns: list[dict{**detection, 'track_id':int, 'centroid':(cx,cy)}]
        """
        if len(detections) == 0:
            # Age out disappeared tracks
            for track_id in list(self.tracks.keys()):
                self.tracks[track_id]['disappeared'] += 1
            return []
        
        # Compute centroids
        input_centroids = np.array([self._centroid(d['bbox']) for d in detections])
        
        # If no existing tracks, assign new
        if len(self.tracks) == 0:
            tracked = []
            for i, det in enumerate(detections):
                track_id = self.next_track_id
                self.next_track_id += 1
                centroid = input_centroids[i]
                self.tracks[track_id] = {
                    'centroid': centroid,
                    'bbox': det['bbox'],
                    'disappeared': 0,
                    'last_update': time.time()
                }
                det['track_id'] = track_id
                det['centroid'] = centroid
                tracked.append(det)
            return tracked
        
        # Existing tracks centroids
        existing_centroids = np.array([track['centroid'] for track in self.tracks.values()])
        distances = np.linalg.norm(input_centroids[:, np.newaxis] - existing_centroids[np.newaxis, :], axis=2)
        
        # Hungarian-like greedy assignment (simple min-distance)
        matched_tracks = {}
        for i, input_centroid in enumerate(input_centroids):
            min_dist_idx = np.argmin(distances[i])
            min_dist = distances[i, min_dist_idx]
            if min_dist < self.max_distance:
                track_id = list(self.tracks.keys())[min_dist_idx]
                matched_tracks[track_id] = i
        
        # Update matched tracks
        tracked = []
        for track_id, det_idx in matched_tracks.items():
            track = self.tracks[track_id]
            track['centroid'] = input_centroids[det_idx]
            track['bbox'] = detections[det_idx]['bbox']
            track['disappeared'] = 0
            track['last_update'] = time.time()
            
            det = detections[det_idx].copy()
            det['track_id'] = track_id
            det['centroid'] = track['centroid']
            tracked.append(det)
        
        # New tracks for unmatched detections
        for i, input_centroid in enumerate(input_centroids):
            if i not in matched_tracks.values():
                track_id = self.next_track_id
                self.next_track_id += 1
                self.tracks[track_id] = {
                    'centroid': input_centroid,
                    'bbox': detections[i]['bbox'],
                    'disappeared': 0,
                    'last_update': time.time()
                }
                det = detections[i].copy()
                det['track_id'] = track_id
                det['centroid'] = input_centroid
                tracked.append(det)
        
        # Age disappeared tracks
        current_time = time.time()
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_tracks:
                self.tracks[track_id]['disappeared'] += 1
                self.tracks[track_id]['last_update'] = current_time
            if (self.tracks[track_id]['disappeared'] > self.max_disappeared or 
                current_time - self.tracks[track_id]['last_update'] > self.max_age):
                del self.tracks[track_id]
        
        return sorted(tracked, key=lambda x: x['track_id'])
