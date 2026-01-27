# Gestforms
In this ongoing project, we want to test if 18-months old infants display selective attention to gesture forms as compared to motor actions.

This project provides a template to analyse eyetracking data from infants looking at dynamic stimuli.

<img width="1120" height="692" alt="image" src="https://github.com/user-attachments/assets/2e9b9ab9-a3cc-4943-825e-51f72024851c" />


## Extracting data
Using a Python script (test.py), we first converted raw EyeLink .asc eye-tracking files which processes and classifies gaze points into Regions of Interest (ROIs) during experimental trials involving gesture (target) and action (distractor) videos.
At this step, the main goal is to determine where participants were looking over time and whether their gaze was directed toward the target gesture, the distractor action, or outside these two regions.

[Download the dataset](Results.txt.zip)

We used the eyetrackingR package to run a cluster-based permutation analyses to examine significant durations during which infants looked more at gestures.

[Download R-script](eyetracking_timecourse.Rmd)

