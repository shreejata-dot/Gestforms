# Gestforms
In this ongoing project, we want to test if 18-months old infants display selective attention to gesture forms as compared to motor actions.

This project provides a template to analyse eyetracking data from infants looking at dynamic stimuli.

<img width="1120" height="692" alt="image" src="https://github.com/user-attachments/assets/2e9b9ab9-a3cc-4943-825e-51f72024851c" />


## Extracting data
Using a Python script (test.py), we first converted raw EyeLink .asc eye-tracking files which processes and classifies gaze points into Regions of Interest (ROIs) during experimental trials involving gesture (target) and action (distractor) videos.
At this step, the main goal is to determine where participants were looking over time and whether their gaze was directed toward the target gesture, the distractor action, or outside these two regions.

[Download the dataset](Results.txt.zip)

We used the eyetrackingR package to run a cluster-based permutation analyses to examine significant durations during which infants looked more at gestures. First, we analysed the whole scene, then specific regions of interest (ROI) of each video, selecting areas where the gestures and actions were executed.

[Download R-script](eyetracking_timecourse.Rmd)


## Findings

<img width="658" height="377" alt="image" src="https://github.com/user-attachments/assets/a7ef753f-8bac-4e26-bd46-967e2048d23a" />

What we find so far is that 18-mo infants do discrilinate gesture forms from other actions, like they discriminate speech sounds from other sounds. 


<img width="936" height="269" alt="image" src="https://github.com/user-attachments/assets/ec129cf1-07c7-4794-a605-7dc1109f4ce9" />

They also look differently at pointing gestures versus iconic gestures that represent actions and object attributes. We are currently analysing the underlying mechanisms for these differences in detecting different gesture types. The manuscript is in preparation.

